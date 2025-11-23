"""Agent Pool Manager - Master process coordinator for auto-scaling agent pools.

This module manages multiple worker processes, each running an AgentPool:
- Spawns worker processes dynamically when capacity is reached
- Routes spawn/terminate requests to appropriate workers
- Monitors worker health and capacity via Redis
- Provides statistics aggregation across all workers
- Handles worker lifecycle (start/stop/cleanup)
"""

import asyncio
import logging
from datetime import datetime, timezone
from multiprocessing import Process
from typing import Dict, List, Optional, Type
from uuid import UUID

from app.agents.core.agent_pool_worker import run_worker_process
from app.agents.core.base_role import BaseAgentRole
from app.agents.core.redis_client import RedisClient, get_redis_client
from app.agents.core.registry import AgentRegistry, ProcessRegistry
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentPoolManager:
    """Manages auto-scaling agent pools with multiprocessing.

    Features:
    - Dynamic process spawning when capacity is reached
    - Load balancing across worker processes
    - Health monitoring and stale worker cleanup
    - Centralized statistics aggregation
    - Graceful shutdown coordination
    """

    def __init__(
        self,
        pool_name: str,
        role_class: Type[BaseAgentRole],
        max_agents_per_process: int = 10,
        heartbeat_interval: int = 30,
        redis_client: Optional[RedisClient] = None,
    ):
        """Initialize pool manager.

        Args:
            pool_name: Pool name
            role_class: Agent role class to instantiate in workers
            max_agents_per_process: Max agents per worker process
            heartbeat_interval: Worker heartbeat interval in seconds
            redis_client: Redis client instance (optional)
        """
        self.pool_name = pool_name
        self.role_class = role_class
        self.max_agents_per_process = max_agents_per_process
        self.heartbeat_interval = heartbeat_interval

        # Redis integration
        self.redis = redis_client or get_redis_client()
        self.agent_registry = AgentRegistry(redis_client=self.redis)
        self.process_registry = ProcessRegistry(redis_client=self.redis)

        # Worker process tracking
        self.worker_processes: Dict[str, Process] = {}  # process_id -> Process

        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._event_listener_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._pubsub = None

        # Statistics
        self.created_at = datetime.now(timezone.utc)
        self.total_workers_spawned = 0
        self.total_workers_terminated = 0

        logger.info(
            f"AgentPoolManager initialized: pool={pool_name}, "
            f"max_agents_per_process={max_agents_per_process}"
        )

    async def start(self) -> bool:
        """Start the pool manager.

        Returns:
            True if started successfully
        """
        try:
            # Ensure Redis is connected
            if not self.redis._connected:
                if not await self.redis.connect():
                    logger.error(f"Failed to connect to Redis for pool '{self.pool_name}'")
                    return False

            # Start background tasks
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            self._event_listener_task = asyncio.create_task(self._event_listener())

            logger.info(f"✓ AgentPoolManager started: {self.pool_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to start pool manager '{self.pool_name}': {e}", exc_info=True)
            return False

    async def stop(self, graceful: bool = True) -> bool:
        """Stop the pool manager and all workers.

        Args:
            graceful: If True, wait for workers to finish

        Returns:
            True if stopped successfully
        """
        try:
            logger.info(f"Stopping pool manager '{self.pool_name}' (graceful={graceful})...")

            self._shutdown_event.set()

            # Stop background tasks
            if self._event_listener_task:
                self._event_listener_task.cancel()
                try:
                    await self._event_listener_task
                except asyncio.CancelledError:
                    pass

            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            # Close pub/sub
            if self._pubsub:
                await self._pubsub.close()

            # Stop all worker processes
            await self._stop_all_workers(graceful=graceful)

            logger.info(f"✓ Pool manager stopped: {self.pool_name}")
            return True

        except Exception as e:
            logger.error(f"Error stopping pool manager: {e}", exc_info=True)
            return False

    # ===== Worker Process Management =====

    async def spawn_worker(self) -> Optional[str]:
        """Spawn a new worker process.

        Returns:
            Process ID if spawned successfully, None otherwise
        """
        try:
            # Create worker process
            process = Process(
                target=run_worker_process,
                args=(
                    self.pool_name,
                    self.role_class,
                    self.max_agents_per_process,
                    self.heartbeat_interval,
                    self.redis.redis_url,
                ),
                daemon=False,  # Not daemon - we want graceful shutdown
            )

            # Start process
            process.start()

            # Wait a bit for process to register in Redis
            await asyncio.sleep(2)

            # Find the process_id by checking recent registrations
            # (worker registers itself with a UUID process_id)
            processes = await self.process_registry.get_pool_processes(self.pool_name)

            # Find new process (not in our tracking dict)
            new_process_id = None
            for process_id in processes:
                if process_id not in self.worker_processes:
                    new_process_id = process_id
                    break

            if new_process_id:
                self.worker_processes[new_process_id] = process
                self.total_workers_spawned += 1

                logger.info(
                    f"✓ Spawned worker process: {new_process_id} "
                    f"(PID: {process.pid}, pool: {self.pool_name})"
                )
                return new_process_id
            else:
                logger.error(f"Failed to find process_id for spawned worker (PID: {process.pid})")
                process.terminate()
                return None

        except Exception as e:
            logger.error(f"Failed to spawn worker process: {e}", exc_info=True)
            return None

    async def terminate_worker(self, process_id: str, graceful: bool = True) -> bool:
        """Terminate a worker process.

        Args:
            process_id: Worker process ID
            graceful: If True, send graceful shutdown command

        Returns:
            True if terminated successfully
        """
        try:
            process = self.worker_processes.get(process_id)
            if not process:
                logger.warning(f"Worker process {process_id} not found in tracking dict")
                return False

            if graceful:
                # Send shutdown command via Redis
                await self.redis.publish_command(
                    pool_name=self.pool_name,
                    command="shutdown",
                    data={"graceful": True},
                )

                # Wait for process to exit (with timeout)
                process.join(timeout=30)

                if process.is_alive():
                    logger.warning(f"Worker {process_id} did not stop gracefully, terminating...")
                    process.terminate()
                    process.join(timeout=5)
            else:
                # Force terminate
                process.terminate()
                process.join(timeout=5)

            # Cleanup
            if process.is_alive():
                process.kill()

            del self.worker_processes[process_id]
            self.total_workers_terminated += 1

            logger.info(f"✓ Terminated worker process: {process_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to terminate worker {process_id}: {e}", exc_info=True)
            return False

    async def _stop_all_workers(self, graceful: bool = True) -> None:
        """Stop all worker processes.

        Args:
            graceful: If True, graceful shutdown
        """
        process_ids = list(self.worker_processes.keys())

        for process_id in process_ids:
            await self.terminate_worker(process_id, graceful=graceful)

    # ===== Agent Management (High-level API) =====

    async def spawn_agent(
        self,
        agent_id: UUID,
        heartbeat_interval: int = 30,
        max_idle_time: int = 300,
    ) -> bool:
        """Spawn an agent, auto-scaling workers if needed.

        This is the main method called by the API to spawn agents.
        It handles:
        - Finding available worker process
        - Auto-spawning new worker if all are at capacity
        - Routing spawn command to target worker

        Args:
            agent_id: Agent UUID (must exist in database)
            heartbeat_interval: Agent heartbeat interval
            max_idle_time: Agent max idle time

        Returns:
            True if spawn initiated successfully
        """
        try:
            # 1. Check if we have any worker processes
            if len(self.worker_processes) == 0:
                logger.info(f"No worker processes, spawning first worker for pool '{self.pool_name}'")
                if not await self.spawn_worker():
                    logger.error("Failed to spawn first worker process")
                    return False

            # 2. Find available worker process
            result = await self.process_registry.find_available_process(
                pool_name=self.pool_name,
                min_slots=1,
            )

            target_process_id = None

            if result:
                target_process_id, process_info = result
                logger.info(
                    f"Found available worker: {target_process_id} "
                    f"({process_info['agent_count']}/{process_info['max_agents']} agents)"
                )
            else:
                # 3. No available worker, spawn new one
                logger.info(f"All workers at capacity, spawning new worker for pool '{self.pool_name}'")
                target_process_id = await self.spawn_worker()

                if not target_process_id:
                    logger.error("Failed to spawn new worker process")
                    return False

            # 4. Send spawn command to target worker
            success = await self.redis.publish_command(
                pool_name=self.pool_name,
                command="spawn",
                data={
                    "agent_id": str(agent_id),
                    "target_process_id": target_process_id,
                    "heartbeat_interval": heartbeat_interval,
                    "max_idle_time": max_idle_time,
                },
            )

            if success:
                logger.info(f"✓ Spawn command sent for agent {agent_id} to worker {target_process_id}")
                return True
            else:
                logger.error(f"Failed to send spawn command for agent {agent_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to spawn agent {agent_id}: {e}", exc_info=True)
            return False

    async def terminate_agent(self, agent_id: UUID, graceful: bool = True) -> bool:
        """Terminate an agent.

        Args:
            agent_id: Agent UUID
            graceful: If True, graceful shutdown

        Returns:
            True if terminate initiated successfully
        """
        try:
            # 1. Find which worker has this agent
            agent_info = await self.agent_registry.get_info(agent_id)

            if not agent_info:
                logger.warning(f"Agent {agent_id} not found in registry")
                return False

            process_id = agent_info.get("process_id")

            if not process_id:
                logger.warning(f"Agent {agent_id} has no process_id")
                return False

            # 2. Send terminate command to worker
            success = await self.redis.publish_command(
                pool_name=self.pool_name,
                command="terminate",
                data={
                    "agent_id": str(agent_id),
                    "graceful": graceful,
                },
            )

            if success:
                logger.info(f"✓ Terminate command sent for agent {agent_id} to worker {process_id}")
                return True
            else:
                logger.error(f"Failed to send terminate command for agent {agent_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to terminate agent {agent_id}: {e}", exc_info=True)
            return False

    # ===== Background Tasks =====

    async def _monitor_loop(self) -> None:
        """Monitor worker health and cleanup stale workers."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(60)  # Check every minute

                # Cleanup stale workers (no heartbeat for 5 minutes)
                cleaned = await self.process_registry.cleanup_stale_processes(
                    pool_name=self.pool_name,
                    timeout_seconds=300,
                )

                if cleaned:
                    logger.warning(f"Cleaned up {len(cleaned)} stale worker processes")

                    # Remove from our tracking
                    for process_id in cleaned:
                        if process_id in self.worker_processes:
                            process = self.worker_processes[process_id]
                            if process.is_alive():
                                process.terminate()
                            del self.worker_processes[process_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}", exc_info=True)

    async def _event_listener(self) -> None:
        """Listen for events from workers."""
        try:
            # Subscribe to pool events
            self._pubsub = await self.redis.subscribe_events(self.pool_name)

            logger.info(f"Listening for events from pool '{self.pool_name}'...")

            while not self._shutdown_event.is_set():
                try:
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )

                    if message and message["type"] == "message":
                        await self._handle_event(message["data"])

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Event listener error: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Fatal event listener error: {e}", exc_info=True)

    async def _handle_event(self, message_data: str) -> None:
        """Handle event from worker.

        Args:
            message_data: JSON message data
        """
        try:
            import json

            message = json.loads(message_data)
            event_type = message.get("event_type")
            data = message.get("data", {})

            logger.debug(f"Received event: {event_type} from pool '{self.pool_name}'")

            # Handle different event types
            if event_type == "agent_spawned":
                logger.info(f"Agent spawned: {data.get('agent_id')} in worker {data.get('process_id')}")
            elif event_type == "agent_spawn_failed":
                logger.error(
                    f"Agent spawn failed: {data.get('agent_id')} "
                    f"in worker {data.get('process_id')}, reason: {data.get('reason')}"
                )
            elif event_type == "agent_terminated":
                logger.info(f"Agent terminated: {data.get('agent_id')} in worker {data.get('process_id')}")
            else:
                logger.debug(f"Unknown event type: {event_type}")

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    # ===== Statistics =====

    async def get_stats(self) -> Dict:
        """Get comprehensive statistics for this pool.

        Returns:
            Statistics dictionary
        """
        try:
            # Get pool stats from Redis registry
            pool_stats = await self.process_registry.get_pool_stats(self.pool_name)

            # Add manager-specific stats
            pool_stats.update({
                "manager_uptime_seconds": (datetime.now(timezone.utc) - self.created_at).total_seconds(),
                "total_workers_spawned": self.total_workers_spawned,
                "total_workers_terminated": self.total_workers_terminated,
                "active_worker_processes": len(self.worker_processes),
            })

            return pool_stats

        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
            return {
                "pool_name": self.pool_name,
                "error": str(e),
            }
