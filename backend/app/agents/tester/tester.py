"""Tester Agent - Merged Role + Crew Implementation.

NEW ARCHITECTURE:
- Inherits from BaseAgent (Kafka abstracted)
- Handles QA and testing tasks
- Integrates CrewAI crew logic directly
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict
from uuid import UUID

import yaml
from crewai import Agent, Crew, Task

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.tester.tasks import (
    create_test_plan_task,
    create_validate_requirements_task,
    create_test_cases_task,
)
from app.agents.tester.tools import get_tester_tools
from app.models import Agent as AgentModel


logger = logging.getLogger(__name__)


class Tester(BaseAgent):
    """Tester agent - creates test plans and ensures software quality.

    NEW ARCHITECTURE:
    - No more separate Consumer/Role layers
    - Handles tasks via handle_task() method
    - Router sends tasks via @Tester mentions
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize Tester.

        Args:
            agent_model: Agent database model
            **kwargs: Additional arguments (heartbeat_interval, max_idle_time)
        """
        super().__init__(agent_model, **kwargs)

        # Load configuration
        self.config = self._load_config()

        # Create CrewAI agent (legacy - for manual @Tester mentions)
        self.crew_agent = self._create_crew_agent()
        
        # Initialize TesterCrew for integration test generation
        from app.agents.tester.crew import TesterCrew
        self.crew = TesterCrew()
        
        # Get project path for test file generation
        from app.core.db import engine
        from sqlmodel import Session
        from app.models import Project
        
        with Session(engine) as session:
            project = session.get(Project, self.project_id)
            self.project_path = project.project_path if project and project.project_path else None
            self.tech_stack = project.tech_stack if project else "nodejs-react"

        logger.info(f"Tester initialized: {self.name}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        config_path = Path(__file__).parent / "config.yaml"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

        # Default configuration
        return {
            "agent": {
                "role": "QA Engineer",
                "goal": "Create comprehensive test plans and ensure software quality",
                "backstory": "You are an experienced QA Engineer expert in testing strategies.",
                "verbose": True,
                "allow_delegation": False,
                "model": "openai/gpt-4",
            }
        }

    def _create_crew_agent(self) -> Agent:
        """Create CrewAI agent for Tester.

        Returns:
            Configured CrewAI Agent
        """
        agent_config = self.config.get("agent", {})
        tools = get_tester_tools()

        agent = Agent(
            role=agent_config.get("role", "QA Engineer"),
            goal=agent_config.get(
                "goal",
                "Create comprehensive test plans and ensure software quality"
            ),
            backstory=agent_config.get(
                "backstory",
                "You are an experienced QA Engineer expert in testing strategies."
            ),
            verbose=agent_config.get("verbose", True),
            allow_delegation=agent_config.get("allow_delegation", False),
            llm=agent_config.get("model", "openai/gpt-4"),
            tools=tools if tools else None,
        )

        return agent

    def _determine_task_type(self, content: str) -> str:
        """Determine what type of testing task to perform.

        Args:
            content: User message content

        Returns:
            Task type: 'validate', 'test_cases', or 'test_plan'
        """
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in ["validate", "verify", "check compliance"]):
            return "validate"
        elif any(keyword in content_lower for keyword in ["test cases", "scenarios", "specific tests"]):
            return "test_cases"
        else:
            return "test_plan"

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router.

        Args:
            task: TaskContext with user message and metadata

        Returns:
            TaskResult with test plan/cases response
        """
        try:
            # Check if this is auto-triggered from story status change
            if task.context.get("trigger_type") == "status_review":
                return await self._handle_story_review_testing(task)
            
            # Otherwise, handle as manual @Tester mention (legacy flow)
            return await self._handle_manual_request(task)

        except Exception as e:
            logger.error(f"[{self.name}] Error handling task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e),
            )
    
    async def _handle_manual_request(self, task: TaskContext) -> TaskResult:
        """Handle manual @Tester mention (legacy flow).
        
        Args:
            task: TaskContext with user message
            
        Returns:
            TaskResult with test plan text response
        """
        user_message = task.content

        logger.info(f"[{self.name}] Processing manual QA task: {user_message[:50]}...")

        # Determine task type
        task_type = self._determine_task_type(user_message)
        logger.info(f"[{self.name}] Task type determined: {task_type}")

        # Create context for task creation
        context = {
            "user_message": user_message,
            "task_description": user_message,
        }

        # Create appropriate task based on type
        if task_type == "validate":
            crew_task = create_validate_requirements_task(self.crew_agent, context)
        elif task_type == "test_cases":
            crew_task = create_test_cases_task(self.crew_agent, context)
        else:
            crew_task = create_test_plan_task(self.crew_agent, context)

        # Execute crew
        crew = Crew(
            agents=[self.crew_agent],
            tasks=[crew_task],
            verbose=True,
        )

        # Run CrewAI asynchronously
        result = await crew.kickoff_async(inputs={})

        # Extract response
        response = str(result)

        logger.info(f"[{self.name}] Test plan completed: {len(response)} chars")

        return TaskResult(
            success=True,
            output=response,
            structured_data={
                "task_type": task.task_type.value,
                "routing_reason": task.routing_reason,
                "qa_type": task_type,
            },
            requires_approval=False,
        )
    
    async def _handle_story_review_testing(self, task: TaskContext) -> TaskResult:
        """Handle auto-triggered integration test generation for stories in REVIEW.
        
        This is triggered automatically when stories move to REVIEW status.
        Generates integration tests for ALL stories currently in REVIEW status.
        
        Args:
            task: TaskContext with trigger_type="status_review"
            
        Returns:
            TaskResult with generated test file info
        """
        story_ids = task.context.get("story_ids", [])
        
        if not story_ids:
            logger.warning(f"[{self.name}] No story_ids in context for review testing")
            return TaskResult(
                success=False,
                error_message="No stories to generate tests for"
            )
        
        logger.info(
            f"[{self.name}] Auto-triggered: Generating integration tests for "
            f"{len(story_ids)} story(ies) in REVIEW status"
        )
        
        # Send "working on it" message
        await self.message_user(
            "thinking",
            f"🧪 Story moved to REVIEW. Generating integration tests (API + DB verification)..."
        )
        
        # Check if project path is available
        if not self.project_path:
            logger.error(f"[{self.name}] No project_path available for test generation")
            await self.message_user(
                "response",
                "❌ Cannot generate tests: project path not configured. "
                "Please contact admin to set up project directory."
            )
            return TaskResult(
                success=False,
                error_message="Project path not configured"
            )
        
        try:
            # Use TesterCrew to generate integration tests
            result = await self.crew.generate_tests_from_stories(
                project_id=str(self.project_id),
                story_ids=story_ids,
                project_path=self.project_path,
                tech_stack=self.tech_stack
            )
            
            # Check for errors
            if result.get("error"):
                logger.error(f"[{self.name}] TesterCrew error: {result['error']}")
                await self.message_user(
                    "response",
                    f"⚠️ Test generation encountered issues:\n{result['error']}\n\n"
                    f"Raw output: {result.get('raw_output', 'N/A')[:500]}"
                )
                return TaskResult(
                    success=False,
                    error_message=result['error']
                )
            
            # Extract result info
            test_file = result.get("filename") or result.get("test_file")
            test_count = result.get("test_count", 0)
            stories_covered = result.get("stories_covered", [])
            
            # Send success message to user
            await self.message_user(
                "response",
                f"✅ Integration tests generated!\n\n"
                f"📁 **File:** `tests/integration/{test_file}`\n"
                f"📝 **Tests created:** {test_count} test cases\n"
                f"📋 **Stories covered:** {len(stories_covered)}\n\n"
                f"🧪 **Run tests:** `npm test tests/integration/`\n\n"
                f"Tests verify both API responses and database state changes.",
                {
                    "message_type": "tests_generated",
                    "test_file": test_file,
                    "test_count": test_count,
                    "story_ids": story_ids,
                    "stories_covered": stories_covered
                }
            )
            
            logger.info(
                f"[{self.name}] Successfully generated {test_count} integration tests "
                f"in file {test_file}"
            )
            
            return TaskResult(
                success=True,
                output=f"Generated integration tests: {test_file}",
                structured_data={
                    "test_file": test_file,
                    "test_count": test_count,
                    "stories_covered": stories_covered,
                    "trigger_type": "auto_review"
                }
            )
        
        except Exception as e:
            logger.error(
                f"[{self.name}] Error generating integration tests: {e}",
                exc_info=True
            )
            await self.message_user(
                "response",
                f"❌ Failed to generate integration tests: {str(e)}\n\n"
                f"Please check logs or contact admin."
            )
            return TaskResult(
                success=False,
                error_message=str(e)
            )
