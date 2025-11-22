"""Agent Pool Manager for dynamic agent lifecycle management.

This module provides centralized management of agent instances with:
- Dynamic agent spawning and termination
- Load balancing
- Health monitoring
- Auto-scaling capabilities
- Resource pooling
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Type
from uuid import UUID, uuid4

from app.agents.core.base_role import BaseAgentRole, AgentLifecycleState

logger = logging.getLogger(__name__)


class AgentPoolConfig:
    """Configuration for agent pool."""

    def __init__(
        self,
        min_agents: int = 0,
        max_agents: int = 10,
        scale_up_threshold: float = 0.8,
        scale_down_threshold: float = 0.2,
        idle_timeout: int = 300,
        health_check_interval: int = 60,
    ):
        """Initialize pool configuration.

        Args:
            min_agents: Minimum number of agents to maintain
            max_agents: Maximum number of agents allowed
            scale_up_threshold: CPU/load threshold to spawn new agents (0-1)
            scale_down_threshold: CPU/load threshold to stop agents (0-1)
            idle_timeout: Seconds before idle agent is stopped
            health_check_interval: Seconds between health checks
        """
        self.min_agents = min_agents
        self.max_agents = max_agents
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.idle_timeout = idle_timeout
        self.health_check_interval = health_check_interval


class AgentPool:
    """Manages a pool of agent instances for a specific role.

    Features:
    - Dynamic agent spawning/stopping
    - Load balancing (round-robin, least-busy)
    - Health monitoring
    - Auto-scaling based on load
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
        self._autoscaler_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        logger.info(f"AgentPool '{pool_name}' created for role {role_class.__name__}")

    async def start(self) -> bool:
        """Start the agent pool and background services.

        Returns:
            True if started successfully
        """
        try:
            # Spawn minimum agents
            for _ in range(self.config.min_agents):
                await self.spawn_agent()

            # Start monitor
            self._monitor_task = asyncio.create_task(self._monitor_loop())

            # Start autoscaler
            self._autoscaler_task = asyncio.create_task(self._autoscaler_loop())

            logger.info(f"AgentPool '{self.pool_name}' started with {len(self.agents)} agents")
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
            for task in [self._monitor_task, self._autoscaler_task]:
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Stop all agents
            stop_tasks = [self.terminate_agent(agent_id, graceful) for agent_id in list(self.agents.keys())]
            await asyncio.gather(*stop_tasks, return_exceptions=True)

            logger.info(f"AgentPool '{self.pool_name}' stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop pool '{self.pool_name}': {e}", exc_info=True)
            return False

    # ===== Agent Management =====

    async def spawn_agent(
        self,
        agent_id: Optional[UUID] = None,
        heartbeat_interval: int = 30,
        max_idle_time: int = 300,
    ) -> Optional[BaseAgentRole]:
        """Spawn a new agent instance.

        Args:
            agent_id: Optional agent ID
            heartbeat_interval: Heartbeat interval in seconds
            max_idle_time: Max idle time in seconds

        Returns:
            Agent instance if spawned successfully, None otherwise
        """
        if len(self.agents) >= self.config.max_agents:
            logger.warning(f"Pool '{self.pool_name}' at max capacity ({self.config.max_agents})")
            return None

        try:
            # Create agent instance
            agent = self.role_class(
                agent_id=agent_id,
                heartbeat_interval=heartbeat_interval,
                max_idle_time=max_idle_time,
            )

            # Set up callbacks
            agent.on_state_change = self._on_agent_state_change
            agent.on_execution_complete = self._on_agent_execution_complete
            agent.on_heartbeat = self._on_agent_heartbeat

            # Start agent
            if await agent.start():
                self.agents[agent.agent_id] = agent
                self.agent_stats[agent.agent_id] = {
                    "spawned_at": datetime.now(timezone.utc),
                    "executions": 0,
                    "last_execution": None,
                }
                self.total_spawned += 1

                logger.info(f"Agent {agent.agent_id} spawned in pool '{self.pool_name}'")
                return agent
            else:
                logger.error(f"Failed to start agent {agent.agent_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to spawn agent: {e}", exc_info=True)
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
            if agent.state == AgentLifecycleState.RUNNING
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
        active_agents = sum(1 for a in self.agents.values() if a.state == AgentLifecycleState.RUNNING)
        busy_agents = sum(1 for a in self.agents.values() if a.state == AgentLifecycleState.BUSY)
        total_executions = sum(a.total_executions for a in self.agents.values())
        total_successful = sum(a.successful_executions for a in self.agents.values())
        total_failed = sum(a.failed_executions for a in self.agents.values())

        return {
            "pool_name": self.pool_name,
            "role_class": self.role_class.__name__,
            "total_agents": len(self.agents),
            "active_agents": active_agents,
            "busy_agents": busy_agents,
            "idle_agents": active_agents - busy_agents,
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

                    # Terminate if idle too long
                    elif health["idle_seconds"] > self.config.idle_timeout:
                        if len(self.agents) > self.config.min_agents:
                            logger.info(f"Agent {agent_id} idle for {health['idle_seconds']}s, terminating")
                            await self.terminate_agent(agent_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}", exc_info=True)

    async def _autoscaler_loop(self) -> None:
        """Auto-scale agents based on load."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                stats = self.get_pool_stats()
                load = stats["load"]

                # Scale up if load is high
                if load > self.config.scale_up_threshold:
                    if len(self.agents) < self.config.max_agents:
                        logger.info(f"Pool '{self.pool_name}' load {load:.2f}, scaling up")
                        await self.spawn_agent()

                # Scale down if load is low
                elif load < self.config.scale_down_threshold:
                    if len(self.agents) > self.config.min_agents:
                        # Find idle agent to terminate
                        idle_agent = next(
                            (a for a in self.agents.values() if a.state == AgentLifecycleState.RUNNING),
                            None
                        )
                        if idle_agent:
                            logger.info(f"Pool '{self.pool_name}' load {load:.2f}, scaling down")
                            await self.terminate_agent(idle_agent.agent_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Autoscaler loop error: {e}", exc_info=True)

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
