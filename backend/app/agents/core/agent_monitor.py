"""Agent monitoring system.

Lightweight monitoring coordinator that aggregates stats from AgentPoolManager
instances and provides system-wide monitoring interface.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentMonitor:
    """Lightweight monitoring coordinator for agent system.
    
    Aggregates statistics from AgentPoolManager instances and provides
    unified monitoring interface. Does NOT perform health checks (those
    are handled by individual AgentPoolManager instances).
    
    Features:
    - System-wide statistics aggregation
    - Periodic logging of key metrics
    - Optional component (system continues if monitor fails)
    """

    def __init__(
        self,
        manager_registry: Dict[str, Any],  # Dict[str, AgentPoolManager]
        monitor_interval: int = 30,
    ):
        """Initialize agent monitor.
        
        Args:
            manager_registry: Dictionary of pool managers {pool_name: AgentPoolManager}
            monitor_interval: Seconds between stat logging (default 30)
        """
        self.manager_registry = manager_registry
        self.monitor_interval = monitor_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self.started_at = datetime.now(timezone.utc)
        
        logger.info(f"AgentMonitor initialized with {len(manager_registry)} pools")

    async def start(self, monitor_interval: Optional[int] = None) -> bool:
        """Start the monitoring system.
        
        Args:
            monitor_interval: Override default monitoring interval
            
        Returns:
            True if started successfully
        """
        if self.running:
            logger.warning("Monitor is already running")
            return False
        
        if monitor_interval:
            self.monitor_interval = monitor_interval
        
        try:
            self.running = True
            self._task = asyncio.create_task(self._monitoring_loop())
            logger.info(f"✓ AgentMonitor started (interval: {self.monitor_interval}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start AgentMonitor: {e}", exc_info=True)
            self.running = False
            return False

    async def stop(self) -> bool:
        """Stop the monitoring system.
        
        Returns:
            True if stopped successfully
        """
        if not self.running:
            return True
        
        try:
            self.running = False
            
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            
            logger.info("AgentMonitor stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping AgentMonitor: {e}", exc_info=True)
            return False

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get aggregated system-wide statistics.
        
        Returns:
            Dictionary with system statistics
        """
        total_agents = 0
        total_busy = 0
        total_idle = 0
        total_executions = 0
        successful_executions = 0
        failed_executions = 0
        
        pool_stats = []
        
        for pool_name, manager in self.manager_registry.items():
            try:
                stats = await manager.get_stats()
                pool_stats.append(stats)
                
                total_agents += stats.get("total_agents", 0)
                total_busy += stats.get("busy_agents", 0)
                total_idle += stats.get("idle_agents", 0)
                total_executions += stats.get("total_executions", 0)
                successful_executions += stats.get("successful_executions", 0)
                failed_executions += stats.get("failed_executions", 0)
                
            except Exception as e:
                logger.error(f"Error getting stats from pool '{pool_name}': {e}")
        
        uptime_seconds = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        
        return {
            "uptime_seconds": uptime_seconds,
            "total_pools": len(self.manager_registry),
            "total_agents": total_agents,
            "busy_agents": total_busy,
            "idle_agents": total_idle,
            "active_agents": total_busy + total_idle,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0.0,
            "utilization": total_busy / total_agents if total_agents > 0 else 0.0,
            "pools": pool_stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_pool_stats(self, pool_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific pool.
        
        Args:
            pool_name: Name of the pool
            
        Returns:
            Pool statistics dictionary or None if pool not found
        """
        manager = self.manager_registry.get(pool_name)
        if not manager:
            logger.warning(f"Pool '{pool_name}' not found in registry")
            return None
        
        try:
            return await manager.get_stats()
        except Exception as e:
            logger.error(f"Error getting stats for pool '{pool_name}': {e}")
            return None

    async def get_all_pools_health(self) -> List[Dict[str, Any]]:
        """Get health status of all pools.
        
        Returns:
            List of pool health dictionaries
        """
        health_statuses = []
        
        for pool_name, manager in self.manager_registry.items():
            try:
                stats = await manager.get_stats()
                health_statuses.append({
                    "pool_name": pool_name,
                    "healthy": True,  # If we can get stats, pool is healthy
                    "total_agents": stats.get("total_agents", 0),
                    "active_agents": stats.get("active_agents", 0),
                    "manager_type": stats.get("manager_type", "unknown"),
                })
            except Exception as e:
                health_statuses.append({
                    "pool_name": pool_name,
                    "healthy": False,
                    "error": str(e),
                })
        
        return health_statuses

    # ===== Background Task =====

    async def _monitoring_loop(self) -> None:
        """Periodic monitoring loop that logs system statistics.
        
        This is NOT for health checking (that's done by AgentPoolManager).
        This is for system-wide observability and logging.
        """
        logger.info("AgentMonitor loop started")
        
        while self.running:
            try:
                await asyncio.sleep(self.monitor_interval)
                
                # Get and log system stats
                stats = await self.get_system_stats()
                
                logger.info(
                    f"[MONITOR] Pools: {stats['total_pools']}, "
                    f"Agents: {stats['total_agents']} "
                    f"(busy: {stats['busy_agents']}, idle: {stats['idle_agents']}), "
                    f"Executions: {stats['total_executions']} "
                    f"(success rate: {stats['success_rate']:.1%}), "
                    f"Utilization: {stats['utilization']:.1%}"
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
        
        logger.info("AgentMonitor loop stopped")
