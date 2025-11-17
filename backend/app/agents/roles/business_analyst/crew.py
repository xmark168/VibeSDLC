"""Business Analyst Crew - Requirements analysis and PRD generation.

This crew analyzes requirements and creates detailed documentation.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from crewai import Agent, Task

from app.agents.roles.base_crew import BaseAgentCrew
from app.agents.roles.business_analyst.tasks import (
    create_analyze_requirements_task,
    create_prd_task,
)
from app.agents.roles.business_analyst.tools import get_ba_tools

logger = logging.getLogger(__name__)


class BusinessAnalystCrew(BaseAgentCrew):
    """Business Analyst Crew - creates requirements documents and user stories.

    This crew:
    1. Analyzes user requirements
    2. Creates user stories with acceptance criteria
    3. Generates PRDs when requested
    4. Provides story point estimates
    """

    @property
    def crew_name(self) -> str:
        return "Business Analyst"

    @property
    def agent_type(self) -> str:
        return "business_analyst"

    def _get_default_config_path(self) -> Path:
        """Get default config path for Business Analyst."""
        return Path(__file__).parent / "config.yaml"

    def create_agent(self) -> Agent:
        """Create the Business Analyst agent.

        Returns:
            Configured CrewAI Agent for requirements analysis
        """
        agent_config = self.config.get("agent", {})
        tools = get_ba_tools()

        self.agent = Agent(
            role=agent_config.get("role", "Business Analyst"),
            goal=agent_config.get(
                "goal",
                "Analyze requirements and create detailed PRDs and user stories"
            ),
            backstory=agent_config.get(
                "backstory",
                "You are a skilled Business Analyst expert in requirements gathering."
            ),
            verbose=agent_config.get("verbose", True),
            allow_delegation=agent_config.get("allow_delegation", False),
            llm=agent_config.get("model", "openai/gpt-4.1"),
            tools=tools if tools else None,
        )

        return self.agent

    def create_tasks(self, context: Dict[str, Any]) -> list[Task]:
        """Create tasks for the Business Analyst crew.

        Determines task type based on context:
        - If 'prd' or 'document' keywords: create PRD
        - Otherwise: analyze requirements and create user story

        Args:
            context: Context containing task_description

        Returns:
            List of tasks for the crew
        """
        if self.agent is None:
            self.create_agent()

        task_description = context.get("task_description", "").lower()

        # Determine task type based on keywords
        if any(keyword in task_description for keyword in ["prd", "product requirements document", "comprehensive document"]):
            return [create_prd_task(self.agent, context)]
        else:
            # Default: requirements analysis and user story creation
            return [create_analyze_requirements_task(self.agent, context)]

    async def execute(
        self,
        context: Dict[str, Any],
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute Business Analyst workflow.

        Args:
            context: Context with task_description
            project_id: Optional project ID
            user_id: Optional user ID

        Returns:
            Result with requirements analysis
        """
        # Execute base workflow
        result = await super().execute(context, project_id, user_id)

        if result.get("success"):
            # Publish the analysis as a response
            await self.publish_response(
                content=result.get("output", ""),
                message_id=context.get("message_id", UUID(int=0)),
                project_id=project_id,
                user_id=user_id,
                structured_data={
                    "analysis_type": "requirements_analysis",
                    "task_description": context.get("task_description", ""),
                },
            )

            logger.info("Business Analyst completed requirements analysis")

        return result
