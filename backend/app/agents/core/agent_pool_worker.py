"""Agent Pool Worker Process.

This module implements a worker process that runs an AgentPool in isolation.
Each worker:
- Runs in its own OS process with own event loop
- Manages up to max_agents (default 10) agents
- Listens for Redis pub/sub commands (spawn, terminate)
- Reports heartbeat and capacity to master via Redis
- Creates own database connection pool (via PgBouncer)
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, Optional, Type
from uuid import UUID, uuid4

from app.agents.core.agent_pool import AgentPool, AgentPoolConfig
from app.agents.core.base_role import BaseAgentRole
from app.agents.core.redis_client import RedisClient, get_redis_client
from app.agents.core.registry import AgentRegistry, ProcessRegistry
from app.core.db import engine, get_worker_engine
from sqlmodel import Session

# Import role classes for dynamic instantiation
from app.agents.roles.team_leader import TeamLeaderRole
from app.agents.roles.business_analyst import BusinessAnalystRole
from app.agents.roles.developer import DeveloperRole
from app.agents.roles.tester import TesterRole

# Configure logging for worker process
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Role class mapping for dynamic instantiation
ROLE_CLASS_MAP = {
    "TeamLeaderRole": TeamLeaderRole,
    "BusinessAnalystRole": BusinessAnalystRole,
    "DeveloperRole": DeveloperRole,
    "TesterRole": TesterRole,
}


class AgentPoolWorker:
    """Worker process that manages an AgentPool instance.

    This class runs in a child process and:
    - Creates and manages an AgentPool
    - Listens for commands via Redis pub/sub
    - Reports status and capacity via Redis
    - Handles graceful shutdown
    """

    def __init__(
        self,
        pool_name: str,
        max_agents: int = 10,
        heartbeat_interval: int = 30,
        redis_url: Optional[str] = None,
        role_class: Optional[Type[BaseAgentRole]] = None,
    ):
        """Initialize worker process.

        Args:
            pool_name: Pool name
            max_agents: Maximum agents for this worker
            heartbeat_interval: Heartbeat interval in seconds
            redis_url: Redis connection URL (optional)
            role_class: (Optional) Default role class for backward compatibility.
                       If None, worker creates a universal pool.
        """
        self.pool_name = pool_name
        self.role_class = role_class  # Optional, for backward compatibility
        self.max_agents = max_agents
        self.heartbeat_interval = heartbeat_interval

        # Process identification
        self.process_id = str(uuid4())
        self.pid = os.getpid()

        # Components (initialized in start())
        self.redis: Optional[RedisClient] = None
        self.redis_url = redis_url
        self.pool: Optional[AgentPool] = None
        self.agent_registry: Optional[AgentRegistry] = None
        self.process_registry: Optional[ProcessRegistry] = None

        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._command_listener_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._pubsub = None

        # Statistics
        self.started_at: Optional[datetime] = None

        pool_type = f"role={role_class.__name__}" if role_class else "universal"
        logger.info(
            f"AgentPoolWorker initialized: process_id={self.process_id}, "
            f"pool={pool_name}, max_agents={max_agents}, type={pool_type}, pid={self.pid}"
        )

    async def start(self) -> bool:
        """Start the worker process.

        Returns:
            True if started successfully
        """
        try:
            self.started_at = datetime.now(timezone.utc)

            # 1. Connect to Redis
            logger.info(f"[{self.process_id}] Connecting to Redis...")
            self.redis = RedisClient(redis_url=self.redis_url) if self.redis_url else get_redis_client()
            if not await self.redis.connect():
                logger.error(f"[{self.process_id}] Failed to connect to Redis")
                return False

            # 2. Initialize registries
            self.agent_registry = AgentRegistry(redis_client=self.redis)
            self.process_registry = ProcessRegistry(redis_client=self.redis)

            # 3. Register this process
            logger.info(f"[{self.process_id}] Registering process in Redis...")
            metadata = {"type": "universal"}
            if self.role_class:
                metadata["role_class"] = self.role_class.__name__

            if not await self.process_registry.register(
                process_id=self.process_id,
                pool_name=self.pool_name,
                pid=self.pid,
                max_agents=self.max_agents,
                metadata=metadata,
            ):
                logger.error(f"[{self.process_id}] Failed to register process")
                return False

            # 4. Create AgentPool (universal or role-specific)
            logger.info(f"[{self.process_id}] Creating AgentPool...")
            pool_config = AgentPoolConfig(
                max_agents=self.max_agents,
                health_check_interval=60,
            )
            self.pool = AgentPool(
                pool_name=self.pool_name,
                config=pool_config,
                role_class=self.role_class,  # None for universal pool
            )

            if not await self.pool.start():
                logger.error(f"[{self.process_id}] Failed to start pool")
                return False

            # 5. Start background tasks
            logger.info(f"[{self.process_id}] Starting background tasks...")
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._command_listener_task = asyncio.create_task(self._command_listener())

            # 6. Setup signal handlers
            self._setup_signal_handlers()

            logger.info(
                f"✓ Worker started successfully: {self.process_id} "
                f"(pool={self.pool_name}, pid={self.pid})"
            )
            return True

        except Exception as e:
            logger.error(f"[{self.process_id}] Failed to start worker: {e}", exc_info=True)
            return False

    async def stop(self, graceful: bool = True) -> bool:
        """Stop the worker process.

        Args:
            graceful: If True, wait for agents to finish

        Returns:
            True if stopped successfully
        """
        try:
            logger.info(f"[{self.process_id}] Stopping worker (graceful={graceful})...")

            self._shutdown_event.set()

            # 1. Stop background tasks
            if self._command_listener_task:
                self._command_listener_task.cancel()
                try:
                    await self._command_listener_task
                except asyncio.CancelledError:
                    pass

            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass

            # 2. Close pub/sub
            if self._pubsub:
                await self._pubsub.close()

            # 3. Stop pool and all agents
            if self.pool:
                await self.pool.stop(graceful=graceful)

            # 4. Unregister process
            if self.process_registry:
                await self.process_registry.unregister(self.process_id)

            # 5. Disconnect Redis
            if self.redis:
                await self.redis.disconnect()

            logger.info(f"✓ Worker stopped: {self.process_id}")
            return True

        except Exception as e:
            logger.error(f"[{self.process_id}] Error stopping worker: {e}", exc_info=True)
            return False

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"[{self.process_id}] Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.stop(graceful=(signum != signal.SIGKILL)))

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    # ===== Background Tasks =====

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to master via Redis."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Update heartbeat and agent count
                agent_count = len(self.pool.agents) if self.pool else 0
                await self.process_registry.update_heartbeat(self.process_id, agent_count)

                logger.debug(
                    f"[{self.process_id}] Heartbeat: "
                    f"{agent_count}/{self.max_agents} agents"
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.process_id}] Heartbeat error: {e}")

    async def _command_listener(self) -> None:
        """Listen for commands from master via Redis pub/sub."""
        try:
            # Subscribe to pool commands
            self._pubsub = await self.redis.subscribe_commands(self.pool_name)

            logger.info(f"[{self.process_id}] Listening for commands on pool '{self.pool_name}'...")

            while not self._shutdown_event.is_set():
                try:
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )

                    if message and message["type"] == "message":
                        await self._handle_command(message["data"])

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"[{self.process_id}] Command listener error: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[{self.process_id}] Fatal command listener error: {e}", exc_info=True)

    async def _handle_command(self, message_data: str) -> None:
        """Handle a command received via pub/sub.

        Args:
            message_data: JSON message data
        """
        try:
            message = json.loads(message_data)
            command = message.get("command")
            data = message.get("data", {})

            logger.info(f"[{self.process_id}] Received command: {command}")

            if command == "spawn":
                await self._handle_spawn_command(data)
            elif command == "terminate":
                await self._handle_terminate_command(data)
            elif command == "shutdown":
                await self._handle_shutdown_command(data)
            else:
                logger.warning(f"[{self.process_id}] Unknown command: {command}")

        except Exception as e:
            logger.error(f"[{self.process_id}] Error handling command: {e}", exc_info=True)

    async def _handle_spawn_command(self, data: Dict) -> None:
        """Handle spawn agent command.

        Args:
            data: Command data with agent_id, role_class_name, heartbeat_interval, max_idle_time
        """
        try:
            # Check if this command is for this process
            target_process_id = data.get("target_process_id")
            if target_process_id and target_process_id != self.process_id:
                logger.debug(f"[{self.process_id}] Spawn command not for this process, ignoring")
                return

            agent_id = UUID(data["agent_id"])
            heartbeat_interval = data.get("heartbeat_interval", 30)
            max_idle_time = data.get("max_idle_time", 300)

            # Get role_class from command data (for universal pools)
            role_class_name = data.get("role_class_name")
            role_class = None
            if role_class_name:
                role_class = ROLE_CLASS_MAP.get(role_class_name)
                if not role_class:
                    logger.error(
                        f"[{self.process_id}] Unknown role_class_name: {role_class_name}. "
                        f"Available: {list(ROLE_CLASS_MAP.keys())}"
                    )
                    return
                logger.info(f"[{self.process_id}] Spawning agent {agent_id} with role {role_class_name}...")
            else:
                logger.info(f"[{self.process_id}] Spawning agent {agent_id}...")

            # Spawn agent (role_class may be None if pool has default role_class)
            runtime_agent = await self.pool.spawn_agent(
                agent_id=agent_id,
                role_class=role_class,
                heartbeat_interval=heartbeat_interval,
                max_idle_time=max_idle_time,
            )

            if runtime_agent:
                # Register in Redis
                from sqlmodel import Session
                from app.core.db import engine
                from app.models import Agent as AgentModel

                with Session(engine) as db_session:
                    agent_model = db_session.get(AgentModel, agent_id)
                    if agent_model:
                        await self.agent_registry.register(
                            agent_id=agent_id,
                            process_id=self.process_id,
                            pool_name=self.pool_name,
                            role_type=agent_model.role_type,
                            project_id=agent_model.project_id,
                        )

                logger.info(f"[{self.process_id}] ✓ Agent {agent_id} spawned successfully")

                # Publish success event
                await self.redis.publish_event(
                    pool_name=self.pool_name,
                    event_type="agent_spawned",
                    data={
                        "agent_id": str(agent_id),
                        "process_id": self.process_id,
                        "success": True,
                    },
                )
            else:
                logger.error(f"[{self.process_id}] ✗ Failed to spawn agent {agent_id}")

                # Publish failure event
                await self.redis.publish_event(
                    pool_name=self.pool_name,
                    event_type="agent_spawn_failed",
                    data={
                        "agent_id": str(agent_id),
                        "process_id": self.process_id,
                        "success": False,
                        "reason": "pool.spawn_agent returned None",
                    },
                )

        except Exception as e:
            logger.error(f"[{self.process_id}] Error spawning agent: {e}", exc_info=True)

            # Publish error event
            try:
                await self.redis.publish_event(
                    pool_name=self.pool_name,
                    event_type="agent_spawn_failed",
                    data={
                        "agent_id": data.get("agent_id"),
                        "process_id": self.process_id,
                        "success": False,
                        "reason": str(e),
                    },
                )
            except:
                pass

    async def _handle_terminate_command(self, data: Dict) -> None:
        """Handle terminate agent command.

        Args:
            data: Command data with agent_id, graceful
        """
        try:
            agent_id = UUID(data["agent_id"])
            graceful = data.get("graceful", True)

            logger.info(f"[{self.process_id}] Terminating agent {agent_id} (graceful={graceful})...")

            # Terminate agent
            success = await self.pool.terminate_agent(agent_id, graceful=graceful)

            if success:
                # Unregister from Redis
                await self.agent_registry.unregister(agent_id)

                logger.info(f"[{self.process_id}] ✓ Agent {agent_id} terminated successfully")

                # Publish success event
                await self.redis.publish_event(
                    pool_name=self.pool_name,
                    event_type="agent_terminated",
                    data={
                        "agent_id": str(agent_id),
                        "process_id": self.process_id,
                        "success": True,
                    },
                )
            else:
                logger.error(f"[{self.process_id}] ✗ Failed to terminate agent {agent_id}")

        except Exception as e:
            logger.error(f"[{self.process_id}] Error terminating agent: {e}", exc_info=True)

    async def _handle_shutdown_command(self, data: Dict) -> None:
        """Handle worker shutdown command.

        Args:
            data: Command data with graceful flag
        """
        graceful = data.get("graceful", True)
        logger.info(f"[{self.process_id}] Shutdown command received (graceful={graceful})")
        await self.stop(graceful=graceful)

    # ===== Run Method =====

    async def run(self) -> None:
        """Main run loop for worker process."""
        try:
            if not await self.start():
                logger.error(f"[{self.process_id}] Failed to start worker")
                return

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            logger.info(f"[{self.process_id}] Worker shutting down...")

        except Exception as e:
            logger.error(f"[{self.process_id}] Worker error: {e}", exc_info=True)

        finally:
            await self.stop(graceful=True)


def run_worker_process(
    pool_name: str,
    max_agents: int = 10,
    heartbeat_interval: int = 30,
    redis_url: Optional[str] = None,
    role_class: Optional[Type[BaseAgentRole]] = None,
) -> None:
    """Entry point for worker process.

    This function is called by multiprocessing.Process to start a worker.

    Args:
        pool_name: Pool name
        max_agents: Maximum agents
        heartbeat_interval: Heartbeat interval
        redis_url: Redis URL
        role_class: (Optional) Role class for backward compatibility. If None, creates universal worker.
    """
    # Create new event loop for this process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Create worker (universal or role-specific)
    worker = AgentPoolWorker(
        pool_name=pool_name,
        max_agents=max_agents,
        heartbeat_interval=heartbeat_interval,
        redis_url=redis_url,
        role_class=role_class,
    )

    # Run worker
    try:
        loop.run_until_complete(worker.run())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by keyboard")
    finally:
        loop.close()
