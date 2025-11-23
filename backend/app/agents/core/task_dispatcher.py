"""Task Dispatcher - Central task routing and assignment."""

import logging
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.kafka.producer import get_kafka_producer
from app.kafka.event_schemas import AgentTaskAssignedEvent, KafkaTopics
from app.models import Agent
from app.core.db import engine

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """Central service for task routing and assignment to agents.

    Handles:
    - Direct task assignment to specific agent
    - Broadcast to all agents of a role type
    - Agent selection (load balancing, capability matching)
    """

    async def assign_task(
        self,
        task: AgentTaskAssignedEvent,
        agent_id: UUID,
        project_id: UUID
    ) -> bool:
        """Assign task to a specific agent.

        Args:
            task: Task to assign
            agent_id: Target agent UUID
            project_id: Project UUID

        Returns:
            True if assigned successfully
        """
        try:
            producer = await get_kafka_producer()

            # Set agent and project IDs
            task.agent_id = agent_id
            task.project_id = project_id

            # Publish to AGENT_TASKS (will partition by agent_id)
            success = await producer.publish(KafkaTopics.AGENT_TASKS, task)

            if success:
                logger.info(
                    f"Assigned task {task.task_id} ({task.task_type}) "
                    f"to agent {agent_id} in project {project_id}"
                )
            return success

        except Exception as e:
            logger.error(f"Failed to assign task: {e}")
            return False

    async def broadcast_to_role(
        self,
        task: AgentTaskAssignedEvent,
        role_type: str,
        project_id: UUID
    ) -> bool:
        """Broadcast task to agents of a specific role type in project.

        Selects best agent using load balancing.

        Args:
            task: Task to broadcast
            role_type: Agent role type (e.g., "developer", "tester")
            project_id: Project UUID

        Returns:
            True if broadcasted successfully
        """
        try:
            # Query agents by role and project
            with Session(engine) as db_session:
                agents = db_session.exec(
                    select(Agent)
                    .where(Agent.project_id == project_id)
                    .where(Agent.role_type == role_type)
                    .where(Agent.status == "idle")  # Only idle agents
                ).all()

            if not agents:
                logger.warning(
                    f"No idle {role_type} agents found in project {project_id}"
                )
                return False

            # Select best agent (simple: first idle agent)
            selected_agent = self._select_agent(list(agents), task)

            # Assign to selected agent
            return await self.assign_task(task, selected_agent.id, project_id)

        except Exception as e:
            logger.error(f"Failed to broadcast task: {e}")
            return False

    def _select_agent(
        self,
        agents: List[Agent],
        task: AgentTaskAssignedEvent
    ) -> Agent:
        """Select best agent for task.

        Current strategy: Simple round-robin (first idle agent).
        Future: Load balancing, capability matching, priority queue.

        Args:
            agents: List of candidate agents
            task: Task to assign

        Returns:
            Selected agent
        """
        # Simple: return first agent
        # TODO: Implement load balancing, capability matching
        return agents[0]


# Global singleton instance
_dispatcher_instance: Optional[TaskDispatcher] = None


async def get_task_dispatcher() -> TaskDispatcher:
    """Get global TaskDispatcher instance.

    Returns:
        TaskDispatcher singleton
    """
    global _dispatcher_instance
    if _dispatcher_instance is None:
        _dispatcher_instance = TaskDispatcher()
    return _dispatcher_instance
