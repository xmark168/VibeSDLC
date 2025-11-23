"""Tester Crew - QA planning, test case creation, and quality assurance.

This crew creates test plans and ensures software quality.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from crewai import Agent, Task

from app.agents.base_crew import BaseAgentCrew
from app.agents.tester.tasks import (
    create_test_plan_task,
    create_validate_requirements_task,
    create_test_cases_task,
)
from app.agents.tester.tools import get_tester_tools

logger = logging.getLogger(__name__)


class TesterCrew(BaseAgentCrew):
    """Tester Crew - creates test plans and ensures software quality.

    This crew:
    1. Creates comprehensive test plans
    2. Generates detailed test cases
    3. Validates implementations against requirements
    4. Identifies edge cases and security concerns
    """

    @property
    def crew_name(self) -> str:
        return "QA Engineer"

    @property
    def agent_type(self) -> str:
        return "tester"

    def _get_default_config_path(self) -> Path:
        """Get default config path for Tester."""
        return Path(__file__).parent / "config.yaml"

    def create_agent(self) -> Agent:
        """Create the Tester agent.

        Returns:
            Configured CrewAI Agent for QA testing
        """
        agent_config = self.config.get("agent", {})
        tools = get_tester_tools()

        self.agent = Agent(
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
            llm=agent_config.get("model", "openai/gpt-4.1"),
            tools=tools if tools else None,
        )

        return self.agent

    def create_tasks(self, context: Dict[str, Any]) -> list[Task]:
        """Create tasks for the Tester crew.

        Determines task type based on context:
        - If 'validate' or 'verify' keywords: validation task
        - If 'test cases' or 'scenarios' keywords: test case generation
        - Otherwise: comprehensive test plan

        Args:
            context: Context containing task_description

        Returns:
            List of tasks for the crew
        """
        if self.agent is None:
            self.create_agent()

        task_description = context.get("task_description", "").lower()

        # Determine task type based on keywords
        if any(keyword in task_description for keyword in ["validate", "verify", "check compliance"]):
            return [create_validate_requirements_task(self.agent, context)]
        elif any(keyword in task_description for keyword in ["test cases", "scenarios", "specific tests"]):
            return [create_test_cases_task(self.agent, context)]
        else:
            # Default: comprehensive test plan
            return [create_test_plan_task(self.agent, context)]

    async def execute(
        self,
        context: Dict[str, Any],
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute Tester workflow.

        Args:
            context: Context with task_description
            project_id: Optional project ID
            user_id: Optional user ID

        Returns:
            Result with test plan/cases
        """
        # Step 1: Analyzing requirements
        await self._publish_progress(
            step_number=1,
            total_steps=4,
            description="Đang phân tích requirements...",
            project_id=project_id,
        )

        # Step 2: Identifying test scenarios
        await self._publish_progress(
            step_number=2,
            total_steps=4,
            description="Đang xác định test scenarios...",
            project_id=project_id,
        )

        # Execute base workflow
        result = await super().execute(context, project_id, user_id)

        # Step 3: Creating test cases
        await self._publish_progress(
            step_number=3,
            total_steps=4,
            description="Đang tạo test cases...",
            project_id=project_id,
        )

        if result.get("success"):
            # Step 4: Preparing test plan
            await self._publish_progress(
                step_number=4,
                total_steps=4,
                description="Đang chuẩn bị test plan...",
                project_id=project_id,
            )

            # Publish the test plan as a response
            await self.publish_response(
                content=result.get("output", ""),
                message_id=context.get("message_id", UUID(int=0)),
                project_id=project_id,
                user_id=user_id,
                structured_data={
                    "qa_type": "test_planning",
                    "task_description": context.get("task_description", ""),
                },
            )

            # Mark as completed
            await self._publish_progress(
                step_number=4,
                total_steps=4,
                description="Hoàn thành",
                status="completed",
                project_id=project_id,
            )

            logger.info("Tester completed QA task")

        return result
