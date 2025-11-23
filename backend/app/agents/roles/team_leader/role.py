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

    async def process_task(self, task_data: Dict[str, Any]) -> None:
        """Process task assigned by Central Message Router.

        Team Leader analyzes the task (usually user messages) and decides whether to:
        1. Respond directly (for simple messages)
        2. Delegate to specialist agents (delegation no longer happens here - Router handles it)

        Args:
            task_data: RouterTaskEvent data containing task and context
        """
        try:
            # Extract task metadata
            task_id = task_data.get("task_id")
            source_event_type = task_data.get("source_event_type")
            routing_reason = task_data.get("routing_reason")

            # Extract context (original event data)
            context_data = task_data.get("context", {})

            message_id = context_data.get("message_id")
            project_id = context_data.get("project_id")
            user_id = context_data.get("user_id")
            content = context_data.get("content", "")
            message_type = context_data.get("message_type", "text")

            logger.info(
                f"Team Leader {self.human_name} processing task {task_id} "
                f"(source: {source_event_type}, reason: {routing_reason}): '{content[:50]}...'"
            )

            # Execute crew
            crew_context = {
                "user_message": content,
                "message_id": str(message_id),
                "message_type": message_type,
                "routing_reason": routing_reason,
            }

            result = await self.crew.execute(
                context=crew_context,
                project_id=UUID(project_id) if isinstance(project_id, str) else project_id,
                user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
            )

            if result.get("success"):
                logger.info(
                    f"Team Leader successfully handled task {task_id}: "
                    f"{result.get('delegation', 'direct response')}"
                )
            else:
                logger.error(f"Team Leader execution failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error in Team Leader processing task: {e}", exc_info=True)


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
