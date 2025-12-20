"""
Agent monitoring system.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlmodel import Session
from app.core.db import engine
from app.services.pool_service import PoolService
from app.models import PoolType
from app.agents.core.agent_pool_manager import AgentPoolManager
from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentMonitor:
    """Monitoring coordinator for agent system."""
    def __init__(
        self,
        manager_registry: Dict[str, Any],  
        monitor_interval: int = 30,
    ):
        self.manager_registry = manager_registry
        self.monitor_interval = monitor_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self.started_at = datetime.now(timezone.utc)
        
        logger.info(f"Agent moniroting system initialized with {len(manager_registry)} pools")

    async def start(self, monitor_interval: Optional[int] = None) -> bool:
        """
        Start the monitoring system.
        """
        if self.running:
            return False
        
        if monitor_interval:
            self.monitor_interval = monitor_interval
        
        try:
            self.running = True
            self._task = asyncio.create_task(self._monitoring_loop())
            logger.info(f"Set up monitor for agent (interval: {self.monitor_interval}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start AgentMonitor: {e}", exc_info=True)
            self.running = False
            return False

    async def stop(self) -> bool:
        """Stop the monitoring system."""
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
            
            logger.info("[SYSTEM] Agent moniroting stopped!")
            return True
        except Exception as e:
            return False

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get aggregated system-wide statistics"""
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
        """Get statistics for a specific pool."""
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
        """Periodic monitoring loop that logs system statistics and triggers auto-scaling"""
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
                
                # Auto-scaling check
                if settings.AGENT_POOL_AUTO_SCALE_ENABLED:
                    await self._check_auto_scaling(stats)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
        
        logger.info("AgentMonitor loop stopped")

    async def _check_auto_scaling(self, stats: Dict[str, Any]) -> None:
        """Check if auto-scaling is needed based on pool loads.
        
        Creates overflow pools when universal pool exceeds threshold.
        """
        from app.agents.core.pool_helpers import get_pool_load, should_create_new_pool
        
        threshold = settings.AGENT_POOL_AUTO_SCALE_THRESHOLD
        
        for pool_stats in stats.get("pools", []):
            pool_name = pool_stats.get("pool_name")
            manager = self.manager_registry.get(pool_name)
            
            if not manager:
                continue
            
            load = get_pool_load(manager)
            
            # Log warning if approaching capacity
            if load >= threshold * 0.9:
                logger.warning(
                    f"[AUTO-SCALE] Pool '{pool_name}' at {load:.1%} capacity "
                    f"(threshold: {threshold:.0%})"
                )
            
            # Trigger overflow pool creation if needed
            if should_create_new_pool(manager, threshold):
                await self._create_overflow_pool(pool_name, manager)

    async def _create_overflow_pool(self) -> None:
        """Create an overflow pool when source pool is overloaded."""
        
        # Count existing overflow pools
        overflow_count = len([p for p in self.manager_registry.keys() if "overflow" in p])
        new_pool_name = f"overflow_pool_{overflow_count + 1}"
        
        # Check if we already have this pool
        if new_pool_name in self.manager_registry:
            return
        
        logger.info(f"[AUTO-SCALE] Creating overflow pool: {new_pool_name}")
        
        try:
            with Session(engine) as session:
                pool_service = PoolService(session)
                
                # Check if pool exists in DB
                db_pool = pool_service.get_pool_by_name(new_pool_name)
                
                if not db_pool:
                    db_pool = pool_service.create_pool(
                        pool_name=new_pool_name,
                        role_type=None,  # Universal overflow
                        pool_type=PoolType.FREE,
                        max_agents=settings.AGENT_POOL_MAX_AGENTS // 2,  # Half capacity
                        health_check_interval=settings.AGENT_POOL_HEALTH_CHECK_INTERVAL,
                        auto_created=True,
                    )
            
            # Create and start manager
            manager = AgentPoolManager(
                pool_name=new_pool_name,
                max_agents=db_pool.max_agents,
                health_check_interval=db_pool.health_check_interval,
                pool_id=db_pool.id,
            )
            
            if await manager.start():
                self.manager_registry[new_pool_name] = manager
                logger.info(f"[AUTO-SCALE] ✓ Created overflow pool: {new_pool_name}")
            else:
                logger.error(f"[AUTO-SCALE] ✗ Failed to start overflow pool: {new_pool_name}")
                
        except Exception as e:
            logger.error(f"[AUTO-SCALE] Error creating overflow pool: {e}", exc_info=True)
