"""Developer Crew - Code implementation and technical execution.

This crew implements features, fixes bugs, and provides technical solutions.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from crewai import Agent, Task

from app.agents.roles.base_crew import BaseAgentCrew
from app.agents.roles.developer.tasks import (
    create_implement_feature_task,
    create_code_review_task,
    create_bug_fix_task,
)
from app.agents.roles.developer.tools import get_developer_tools

logger = logging.getLogger(__name__)


class DeveloperCrew(BaseAgentCrew):
    """Developer Crew - implements code solutions and technical features.

    This crew:
    1. Implements new features based on requirements
    2. Reviews code for quality and security
    3. Fixes bugs and resolves technical issues
    4. Provides architecture guidance
    """

    @property
    def crew_name(self) -> str:
        return "Senior Developer"

    @property
    def agent_type(self) -> str:
        return "developer"

    def _get_default_config_path(self) -> Path:
        """Get default config path for Developer."""
        return Path(__file__).parent / "config.yaml"

    def create_agent(self) -> Agent:
        """Create the Developer agent.

        Returns:
            Configured CrewAI Agent for development
        """
        agent_config = self.config.get("agent", {})
        tools = get_developer_tools()

        self.agent = Agent(
            role=agent_config.get("role", "Senior Software Developer"),
            goal=agent_config.get(
                "goal",
                "Design and implement high-quality code solutions"
            ),
            backstory=agent_config.get(
                "backstory",
                "You are a senior developer expert in software implementation."
            ),
            verbose=agent_config.get("verbose", True),
            allow_delegation=agent_config.get("allow_delegation", False),
            llm=agent_config.get("model", "openai/gpt-4.1"),
            tools=tools if tools else None,
        )

        return self.agent

    def create_tasks(self, context: Dict[str, Any]) -> list[Task]:
        """Create tasks for the Developer crew.

        Determines task type based on context:
        - If 'review' or 'code review' keywords: code review task
        - If 'bug' or 'fix' keywords: bug fix task
        - Otherwise: feature implementation task

        Args:
            context: Context containing task_description

        Returns:
            List of tasks for the crew
        """
        if self.agent is None:
            self.create_agent()

        task_description = context.get("task_description", "").lower()

        # Determine task type based on keywords
        if any(keyword in task_description for keyword in ["review", "code review", "feedback on code"]):
            return [create_code_review_task(self.agent, context)]
        elif any(keyword in task_description for keyword in ["bug", "fix", "error", "issue"]):
            return [create_bug_fix_task(self.agent, context)]
        else:
            # Default: feature implementation
            return [create_implement_feature_task(self.agent, context)]

    async def execute(
        self,
        context: Dict[str, Any],
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute Developer workflow.

        Args:
            context: Context with task_description
            project_id: Optional project ID
            user_id: Optional user ID

        Returns:
            Result with implementation details
        """
        # Execute base workflow
        result = await super().execute(context, project_id, user_id)

        if result.get("success"):
            # Publish the implementation as a response
            await self.publish_response(
                content=result.get("output", ""),
                message_id=context.get("message_id", UUID(int=0)),
                project_id=project_id,
                user_id=user_id,
                structured_data={
                    "implementation_type": "code_implementation",
                    "task_description": context.get("task_description", ""),
                },
            )

            logger.info("Developer completed implementation task")

        return result
