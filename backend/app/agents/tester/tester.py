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

        # Create CrewAI agent
        self.crew_agent = self._create_crew_agent()

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
            user_message = task.content

            logger.info(f"[{self.name}] Processing QA task: {user_message[:50]}...")

            # Status update
            await self.message_user("thinking", "Creating test plan...")

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

            # Run CrewAI asynchronously using native async support
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

        except Exception as e:
            logger.error(f"[{self.name}] Error handling task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e),
            )
