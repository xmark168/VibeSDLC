"""Agent Pool Manager for dynamic agent lifecycle management.

"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Type
from uuid import UUID, uuid4

from sqlmodel import Session

from app.agents.core.base_role import BaseAgentRole
from app.models import AgentStatus, Agent as AgentModel
from app.core.db import engine

logger = logging.getLogger(__name__)


class AgentPoolConfig:
    """Configuration for agent pool."""

    def __init__(
        self,
        max_agents: int = 10,
        health_check_interval: int = 60,
    ):
        """Initialize pool configuration.

        Args:
            max_agents: Maximum number of agents allowed
            health_check_interval: Seconds between health checks
        """
        self.max_agents = max_agents
        self.health_check_interval = health_check_interval


class AgentPool:
    """Manages a pool of agent instances for a specific role.

    Features:
    - Manual agent spawning/stopping via API
    - Load balancing (round-robin, least-busy)
    - Health monitoring
    - Resource cleanup
    """

    def __init__(
        self,
        role_class: Type[BaseAgentRole],
        pool_name: str,
        config: Optional[AgentPoolConfig] = None,
    ):
        """Initialize agent pool.

        Args:
            role_class: Agent role class to instantiate
            pool_name: Unique pool name
            config: Pool configuration
        """
        self.role_class = role_class
        self.pool_name = pool_name
        self.config = config or AgentPoolConfig()

        # Agent tracking
        self.agents: Dict[UUID, BaseAgentRole] = {}
        self.agent_stats: Dict[UUID, Dict] = {}

        # Pool state
        self.created_at = datetime.now(timezone.utc)
        self.total_spawned = 0
        self.total_terminated = 0

        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        logger.info(f"AgentPool '{pool_name}' created for role {role_class.__name__}")

    async def start(self) -> bool:
        """Start the agent pool and background services.

        Returns:
            True if started successfully
        """
        try:
            # Start monitor (no auto-spawn, agents are created via API)
            self._monitor_task = asyncio.create_task(self._monitor_loop())

            logger.info(f"AgentPool '{self.pool_name}' started")
            return True

        except Exception as e:
            logger.error(f"Failed to start pool '{self.pool_name}': {e}", exc_info=True)
            return False

    async def stop(self, graceful: bool = True) -> bool:
        """Stop the agent pool and all agents.

        Args:
            graceful: If True, wait for agents to finish

        Returns:
            True if stopped successfully
        """
        try:
            self._shutdown_event.set()

            # Stop background tasks
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            # Stop all agents
            agent_ids = list(self.agents.keys())
            stop_tasks = [self.terminate_agent(agent_id, graceful) for agent_id in agent_ids]
            results = await asyncio.gather(*stop_tasks, return_exceptions=True)

            # Log any failures
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to terminate agent during pool shutdown: {result}")

            # Bulk update all agent states to 'stopped' in DB as a safety net
            # This ensures state is persisted even if individual sync tasks didn't complete
            if agent_ids:
                try:
                    from sqlmodel import Session, update
                    from app.core.db import engine
                    from app.models import Agent as AgentModel, AgentStatus

                    with Session(engine) as db_session:
                        stmt = (
                            update(AgentModel)
                            .where(AgentModel.id.in_(agent_ids))
                            .values(status=AgentStatus.stopped)
                        )
                        db_session.exec(stmt)
                        db_session.commit()
                        logger.info(f"Bulk updated {len(agent_ids)} agents to 'stopped' status in pool '{self.pool_name}'")
                except Exception as e:
                    logger.error(f"Failed to bulk update agent states during shutdown: {e}")

            logger.info(f"AgentPool '{self.pool_name}' stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop pool '{self.pool_name}': {e}", exc_info=True)
            return False

    # ===== Agent Management =====

    async def spawn_agent(
        self,
        agent_id: UUID,
        heartbeat_interval: int = 30,
        max_idle_time: int = 300,
    ) -> Optional[BaseAgentRole]:
        """Spawn a new agent instance from database.

        This method loads the agent from database and creates a runtime instance
        with full Kafka consumer support.

        Args:
            agent_id: Agent ID (must exist in database)
            heartbeat_interval: Heartbeat interval in seconds
            max_idle_time: Max idle time in seconds

        Returns:
            Agent instance if spawned successfully, None otherwise
        """
        if len(self.agents) >= self.config.max_agents:
            logger.warning(f"Pool '{self.pool_name}' at max capacity ({self.config.max_agents})")
            return None

        try:
            # Load agent from database
            with Session(engine) as db_session:
                agent_model = db_session.get(AgentModel, agent_id)

                if not agent_model:
                    logger.error(f"Agent {agent_id} not found in database")
                    return None

                # Verify agent isn't already in pool
                if agent_id in self.agents:
                    logger.warning(f"Agent {agent_id} already exists in pool '{self.pool_name}'")
                    return None

                # Create agent instance with agent_model (enables Kafka consumer)
                agent = self.role_class(
                    agent_model=agent_model,
                    heartbeat_interval=heartbeat_interval,
                    max_idle_time=max_idle_time,
                )

                # Set up callbacks
                agent.on_state_change = self._on_agent_state_change
                agent.on_execution_complete = self._on_agent_execution_complete
                agent.on_heartbeat = self._on_agent_heartbeat

                # Start agent (starts Kafka consumer + heartbeat)
                if await agent.start():
                    self.agents[agent.agent_id] = agent
                    self.agent_stats[agent.agent_id] = {
                        "spawned_at": datetime.now(timezone.utc),
                        "executions": 0,
                        "last_execution": None,
                    }
                    self.total_spawned += 1

                    logger.info(
                        f"✓ Spawned agent: {agent_model.human_name} ({agent_id}) "
                        f"in pool '{self.pool_name}' with Kafka consumer enabled"
                    )
                    return agent
                else:
                    logger.error(f"Failed to start agent {agent_id}")
                    return None

        except Exception as e:
            logger.error(f"Failed to spawn agent {agent_id}: {e}", exc_info=True)
            return None

    async def terminate_agent(self, agent_id: UUID, graceful: bool = True) -> bool:
        """Terminate an agent instance.

        Args:
            agent_id: Agent ID to terminate
            graceful: If True, wait for agent to finish

        Returns:
            True if terminated successfully
        """
        agent = self.agents.get(agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found in pool '{self.pool_name}'")
            return False

        try:
            # Stop agent
            await agent.stop(graceful=graceful)

            # Remove from pool
            del self.agents[agent_id]
            del self.agent_stats[agent_id]
            self.total_terminated += 1

            logger.info(f"Agent {agent_id} terminated from pool '{self.pool_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to terminate agent {agent_id}: {e}", exc_info=True)
            return False

    async def get_agent(self, strategy: str = "round_robin") -> Optional[BaseAgentRole]:
        """Get an available agent from the pool.

        Args:
            strategy: Load balancing strategy ('round_robin', 'least_busy', 'random')

        Returns:
            Available agent or None
        """
        available_agents = [
            agent for agent in self.agents.values()
            if agent.state == AgentStatus.idle
        ]

        if not available_agents:
            logger.warning(f"No available agents in pool '{self.pool_name}'")
            return None

        if strategy == "least_busy":
            # Find agent with fewest executions
            return min(available_agents, key=lambda a: a.total_executions)
        elif strategy == "random":
            import random
            return random.choice(available_agents)
        else:  # round_robin (default)
            return available_agents[0]

    # ===== Pool Statistics =====

    def get_pool_stats(self) -> Dict:
        """Get pool statistics.

        Returns:
            Pool statistics dictionary
        """
        idle_agents = sum(1 for a in self.agents.values() if a.state == AgentStatus.idle)
        busy_agents = sum(1 for a in self.agents.values() if a.state == AgentStatus.busy)
        active_agents = idle_agents + busy_agents  # Active = IDLE + BUSY
        total_executions = sum(a.total_executions for a in self.agents.values())
        total_successful = sum(a.successful_executions for a in self.agents.values())
        total_failed = sum(a.failed_executions for a in self.agents.values())

        return {
            "pool_name": self.pool_name,
            "role_class": self.role_class.__name__,
            "total_agents": len(self.agents),
            "active_agents": active_agents,
            "busy_agents": busy_agents,
            "idle_agents": idle_agents,
            "total_spawned": self.total_spawned,
            "total_terminated": self.total_terminated,
            "total_executions": total_executions,
            "successful_executions": total_successful,
            "failed_executions": total_failed,
            "success_rate": total_successful / total_executions if total_executions > 0 else 0,
            "load": busy_agents / len(self.agents) if len(self.agents) > 0 else 0,
            "created_at": self.created_at.isoformat(),
        }

    async def get_all_agent_health(self) -> List[Dict]:
        """Get health status of all agents.

        Returns:
            List of health status dictionaries
        """
        health_checks = [agent.health_check() for agent in self.agents.values()]
        return await asyncio.gather(*health_checks, return_exceptions=True)

    # ===== Background Tasks =====

    async def _monitor_loop(self) -> None:
        """Monitor agent health and cleanup unhealthy agents."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.health_check_interval)

                # Check each agent
                for agent_id, agent in list(self.agents.items()):
                    health = await agent.health_check()

                    # Terminate if unhealthy
                    if not health["healthy"]:
                        logger.warning(f"Agent {agent_id} unhealthy, terminating")
                        await self.terminate_agent(agent_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}", exc_info=True)

    # ===== Agent Callbacks =====

    async def _on_agent_state_change(self, agent: BaseAgentRole, old_state, new_state) -> None:
        """Callback when agent state changes."""
        logger.debug(f"Agent {agent.agent_id} state: {old_state} -> {new_state}")

    async def _on_agent_execution_complete(self, agent: BaseAgentRole, result: Dict) -> None:
        """Callback when agent completes execution."""
        if agent.agent_id in self.agent_stats:
            self.agent_stats[agent.agent_id]["executions"] += 1
            self.agent_stats[agent.agent_id]["last_execution"] = datetime.now(timezone.utc)

    async def _on_agent_heartbeat(self, agent: BaseAgentRole) -> None:
        """Callback on agent heartbeat."""
        # Can be used for monitoring/metrics
        pass
