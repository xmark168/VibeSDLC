"""Agent and Process Registry with Redis backend.

This module provides high-level registry operations for:
- Tracking agents across multiple worker processes
- Managing worker process lifecycle
- Load balancing and capacity management
- Health monitoring
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from app.agents.core.redis_client import RedisClient, get_redis_client
from app.models import AgentStatus

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for tracking agents across processes.

    Uses Redis as backend for distributed state management.
    """

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """Initialize agent registry.

        Args:
            redis_client: Redis client instance (defaults to global instance)
        """
        self.redis = redis_client or get_redis_client()

    async def register(
        self,
        agent_id: UUID,
        process_id: str,
        pool_name: str,
        role_type: str,
        project_id: UUID,
        status: AgentStatus = AgentStatus.idle,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Register an agent in the distributed registry.

        Args:
            agent_id: Agent UUID
            process_id: Worker process ID hosting this agent
            pool_name: Pool name
            role_type: Agent role type
            project_id: Project UUID
            status: Agent status
            metadata: Additional metadata

        Returns:
            True if registered successfully
        """
        return await self.redis.register_agent(
            agent_id=agent_id,
            process_id=process_id,
            pool_name=pool_name,
            role_type=role_type,
            project_id=project_id,
            status=status.value,
            metadata=metadata,
        )

    async def unregister(self, agent_id: UUID) -> bool:
        """Unregister an agent from the distributed registry.

        Args:
            agent_id: Agent UUID

        Returns:
            True if unregistered successfully
        """
        return await self.redis.unregister_agent(agent_id)

    async def get_info(self, agent_id: UUID) -> Optional[Dict]:
        """Get agent information.

        Args:
            agent_id: Agent UUID

        Returns:
            Agent info dict or None if not found
        """
        return await self.redis.get_agent_info(agent_id)

    async def update_status(self, agent_id: UUID, status: AgentStatus) -> bool:
        """Update agent status.

        Args:
            agent_id: Agent UUID
            status: New status

        Returns:
            True if updated successfully
        """
        return await self.redis.update_agent_status(agent_id, status.value)

    async def get_process_id(self, agent_id: UUID) -> Optional[str]:
        """Get the process ID hosting an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Process ID or None if not found
        """
        info = await self.get_info(agent_id)
        if info:
            return info.get("process_id")
        return None

    async def get_pool_agents(self, pool_name: str) -> List[str]:
        """Get all agent IDs in a pool.

        Args:
            pool_name: Pool name

        Returns:
            List of agent ID strings
        """
        try:
            pool_agents_key = f"pool:{pool_name}:agents"
            agent_ids = await self.redis.client.smembers(pool_agents_key)
            return list(agent_ids)

        except Exception as e:
            logger.error(f"Failed to get pool agents: {e}")
            return []

    async def get_pool_agent_count(self, pool_name: str) -> int:
        """Get total number of agents in a pool.

        Args:
            pool_name: Pool name

        Returns:
            Total agent count
        """
        return await self.redis.get_pool_agent_count(pool_name)


class ProcessRegistry:
    """Registry for tracking worker processes.

    Uses Redis as backend for distributed state management.
    """

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """Initialize process registry.

        Args:
            redis_client: Redis client instance (defaults to global instance)
        """
        self.redis = redis_client or get_redis_client()

    async def register(
        self,
        process_id: str,
        pool_name: str,
        pid: int,
        max_agents: int = 10,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Register a worker process.

        Args:
            process_id: Process ID (UUID string)
            pool_name: Pool name
            pid: OS process ID
            max_agents: Maximum agents for this process
            metadata: Additional metadata

        Returns:
            True if registered successfully
        """
        return await self.redis.register_process(
            process_id=process_id,
            pool_name=pool_name,
            pid=pid,
            max_agents=max_agents,
            metadata=metadata,
        )

    async def unregister(self, process_id: str) -> bool:
        """Unregister a worker process.

        Args:
            process_id: Process ID

        Returns:
            True if unregistered successfully
        """
        return await self.redis.unregister_process(process_id)

    async def update_heartbeat(self, process_id: str, agent_count: int) -> bool:
        """Update process heartbeat and agent count.

        This should be called periodically by workers to indicate they're alive.

        Args:
            process_id: Process ID
            agent_count: Current number of agents in process

        Returns:
            True if updated successfully
        """
        return await self.redis.update_process_heartbeat(process_id, agent_count)

    async def get_info(self, process_id: str) -> Optional[Dict]:
        """Get process information.

        Args:
            process_id: Process ID

        Returns:
            Process info dict or None if not found
        """
        return await self.redis.get_process_info(process_id)

    async def get_pool_processes(self, pool_name: str, max_count: int = 100) -> List[str]:
        """Get worker processes for a pool, ordered by available capacity.

        Args:
            pool_name: Pool name
            max_count: Maximum number of processes to return

        Returns:
            List of process IDs ordered by available capacity (most available first)
        """
        return await self.redis.get_pool_processes(pool_name, max_count)

    async def find_available_process(
        self,
        pool_name: str,
        min_slots: int = 1,
    ) -> Optional[Tuple[str, Dict]]:
        """Find a process with available capacity.

        Args:
            pool_name: Pool name
            min_slots: Minimum available slots required

        Returns:
            Tuple of (process_id, process_info) or None if no process available
        """
        try:
            # Get processes sorted by available capacity
            process_ids = await self.get_pool_processes(pool_name)

            for process_id in process_ids:
                info = await self.get_info(process_id)

                if not info:
                    continue

                max_agents = info.get("max_agents", 10)
                agent_count = info.get("agent_count", 0)
                available_slots = max_agents - agent_count

                if available_slots >= min_slots:
                    return (process_id, info)

            return None

        except Exception as e:
            logger.error(f"Failed to find available process: {e}")
            return None

    async def get_pool_capacity(self, pool_name: str) -> Dict[str, int]:
        """Get total capacity statistics for a pool.

        Args:
            pool_name: Pool name

        Returns:
            Dict with total_capacity, used_capacity, available_capacity
        """
        try:
            process_ids = await self.get_pool_processes(pool_name)

            total_capacity = 0
            used_capacity = 0

            for process_id in process_ids:
                info = await self.get_info(process_id)

                if not info:
                    continue

                max_agents = info.get("max_agents", 10)
                agent_count = info.get("agent_count", 0)

                total_capacity += max_agents
                used_capacity += agent_count

            return {
                "total_capacity": total_capacity,
                "used_capacity": used_capacity,
                "available_capacity": total_capacity - used_capacity,
                "process_count": len(process_ids),
            }

        except Exception as e:
            logger.error(f"Failed to get pool capacity: {e}")
            return {
                "total_capacity": 0,
                "used_capacity": 0,
                "available_capacity": 0,
                "process_count": 0,
            }

    async def cleanup_stale_processes(
        self,
        pool_name: str,
        timeout_seconds: int = 300,
    ) -> List[str]:
        """Clean up processes with stale heartbeats.

        Args:
            pool_name: Pool name
            timeout_seconds: Heartbeat timeout in seconds

        Returns:
            List of cleaned up process IDs
        """
        try:
            process_ids = await self.get_pool_processes(pool_name)
            cleaned = []
            now = datetime.now(timezone.utc)

            for process_id in process_ids:
                info = await self.get_info(process_id)

                if not info:
                    continue

                last_heartbeat_str = info.get("last_heartbeat")
                if not last_heartbeat_str:
                    # No heartbeat recorded, consider stale
                    await self.unregister(process_id)
                    cleaned.append(process_id)
                    logger.warning(f"Cleaned up process {process_id} (no heartbeat)")
                    continue

                last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
                age = (now - last_heartbeat).total_seconds()

                if age > timeout_seconds:
                    # Stale heartbeat
                    await self.unregister(process_id)
                    cleaned.append(process_id)
                    logger.warning(
                        f"Cleaned up stale process {process_id} "
                        f"(heartbeat age: {age:.0f}s > {timeout_seconds}s)"
                    )

            return cleaned

        except Exception as e:
            logger.error(f"Failed to cleanup stale processes: {e}")
            return []

    async def get_pool_stats(self, pool_name: str) -> Dict:
        """Get comprehensive statistics for a pool.

        Args:
            pool_name: Pool name

        Returns:
            Statistics dictionary
        """
        try:
            capacity = await self.get_pool_capacity(pool_name)
            agent_count = await self.redis.get_pool_agent_count(pool_name)

            return {
                "pool_name": pool_name,
                "process_count": capacity["process_count"],
                "total_capacity": capacity["total_capacity"],
                "used_capacity": capacity["used_capacity"],
                "available_capacity": capacity["available_capacity"],
                "agent_count": agent_count,
                "utilization": (
                    capacity["used_capacity"] / capacity["total_capacity"]
                    if capacity["total_capacity"] > 0
                    else 0
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get pool stats: {e}")
            return {
                "pool_name": pool_name,
                "process_count": 0,
                "total_capacity": 0,
                "used_capacity": 0,
                "available_capacity": 0,
                "agent_count": 0,
                "utilization": 0,
            }
