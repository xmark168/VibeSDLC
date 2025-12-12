import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from sqlmodel import Session, select, update

from app.agents.core.base_agent import BaseAgent
from app.models import Agent as AgentModel, AgentStatus, AgentPool, PoolType
from app.core.db import engine
from app.services.pool_service import PoolService

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
        pool_id: Optional[UUID] = None,
    ):
        """Initialize pool manager.

        Args:
            pool_name: Pool name (e.g., "universal_pool")
            max_agents: Maximum agents allowed in pool
            health_check_interval: Seconds between health checks
            pool_id: Database pool ID (if already exists)
        """
        self.pool_name = pool_name
        self.max_agents = max_agents
        self.health_check_interval = health_check_interval
        self.pool_id = pool_id

        # Direct in-memory agent storage
        self.agents: Dict[UUID, BaseAgent] = {}

        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Statistics
        self.created_at = datetime.now(timezone.utc)
        self.total_spawned = 0
        self.total_terminated = 0
        self._is_running = False

        logger.info(
            f"AgentPoolManager initialized: pool={pool_name}, "
            f"max_agents={max_agents}, pool_id={pool_id}"
        )

    async def start(self) -> bool:
        """Start the pool manager.

        Returns:
            True if started successfully
        """
        try:
            # Start health monitor
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            self._is_running = True

            # Update DB: mark pool as started
            if self.pool_id:
                with Session(engine) as session:
                    pool_service = PoolService(session)
                    pool_service.mark_pool_started(self.pool_id)

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
            self._is_running = False

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

            # Update DB: mark pool as stopped
            if self.pool_id:
                with Session(engine) as session:
                    pool_service = PoolService(session)
                    pool_service.mark_pool_stopped(self.pool_id)
                    pool_service.update_agent_count(self.pool_id, 0)

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
                
                # 4.5. Attach circuit breaker
                from app.agents.core.circuit_breaker import get_circuit_breaker_manager
                cb_manager = get_circuit_breaker_manager()
                circuit_breaker = cb_manager.get_or_create(agent_id)
                agent.set_circuit_breaker(circuit_breaker)

                # 5. Start agent (starts Kafka consumer for handling tasks)
                if await agent.start():
                    # 6. Store in memory
                    self.agents[agent_id] = agent
                    self.total_spawned += 1

                    # 7. Update DB status
                    from app.services import AgentService
                    agent_service = AgentService(db_session)
                    agent_service.update_status(agent_id, AgentStatus.idle, commit=False)
                    
                    # 8. Update agent pool_id and increment counters
                    agent_model.pool_id = self.pool_id
                    db_session.add(agent_model)
                    db_session.commit()
                    
                    # 9. Update pool counters in DB
                    if self.pool_id:
                        pool_service = PoolService(db_session)
                        pool_service.increment_spawn_count(self.pool_id)

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
            await agent.stop()

            # 2. Remove from memory
            del self.agents[agent_id]
            self.total_terminated += 1
            
            # 2.5. Remove circuit breaker
            from app.agents.core.circuit_breaker import get_circuit_breaker_manager
            cb_manager = get_circuit_breaker_manager()
            cb_manager.remove(agent_id)

            # 3. Update DB status and pool counters
            with Session(engine) as db_session:
                from app.services import AgentService
                agent_service = AgentService(db_session)
                agent_service.update_status(agent_id, AgentStatus.stopped, commit=True)
                
                # 4. Update pool counters in DB
                if self.pool_id:
                    pool_service = PoolService(db_session)
                    pool_service.increment_terminate_count(self.pool_id)

            logger.info(f"✓ Terminated agent {agent.name} ({agent_id}) from pool '{self.pool_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to terminate agent {agent_id}: {e}", exc_info=True)
            return False

    def has_agent(self, agent_id: UUID) -> bool:
        """Check if agent exists in pool.

        Args:
            agent_id: Agent UUID

        Returns:
            True if agent exists, False otherwise
        """
        return agent_id in self.agents

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

    # ===== Story Signal Management =====

    def signal_agent(self, agent_id: UUID, story_id: str, signal: str) -> bool:
        """Send signal directly to an agent for a story.
        
        This is O(1) - no Kafka, no DB poll needed.
        Agent ID comes from story.assigned_agent_id in DB.
        
        Args:
            agent_id: Agent UUID (from story.assigned_agent_id)
            story_id: Story UUID string
            signal: Signal type ('cancel', 'pause')
            
        Returns:
            True if signal was delivered to agent
        """
        logger.info(f"[Pool] [SIGNAL] signal_agent called: agent={agent_id}, story={story_id[:8]}, signal={signal}")
        logger.info(f"[Pool] [SIGNAL] Current agents in pool: {list(self.agents.keys())}")
        
        agent = self.agents.get(agent_id)
        if not agent:
            logger.warning(f"[Pool] [SIGNAL] Agent {agent_id} NOT FOUND in pool '{self.pool_name}'")
            return False
        
        # Direct push to agent - instant delivery
        logger.info(f"[Pool] [SIGNAL] Calling agent.receive_signal({story_id[:8]}, {signal})")
        agent.receive_signal(story_id, signal)
        
        # Verify signal was stored
        stored_signal = agent.check_signal(story_id)
        logger.info(f"[Pool] [SIGNAL] Signal stored in agent._pending_signals: {stored_signal}")
        logger.info(f"[Pool] [SIGNAL] Agent._pending_signals = {agent._pending_signals}")
        
        return True

    @property
    def is_running(self) -> bool:
        """Check if pool manager is running.

        Returns:
            True if running
        """
        return self._is_running

    # ===== Statistics =====

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics.

        Returns:
            Statistics dictionary
        """
        from sqlalchemy import func
        from app.models import AgentExecution, AgentExecutionStatus
        
        idle_agents = sum(1 for a in self.agents.values() if a.state == AgentStatus.idle)
        busy_agents = sum(1 for a in self.agents.values() if a.state == AgentStatus.busy)
        active_agents = idle_agents + busy_agents

        # Query execution stats from database for this pool
        total_executions = 0
        successful_executions = 0
        failed_executions = 0
        
        # Get role type from pool name
        role_type = None
        if self.pool_name.endswith("_pool"):
            role_type = self.pool_name.replace("_pool", "")
        
        if self.pool_id:
            with Session(engine) as session:
                # Count executions for this pool by pool_id
                total_executions = session.exec(
                    select(func.count(AgentExecution.id))
                    .where(AgentExecution.pool_id == self.pool_id)
                ).one() or 0
                
                successful_executions = session.exec(
                    select(func.count(AgentExecution.id))
                    .where(
                        AgentExecution.pool_id == self.pool_id,
                        AgentExecution.status == AgentExecutionStatus.COMPLETED
                    )
                ).one() or 0
                
                failed_executions = session.exec(
                    select(func.count(AgentExecution.id))
                    .where(
                        AgentExecution.pool_id == self.pool_id,
                        AgentExecution.status == AgentExecutionStatus.FAILED
                    )
                ).one() or 0

        # Get agents list
        agents_list = []
        for agent_id, agent in self.agents.items():
            agents_list.append({
                "agent_id": str(agent_id),
                "name": getattr(agent, 'name', 'Unknown'),
                "role": getattr(agent, 'role', agent.__class__.__name__),
                "state": agent.state.value if hasattr(agent.state, 'value') else str(agent.state),
            })

        # Get pool priority from DB
        pool_priority = 0
        if self.pool_id:
            with Session(engine) as session:
                pool = session.get(AgentPool, self.pool_id)
                if pool:
                    pool_priority = pool.priority

        return {
            "id": str(self.pool_id) if self.pool_id else None,
            "pool_name": self.pool_name,
            "role_type": role_type or "universal",
            "priority": pool_priority,
            "manager_type": "in-memory",
            "total_agents": len(self.agents),
            "active_agents": active_agents,
            "busy_agents": busy_agents,
            "idle_agents": idle_agents,
            "max_agents": self.max_agents,
            "is_running": self.is_running,
            "total_spawned": self.total_spawned,
            "total_terminated": self.total_terminated,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "load": busy_agents / len(self.agents) if len(self.agents) > 0 else 0,
            "created_at": self.created_at.isoformat(),
            "manager_uptime_seconds": (datetime.now(timezone.utc) - self.created_at).total_seconds(),
            "agents": agents_list,
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
        """Health check monitor loop with stale state detection.

        Periodically checks agent health and terminates unhealthy agents.
        Also detects and resets agents stuck in busy state with no tasks.
        """
        logger.info(f"Health monitor started for pool '{self.pool_name}'")

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.health_check_interval)

                # Check each agent's health
                for agent_id, agent in list(self.agents.items()):
                    try:
                        health = await agent.health_check()
                        severity = health.get("severity", "ok")

                        # Critical: terminate immediately
                        if not health.get("healthy", False) and severity == "critical":
                            logger.error(
                                f"[HEALTH] Agent {agent.name} ({agent_id}) CRITICAL: "
                                f"{health.get('reason', 'unknown')}"
                            )
                            await self.terminate_agent(agent_id, graceful=False)
                            continue

                        # Warning: log but don't terminate (may recover)
                        if not health.get("healthy", False) and severity == "warning":
                            logger.warning(
                                f"[HEALTH] Agent {agent.name} ({agent_id}) WARNING: "
                                f"{health.get('reason', 'unknown')}"
                            )
                            # Reset to idle if stuck busy (give chance to recover)
                            if agent.state == AgentStatus.busy:
                                agent.state = AgentStatus.idle
                            continue

                        # Degraded but operational: log warnings
                        if health.get("warnings"):
                            logger.warning(
                                f"[HEALTH] Agent {agent.name} ({agent_id}) degraded: "
                                f"{health.get('warnings')}"
                            )

                        # Check for stale busy state (agent stuck as busy with no tasks)
                        if agent.state == AgentStatus.busy:
                            has_queue_tasks = hasattr(agent, '_task_queue') and agent._task_queue.qsize() > 0
                            has_current_task = getattr(agent, '_current_task_id', None) is not None
                            
                            if not has_queue_tasks and not has_current_task:
                                logger.warning(
                                    f"[HEALTH] Agent {agent.name} ({agent_id}) stuck in busy state "
                                    f"with no tasks, resetting to idle"
                                )
                                agent.state = AgentStatus.idle

                    except Exception as e:
                        logger.error(f"[HEALTH] Error checking health of agent {agent_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HEALTH] Monitor loop error: {e}", exc_info=True)

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
