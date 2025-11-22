"""Agent Orchestrator Service - Refactored for dynamic per-agent consumers.

Central service that manages all agent instances and their lifecycle.
This orchestrator:
1. Loads agent instances from database on startup
2. Creates BaseAgentRole instance for each agent
3. Starts Kafka consumers for each agent
4. Manages agent lifecycle
5. Integrates with FastAPI app startup/shutdown
"""

import asyncio
import logging
from typing import Dict, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.agents.roles.team_leader import TeamLeaderRole
from app.agents.roles.business_analyst import BusinessAnalystRole
from app.agents.roles.tester import TesterRole
from app.models import Agent as AgentModel, Project
from app.core.db import engine
from app.agents.core.base_role import BaseAgentRole

logger = logging.getLogger(__name__)


# Mapping of role_type to Role class
ROLE_CLASS_MAP = {
    "team_leader": TeamLeaderRole,
    "business_analyst": BusinessAnalystRole,
    "tester": TesterRole,
    "developer": None,  # TODO: Add DeveloperRole when ready
}


class AgentOrchestrator:
    """Central orchestrator for all agent instances.

    Manages:
    - Dynamic loading of agents from database
    - Per-agent BaseAgentRole instances
    - Per-agent Kafka consumers
    - Agent lifecycle (start/stop)

    Flow:
    1. User message → published to project_{project_id}_messages topic
    2. All agents in that project listen to the topic
    3. Agent with matching agent_id (or Team Leader if no match) processes message
    4. Agent publishes response back to WebSocket
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self._running = False
        self._agent_roles: Dict[UUID, BaseAgentRole] = {}  # agent_id -> BaseAgentRole instance
        logger.info("Agent Orchestrator initialized (dynamic architecture)")

    async def start(self) -> None:
        """Start orchestrator and load all agents from database.

        This loads ALL agent instances from the database and starts their consumers.
        """
        if self._running:
            logger.warning("Agent Orchestrator already running")
            return

        logger.info("Starting Agent Orchestrator (loading agents from database)...")

        try:
            # Load all agents from database
            with Session(engine) as db_session:
                # Query all active agents
                agents = db_session.exec(
                    select(AgentModel)
                    .where(AgentModel.status != "stopped")
                ).all()

                logger.info(f"Found {len(agents)} active agents in database")

                # Start each agent
                for agent in agents:
                    try:
                        await self.start_agent(agent, db_session)
                    except Exception as e:
                        logger.error(
                            f"Failed to start agent {agent.human_name} ({agent.id}): {e}",
                            exc_info=True
                        )

            self._running = True
            logger.info(
                f"Agent Orchestrator started successfully - {len(self._agent_roles)} agents running"
            )

        except Exception as e:
            logger.error(f"Failed to start Agent Orchestrator: {e}", exc_info=True)
            raise

    async def start_agent(self, agent: AgentModel, db_session: Optional[Session] = None) -> bool:
        """Start a specific agent instance.

        Args:
            agent: Agent model from database
            db_session: Optional database session

        Returns:
            True if started successfully
        """
        try:
            # Check if already running
            if agent.id in self._agent_roles:
                logger.warning(f"Agent {agent.human_name} ({agent.id}) already running")
                return False

            # Get role class for this agent type
            role_class = ROLE_CLASS_MAP.get(agent.role_type)
            if not role_class:
                logger.warning(
                    f"No role class found for agent type '{agent.role_type}', skipping agent {agent.id}"
                )
                return False

            # Create role instance
            role_instance = role_class(agent_model=agent)

            # Start the role (which starts consumer)
            success = await role_instance.start()

            if success:
                self._agent_roles[agent.id] = role_instance
                logger.info(
                    f"✓ Started agent: {agent.human_name} ({agent.role_type}) "
                    f"for project {agent.project_id}"
                )
                return True
            else:
                logger.error(f"Failed to start agent {agent.human_name}")
                return False

        except Exception as e:
            logger.error(f"Error starting agent {agent.id}: {e}", exc_info=True)
            return False

    async def stop_agent(self, agent_id: UUID) -> bool:
        """Stop a specific agent instance.

        Args:
            agent_id: UUID of the agent to stop

        Returns:
            True if stopped successfully
        """
        try:
            role_instance = self._agent_roles.get(agent_id)
            if not role_instance:
                logger.warning(f"Agent {agent_id} not found in running agents")
                return False

            # Stop the role (which stops consumer)
            success = await role_instance.stop()

            if success:
                del self._agent_roles[agent_id]
                logger.info(f"✓ Stopped agent {agent_id}")
                return True
            else:
                logger.error(f"Failed to stop agent {agent_id}")
                return False

        except Exception as e:
            logger.error(f"Error stopping agent {agent_id}: {e}", exc_info=True)
            return False

    async def stop(self) -> None:
        """Stop all agent instances."""
        if not self._running:
            return

        logger.info("Stopping Agent Orchestrator...")

        try:
            # Stop all agents
            agent_ids = list(self._agent_roles.keys())
            for agent_id in agent_ids:
                await self.stop_agent(agent_id)

            self._agent_roles.clear()
            self._running = False

            logger.info("Agent Orchestrator stopped")

        except Exception as e:
            logger.error(f"Error stopping Agent Orchestrator: {e}", exc_info=True)

    @property
    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self._running

    def get_agent_status(self, agent_id: UUID) -> Optional[Dict]:
        """Get status of a specific agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            Agent status dictionary or None if not found
        """
        role_instance = self._agent_roles.get(agent_id)
        if not role_instance:
            return None

        return {
            "agent_id": str(agent_id),
            "role_name": role_instance.role_name,
            "agent_type": role_instance.agent_type,
            "state": role_instance.state.value,
            "project_id": str(role_instance.project_id) if role_instance.project_id else None,
            "human_name": role_instance.human_name,
            "running": role_instance.state.value in ["running", "idle", "busy"],
        }

    def get_all_agent_status(self) -> Dict[UUID, Dict]:
        """Get status of all running agents.

        Returns:
            Dictionary mapping agent_id to status dict
        """
        return {
            agent_id: self.get_agent_status(agent_id)
            for agent_id in self._agent_roles.keys()
        }


# Global orchestrator instance
_orchestrator_instance: Optional[AgentOrchestrator] = None


async def get_orchestrator() -> AgentOrchestrator:
    """Get the global orchestrator instance.

    Returns:
        Initialized AgentOrchestrator singleton
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance


async def start_orchestrator() -> None:
    """Start the global orchestrator instance."""
    orchestrator = await get_orchestrator()
    await orchestrator.start()


async def stop_orchestrator() -> None:
    """Stop the global orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance:
        await _orchestrator_instance.stop()
        _orchestrator_instance = None
