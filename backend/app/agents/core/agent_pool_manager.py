import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from sqlmodel import Session, select, update

from app.agents.core.base_agent import BaseAgent
from app.models import Agent as AgentModel, AgentStatus
from app.core.db import engine

logger = logging.getLogger(__name__)


class AgentPoolManager:
    """In-memory agent pool manager.

    Manages agents directly in single process using asyncio.
    No multiprocessing, no Redis, no IPC complexity.

    Features:
    - Direct in-memory agent management
    - Single health monitor loop
    - Database as single source of truth
    - Graceful shutdown
    - Statistics tracking
    """

    def __init__(
        self,
        pool_name: str,
        max_agents: int = 100,
        health_check_interval: int = 60,
    ):
        """Initialize pool manager.

        Args:
            pool_name: Pool name (e.g., "universal_pool")
            max_agents: Maximum agents allowed in pool
            health_check_interval: Seconds between health checks
        """
        self.pool_name = pool_name
        self.max_agents = max_agents
        self.health_check_interval = health_check_interval

        # Direct in-memory agent storage
        self.agents: Dict[UUID, BaseAgent] = {}

        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Statistics
        self.created_at = datetime.now(timezone.utc)
        self.total_spawned = 0
        self.total_terminated = 0

        logger.info(
            f"AgentPoolManager initialized: pool={pool_name}, "
            f"max_agents={max_agents}"
        )

    async def start(self) -> bool:
        """Start the pool manager.

        Returns:
            True if started successfully
        """
        try:
            # Start health monitor
            self._monitor_task = asyncio.create_task(self._monitor_loop())

            logger.info(f"✓ AgentPoolManager started: {self.pool_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to start pool manager '{self.pool_name}': {e}", exc_info=True)
            return False

    async def stop(self, graceful: bool = True) -> bool:
        """Stop the pool manager and all agents.

        Args:
            graceful: If True, wait for agents to finish current tasks

        Returns:
            True if stopped successfully
        """
        try:
            logger.info(f"Stopping pool manager '{self.pool_name}' (graceful={graceful})...")

            self._shutdown_event.set()

            # Stop monitor task
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            # Stop all agents
            agent_ids = list(self.agents.keys())
            for agent_id in agent_ids:
                try:
                    await self.terminate_agent(agent_id, graceful=graceful)
                except (Exception, asyncio.CancelledError) as e:
                    logger.error(f"Error terminating agent {agent_id}: {e}")

            logger.info(f"✓ Pool manager stopped: {self.pool_name}")
            return True

        except asyncio.CancelledError:
            logger.info(f"Pool manager stop cancelled: {self.pool_name}")
            return False
        except Exception as e:
            logger.error(f"Error stopping pool manager: {e}", exc_info=True)
            return False

    # ===== Agent Management =====

    async def spawn_agent(
        self,
        agent_id: UUID,
        role_class: Type[BaseAgent],
        heartbeat_interval: int = 30,
        max_idle_time: int = 300,
    ) -> bool:
        """Spawn an agent directly in memory.

        No multiprocessing, no IPC overhead.
        Flow:
        1. Check capacity
        2. Load agent from DB
        3. Create agent instance
        4. Start agent (starts Kafka consumer)
        5. Store in memory dict
        6. Update DB status

        Args:
            agent_id: Agent UUID (must exist in database)
            role_class: Agent role class to instantiate
            heartbeat_interval: Agent heartbeat interval
            max_idle_time: Agent max idle time

        Returns:
            True if spawned successfully
        """
        # 1. Check capacity
        if len(self.agents) >= self.max_agents:
            logger.warning(f"Pool '{self.pool_name}' at max capacity ({self.max_agents})")
            return False

        # 2. Check if already spawned
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already exists in pool")
            return False

        try:
            # 3. Load agent from database
            with Session(engine) as db_session:
                agent_model = db_session.get(AgentModel, agent_id)

                if not agent_model:
                    logger.error(f"Agent {agent_id} not found in database")
                    return False

                # 4. Create agent instance
                agent = role_class(
                    agent_model=agent_model,
                    heartbeat_interval=heartbeat_interval,
                    max_idle_time=max_idle_time,
                )

                # 5. Start agent (starts Kafka consumer for handling tasks)
                if await agent.start():
                    # 6. Store in memory
                    self.agents[agent_id] = agent
                    self.total_spawned += 1

                    # 7. Update DB status
                    from app.services import AgentService
                    agent_service = AgentService(db_session)
                    agent_service.update_status(agent_id, AgentStatus.idle, commit=True)

                    logger.info(
                        f"✓ Spawned agent: {agent_model.human_name} ({agent_id}) "
                        f"[{role_class.__name__}] in pool '{self.pool_name}'"
                    )
                    return True
                else:
                    logger.error(f"Failed to start agent {agent_id}")
                    return False

        except Exception as e:
            logger.error(f"Failed to spawn agent {agent_id}: {e}", exc_info=True)
            return False

    async def terminate_agent(self, agent_id: UUID, graceful: bool = True) -> bool:
        """Terminate an agent.

        Args:
            agent_id: Agent UUID
            graceful: If True, wait for agent to finish current task

        Returns:
            True if terminated successfully
        """
        agent = self.agents.get(agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found in pool '{self.pool_name}'")
            return False

        try:
            # 1. Stop agent (stops Kafka consumer)
            await agent.stop(graceful=graceful)

            # 2. Remove from memory
            del self.agents[agent_id]
            self.total_terminated += 1

            # 3. Update DB status
            with Session(engine) as db_session:
                from app.services import AgentService
                agent_service = AgentService(db_session)
                agent_service.update_status(agent_id, AgentStatus.stopped, commit=True)

            logger.info(f"✓ Terminated agent {agent.name} ({agent_id}) from pool '{self.pool_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to terminate agent {agent_id}: {e}", exc_info=True)
            return False

    def get_agent(self, agent_id: UUID) -> Optional[BaseAgent]:
        """Get agent by ID.

        Args:
            agent_id: Agent UUID

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)

    def get_all_agents(self) -> List[BaseAgent]:
        """Get all agents in pool.

        Returns:
            List of agent instances
        """
        return list(self.agents.values())

    # ===== Statistics =====

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics.

        Returns:
            Statistics dictionary
        """
        idle_agents = sum(1 for a in self.agents.values() if a.state == AgentStatus.idle)
        busy_agents = sum(1 for a in self.agents.values() if a.state == AgentStatus.busy)
        active_agents = idle_agents + busy_agents

        total_executions = sum(a.total_executions for a in self.agents.values())
        successful_executions = sum(a.successful_executions for a in self.agents.values())
        failed_executions = sum(a.failed_executions for a in self.agents.values())

        return {
            "pool_name": self.pool_name,
            "manager_type": "in-memory",
            "total_agents": len(self.agents),
            "active_agents": active_agents,
            "busy_agents": busy_agents,
            "idle_agents": idle_agents,
            "total_spawned": self.total_spawned,
            "total_terminated": self.total_terminated,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "load": busy_agents / len(self.agents) if len(self.agents) > 0 else 0,
            "created_at": self.created_at.isoformat(),
            "manager_uptime_seconds": (datetime.now(timezone.utc) - self.created_at).total_seconds(),
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
        """Single health check monitor loop.

        Periodically checks agent health and terminates unhealthy agents.
        """
        logger.info(f"Health monitor started for pool '{self.pool_name}'")

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.health_check_interval)

                # Check each agent's health
                for agent_id, agent in list(self.agents.items()):
                    try:
                        health = await agent.health_check()

                        if not health.get("healthy", False):
                            logger.warning(
                                f"Agent {agent.name} ({agent_id}) unhealthy, terminating. "
                                f"Reason: {health.get('reason', 'unknown')}"
                            )
                            await self.terminate_agent(agent_id, graceful=False)

                    except Exception as e:
                        logger.error(f"Error checking health of agent {agent_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}", exc_info=True)

        logger.info(f"Health monitor stopped for pool '{self.pool_name}'")


# ===== Migration Helper =====

async def migrate_to_agent_pool_manager(
    old_manager_registry: Dict[str, Any],
    use_new_manager: bool = False,
) -> Dict[str, AgentPoolManager]:
    """Helper to migrate from old multiprocessing manager to new in-memory manager.

    Args:
        old_manager_registry: Existing manager registry
        use_new_manager: If True, create new managers

    Returns:
        New manager registry
    """
    if not use_new_manager:
        return {}

    registry: Dict[str, AgentPoolManager] = {}

    logger.info("Migrating to agent pool managers...")

    # Create universal pool
    pool_name = "universal_pool"
    manager = AgentPoolManager(
        pool_name=pool_name,
        max_agents=100,  # Higher limit since no process overhead
        health_check_interval=60,
    )

    if await manager.start():
        registry[pool_name] = manager
        logger.info(f"✓ Created agent pool manager: {pool_name}")
    else:
        logger.error(f"✗ Failed to create agent pool manager: {pool_name}")

    return registry
