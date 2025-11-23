"""Redis client for agent pool coordination and shared state.

This module provides async Redis client with utilities for:
- Agent registry (track agents across processes)
- Process registry (track worker processes)
- Pub/Sub for IPC (inter-process communication)
- Distributed locks for atomic operations
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.asyncio.lock import Lock

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for agent pool coordination.

    Provides high-level operations for:
    - Agent/Process registry
    - Pub/Sub messaging
    - Distributed locks
    - Atomic operations
    """

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis client.

        Args:
            redis_url: Redis connection URL (defaults to settings)
        """
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._connected = False

        logger.info(f"RedisClient initialized with URL: {self._mask_password(self.redis_url)}")

    @staticmethod
    def _mask_password(url: str) -> str:
        """Mask password in Redis URL for logging."""
        if "@" in url and ":" in url:
            parts = url.split("@")
            auth_parts = parts[0].split(":")
            if len(auth_parts) >= 3:  # redis://:<password>@host
                masked = f"{auth_parts[0]}:{auth_parts[1]}:****@{parts[1]}"
                return masked
        return url

    async def connect(self) -> bool:
        """Connect to Redis server.

        Returns:
            True if connected successfully
        """
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )

            # Test connection
            await self._client.ping()
            self._connected = True

            logger.info("✓ Connected to Redis successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        try:
            if self._pubsub:
                await self._pubsub.close()
                self._pubsub = None

            if self._client:
                await self._client.close()
                self._client = None

            self._connected = False
            logger.info("Disconnected from Redis")

        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")

    @property
    def client(self) -> Redis:
        """Get Redis client.

        Returns:
            Redis client instance

        Raises:
            RuntimeError: If not connected
        """
        if not self._connected or not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    # ===== Agent Registry Operations =====

    async def register_agent(
        self,
        agent_id: UUID,
        process_id: str,
        pool_name: str,
        role_type: str,
        project_id: UUID,
        status: str = "idle",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Register an agent in Redis.

        Args:
            agent_id: Agent UUID
            process_id: Worker process ID
            pool_name: Pool name
            role_type: Agent role type
            project_id: Project UUID
            status: Agent status
            metadata: Additional metadata

        Returns:
            True if registered successfully
        """
        try:
            agent_key = f"agent:{agent_id}"
            agent_data = {
                "agent_id": str(agent_id),
                "process_id": process_id,
                "pool_name": pool_name,
                "role_type": role_type,
                "project_id": str(project_id),
                "status": status,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "metadata": json.dumps(metadata or {}),
            }

            await self.client.hset(agent_key, mapping=agent_data)

            # Add to process's agent set
            process_agents_key = f"process:{process_id}:agents"
            await self.client.sadd(process_agents_key, str(agent_id))

            # Add to pool's agent set
            pool_agents_key = f"pool:{pool_name}:agents"
            await self.client.sadd(pool_agents_key, str(agent_id))

            logger.debug(f"Registered agent {agent_id} in Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: UUID) -> bool:
        """Unregister an agent from Redis.

        Args:
            agent_id: Agent UUID

        Returns:
            True if unregistered successfully
        """
        try:
            agent_key = f"agent:{agent_id}"

            # Get agent data before deleting
            agent_data = await self.client.hgetall(agent_key)
            if not agent_data:
                logger.warning(f"Agent {agent_id} not found in Redis")
                return False

            process_id = agent_data.get("process_id")
            pool_name = agent_data.get("pool_name")

            # Remove from sets
            if process_id:
                await self.client.srem(f"process:{process_id}:agents", str(agent_id))
            if pool_name:
                await self.client.srem(f"pool:{pool_name}:agents", str(agent_id))

            # Delete agent key
            await self.client.delete(agent_key)

            logger.debug(f"Unregistered agent {agent_id} from Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def get_agent_info(self, agent_id: UUID) -> Optional[Dict[str, Any]]:
        """Get agent information from Redis.

        Args:
            agent_id: Agent UUID

        Returns:
            Agent data dict or None if not found
        """
        try:
            agent_key = f"agent:{agent_id}"
            agent_data = await self.client.hgetall(agent_key)

            if not agent_data:
                return None

            # Parse metadata JSON
            if "metadata" in agent_data:
                agent_data["metadata"] = json.loads(agent_data["metadata"])

            return agent_data

        except Exception as e:
            logger.error(f"Failed to get agent info {agent_id}: {e}")
            return None

    async def update_agent_status(self, agent_id: UUID, status: str) -> bool:
        """Update agent status in Redis.

        Args:
            agent_id: Agent UUID
            status: New status

        Returns:
            True if updated successfully
        """
        try:
            agent_key = f"agent:{agent_id}"
            await self.client.hset(agent_key, "status", status)
            await self.client.hset(agent_key, "updated_at", datetime.now(timezone.utc).isoformat())
            return True

        except Exception as e:
            logger.error(f"Failed to update agent status {agent_id}: {e}")
            return False

    # ===== Process Registry Operations =====

    async def register_process(
        self,
        process_id: str,
        pool_name: str,
        pid: int,
        max_agents: int = 10,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Register a worker process in Redis.

        Args:
            process_id: Process ID (UUID)
            pool_name: Pool name
            pid: OS process ID
            max_agents: Max agents for this process
            metadata: Additional metadata

        Returns:
            True if registered successfully
        """
        try:
            process_key = f"process:{process_id}"
            process_data = {
                "process_id": process_id,
                "pool_name": pool_name,
                "pid": str(pid),
                "max_agents": str(max_agents),
                "agent_count": "0",
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "metadata": json.dumps(metadata or {}),
            }

            await self.client.hset(process_key, mapping=process_data)

            # Add to pool's process set with capacity score (available slots)
            pool_processes_key = f"pool:{pool_name}:processes"
            await self.client.zadd(pool_processes_key, {process_id: max_agents})

            logger.info(f"Registered process {process_id} (PID: {pid}) for pool '{pool_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to register process {process_id}: {e}")
            return False

    async def unregister_process(self, process_id: str) -> bool:
        """Unregister a worker process from Redis.

        Args:
            process_id: Process ID

        Returns:
            True if unregistered successfully
        """
        try:
            process_key = f"process:{process_id}"

            # Get process data
            process_data = await self.client.hgetall(process_key)
            if not process_data:
                logger.warning(f"Process {process_id} not found in Redis")
                return False

            pool_name = process_data.get("pool_name")

            # Remove from pool's process set
            if pool_name:
                await self.client.zrem(f"pool:{pool_name}:processes", process_id)

            # Delete process agents set
            await self.client.delete(f"process:{process_id}:agents")

            # Delete process key
            await self.client.delete(process_key)

            logger.info(f"Unregistered process {process_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister process {process_id}: {e}")
            return False

    async def update_process_heartbeat(self, process_id: str, agent_count: int) -> bool:
        """Update process heartbeat and agent count.

        Args:
            process_id: Process ID
            agent_count: Current number of agents

        Returns:
            True if updated successfully
        """
        try:
            process_key = f"process:{process_id}"

            # Update heartbeat and agent count
            await self.client.hset(process_key, "last_heartbeat", datetime.now(timezone.utc).isoformat())
            await self.client.hset(process_key, "agent_count", str(agent_count))

            # Update capacity score in sorted set (available slots)
            process_data = await self.client.hgetall(process_key)
            if process_data:
                max_agents = int(process_data.get("max_agents", 10))
                pool_name = process_data.get("pool_name")
                available_slots = max_agents - agent_count

                if pool_name:
                    pool_processes_key = f"pool:{pool_name}:processes"
                    await self.client.zadd(pool_processes_key, {process_id: available_slots})

            return True

        except Exception as e:
            logger.error(f"Failed to update process heartbeat {process_id}: {e}")
            return False

    async def get_process_info(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Get process information from Redis.

        Args:
            process_id: Process ID

        Returns:
            Process data dict or None if not found
        """
        try:
            process_key = f"process:{process_id}"
            process_data = await self.client.hgetall(process_key)

            if not process_data:
                return None

            # Parse metadata JSON
            if "metadata" in process_data:
                process_data["metadata"] = json.loads(process_data["metadata"])

            # Convert numeric fields
            if "max_agents" in process_data:
                process_data["max_agents"] = int(process_data["max_agents"])
            if "agent_count" in process_data:
                process_data["agent_count"] = int(process_data["agent_count"])
            if "pid" in process_data:
                process_data["pid"] = int(process_data["pid"])

            return process_data

        except Exception as e:
            logger.error(f"Failed to get process info {process_id}: {e}")
            return None

    async def get_pool_processes(self, pool_name: str, max_processes: int = 100) -> List[str]:
        """Get worker processes for a pool, ordered by available capacity.

        Args:
            pool_name: Pool name
            max_processes: Max number of processes to return

        Returns:
            List of process IDs ordered by available slots (most available first)
        """
        try:
            pool_processes_key = f"pool:{pool_name}:processes"

            # Get processes sorted by capacity (descending)
            process_ids = await self.client.zrevrange(pool_processes_key, 0, max_processes - 1)

            return process_ids

        except Exception as e:
            logger.error(f"Failed to get pool processes for '{pool_name}': {e}")
            return []

    async def get_pool_agent_count(self, pool_name: str) -> int:
        """Get total agent count across all processes in a pool.

        Args:
            pool_name: Pool name

        Returns:
            Total agent count
        """
        try:
            pool_agents_key = f"pool:{pool_name}:agents"
            count = await self.client.scard(pool_agents_key)
            return count

        except Exception as e:
            logger.error(f"Failed to get pool agent count for '{pool_name}': {e}")
            return 0

    # ===== Pub/Sub Operations =====

    async def publish_command(
        self,
        pool_name: str,
        command: str,
        data: Dict[str, Any],
    ) -> bool:
        """Publish a command to pool workers via pub/sub.

        Args:
            pool_name: Pool name
            command: Command type (spawn, terminate, etc.)
            data: Command data

        Returns:
            True if published successfully
        """
        try:
            channel = f"pool:{pool_name}:commands"
            message = json.dumps({
                "command": command,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            await self.client.publish(channel, message)
            logger.debug(f"Published command '{command}' to pool '{pool_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to publish command to '{pool_name}': {e}")
            return False

    async def subscribe_commands(self, pool_name: str):
        """Subscribe to pool commands channel.

        Args:
            pool_name: Pool name

        Returns:
            PubSub instance
        """
        try:
            channel = f"pool:{pool_name}:commands"

            if not self._pubsub:
                self._pubsub = self.client.pubsub()

            await self._pubsub.subscribe(channel)
            logger.info(f"Subscribed to pool '{pool_name}' commands")

            return self._pubsub

        except Exception as e:
            logger.error(f"Failed to subscribe to pool commands: {e}")
            raise

    async def publish_event(
        self,
        pool_name: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> bool:
        """Publish an event from worker to master.

        Args:
            pool_name: Pool name
            event_type: Event type (heartbeat, status, etc.)
            data: Event data

        Returns:
            True if published successfully
        """
        try:
            channel = f"pool:{pool_name}:events"
            message = json.dumps({
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            await self.client.publish(channel, message)
            return True

        except Exception as e:
            logger.error(f"Failed to publish event to '{pool_name}': {e}")
            return False

    async def subscribe_events(self, pool_name: str):
        """Subscribe to pool events channel.

        Args:
            pool_name: Pool name

        Returns:
            PubSub instance
        """
        try:
            channel = f"pool:{pool_name}:events"

            if not self._pubsub:
                self._pubsub = self.client.pubsub()

            await self._pubsub.subscribe(channel)
            logger.info(f"Subscribed to pool '{pool_name}' events")

            return self._pubsub

        except Exception as e:
            logger.error(f"Failed to subscribe to pool events: {e}")
            raise

    # ===== Distributed Lock Operations =====

    def get_lock(self, lock_name: str, timeout: int = 10) -> Lock:
        """Get a distributed lock.

        Args:
            lock_name: Lock name
            timeout: Lock timeout in seconds

        Returns:
            Redis Lock instance
        """
        return Lock(self.client, lock_name, timeout=timeout)

    async def acquire_pool_lock(self, pool_name: str, timeout: int = 5) -> Lock:
        """Acquire a lock for pool operations.

        Args:
            pool_name: Pool name
            timeout: Lock timeout in seconds

        Returns:
            Acquired lock (use with async context manager)
        """
        lock = self.get_lock(f"pool:{pool_name}:lock", timeout=timeout)
        await lock.acquire()
        return lock


# Global Redis client instance
_global_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get or create global Redis client instance.

    Returns:
        RedisClient instance
    """
    global _global_redis_client

    if _global_redis_client is None:
        _global_redis_client = RedisClient()

    return _global_redis_client


async def init_redis() -> bool:
    """Initialize global Redis client.

    Returns:
        True if initialized successfully
    """
    client = get_redis_client()
    return await client.connect()


async def close_redis() -> None:
    """Close global Redis client."""
    global _global_redis_client

    if _global_redis_client:
        await _global_redis_client.disconnect()
        _global_redis_client = None
