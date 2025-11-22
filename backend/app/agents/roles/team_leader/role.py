"""Team Leader Role - Bridge between BaseAgentRole and TeamLeaderCrew.

This class wraps the existing TeamLeaderCrew and integrates it with
the new consumer-based architecture.
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID
from pathlib import Path

from crewai import Agent, Task

from app.agents.core.base_role import BaseAgentRole
from app.agents.core.base_agent_consumer import BaseAgentInstanceConsumer
from app.agents.roles.team_leader.crew import TeamLeaderCrew
from app.models import Agent as AgentModel

logger = logging.getLogger(__name__)


class TeamLeaderConsumer(BaseAgentInstanceConsumer):
    """Consumer for Team Leader agent instances."""

    def __init__(self, agent: AgentModel, crew: TeamLeaderCrew):
        """Initialize Team Leader consumer.

        Args:
            agent: Agent model from database
            crew: TeamLeaderCrew instance
        """
        super().__init__(agent)
        self.crew = crew

    async def process_user_message(self, message_data: Dict[str, Any]) -> None:
        """Process user message for Team Leader.

        Team Leader analyzes the message and decides whether to:
        1. Respond directly (for simple messages)
        2. Delegate to specialist agents

        Args:
            message_data: Message data dictionary
        """
        try:
            message_id = message_data.get("message_id")
            project_id = message_data.get("project_id")
            user_id = message_data.get("user_id")
            content = message_data.get("content", "")

            logger.info(
                f"Team Leader {self.human_name} processing message {message_id}: '{content[:50]}...'"
            )

            # Execute crew
            context = {
                "user_message": content,
                "message_id": str(message_id),
                "message_type": message_data.get("message_type", "text"),
            }

            result = await self.crew.execute(
                context=context,
                project_id=UUID(project_id) if isinstance(project_id, str) else project_id,
                user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
            )

            if result.get("success"):
                logger.info(
                    f"Team Leader successfully handled message {message_id}: "
                    f"{result.get('delegation', 'direct response')}"
                )
            else:
                logger.error(f"Team Leader execution failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error in Team Leader processing message: {e}", exc_info=True)


class TeamLeaderRole(BaseAgentRole):
    """Team Leader role that bridges BaseAgentRole with TeamLeaderCrew."""

    def __init__(self, agent_model: Optional[AgentModel] = None, **kwargs):
        """Initialize Team Leader role.

        Args:
            agent_model: Agent database model instance
            **kwargs: Additional arguments for BaseAgentRole
        """
        super().__init__(agent_model=agent_model, **kwargs)

        # Create crew instance
        self.team_leader_crew = TeamLeaderCrew()

    # ===== BaseAgentRole Abstract Properties =====

    @property
    def role_name(self) -> str:
        return "TeamLeader"

    @property
    def agent_type(self) -> str:
        return "team_leader"

    @property
    def kafka_topic(self) -> str:
        """This is deprecated - using project-specific topics now."""
        from app.kafka.event_schemas import get_project_topic
        if self.project_id:
            return get_project_topic(self.project_id)
        return "unknown"

    # ===== BaseAgentRole Abstract Methods =====

    def create_agent(self) -> Agent:
        """Create CrewAI agent."""
        return self.team_leader_crew.create_agent()

    def create_tasks(self, context: Dict[str, Any]) -> list[Task]:
        """Create tasks for execution."""
        return self.team_leader_crew.create_tasks(context)

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process message (called by consumer)."""
        return await self.team_leader_crew.execute(
            context={"user_message": message.get("content", "")},
            project_id=message.get("project_id"),
            user_id=message.get("user_id"),
        )

    def _create_consumer(self) -> Optional[BaseAgentInstanceConsumer]:
        """Create consumer for this Team Leader instance.

        Returns:
            TeamLeaderConsumer instance
        """
        if not self.agent_model:
            logger.warning("Cannot create consumer without agent_model")
            return None

        return TeamLeaderConsumer(self.agent_model, self.team_leader_crew)
