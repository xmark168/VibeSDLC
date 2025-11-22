"""
Agent Monitor - Centralized monitoring for all agent pools.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from app.agents.core.agent_pool import AgentPool

logger = logging.getLogger(__name__)


class AgentMonitor:
    """Centralized monitor for all agent pools.

    Features:
    - Track multiple pools
    - Aggregate statistics
    - Health monitoring
    - Alert generation
    - Metrics export for dashboards
    """

    def __init__(self, alert_threshold: float = 0.5):
        """Initialize agent monitor.

        Args:
            alert_threshold: Failure rate threshold for alerts (0-1)
        """
        self.pools: Dict[str, AgentPool] = {}
        self.alert_threshold = alert_threshold

        # Monitoring state
        self.started_at: Optional[datetime] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Alert tracking
        self.alerts: List[Dict] = []
        self.max_alerts = 100

        logger.info("AgentMonitor initialized")

    async def start(self, monitor_interval: int = 30) -> bool:
        """Start the monitor.

        Args:
            monitor_interval: Seconds between monitoring checks

        Returns:
            True if started successfully
        """
        try:
            self.started_at = datetime.now(timezone.utc)
            self._monitor_task = asyncio.create_task(self._monitor_loop(monitor_interval))

            logger.info("AgentMonitor started")
            return True

        except Exception as e:
            logger.error(f"Failed to start monitor: {e}", exc_info=True)
            return False

    async def stop(self) -> bool:
        """Stop the monitor.

        Returns:
            True if stopped successfully
        """
        try:
            self._shutdown_event.set()

            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            logger.info("AgentMonitor stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop monitor: {e}", exc_info=True)
            return False

    # ===== Pool Management =====

    def register_pool(self, pool: AgentPool) -> bool:
        """Register a pool for monitoring.

        Args:
            pool: Agent pool to monitor

        Returns:
            True if registered successfully
        """
        if pool.pool_name in self.pools:
            logger.warning(f"Pool '{pool.pool_name}' already registered")
            return False

        self.pools[pool.pool_name] = pool
        logger.info(f"Pool '{pool.pool_name}' registered for monitoring")
        return True

    def unregister_pool(self, pool_name: str) -> bool:
        """Unregister a pool from monitoring.

        Args:
            pool_name: Pool name to unregister

        Returns:
            True if unregistered successfully
        """
        if pool_name not in self.pools:
            logger.warning(f"Pool '{pool_name}' not registered")
            return False

        del self.pools[pool_name]
        logger.info(f"Pool '{pool_name}' unregistered from monitoring")
        return True

    # ===== Monitoring =====

    async def _monitor_loop(self, interval: int) -> None:
        """Monitor all pools periodically."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(interval)
                await self._check_all_pools()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}", exc_info=True)

    async def _check_all_pools(self) -> None:
        """Check health of all pools and generate alerts."""
        for pool_name, pool in self.pools.items():
            try:
                stats = pool.get_pool_stats()

                # Check for alerts
                if stats["total_executions"] > 0:
                    failure_rate = stats["failed_executions"] / stats["total_executions"]

                    if failure_rate > self.alert_threshold:
                        await self._create_alert(
                            severity="WARNING",
                            pool_name=pool_name,
                            message=f"High failure rate: {failure_rate:.2%}",
                            stats=stats
                        )

                # Check if pool has no active agents
                if stats["active_agents"] == 0 and stats["total_agents"] > 0:
                    await self._create_alert(
                        severity="ERROR",
                        pool_name=pool_name,
                        message="No active agents in pool",
                        stats=stats
                    )

            except Exception as e:
                logger.error(f"Error checking pool '{pool_name}': {e}")

    async def _create_alert(
        self,
        severity: str,
        pool_name: str,
        message: str,
        stats: Dict,
    ) -> None:
        """Create an alert.

        Args:
            severity: Alert severity (INFO, WARNING, ERROR)
            pool_name: Pool name
            message: Alert message
            stats: Pool statistics
        """
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "pool_name": pool_name,
            "message": message,
            "stats": stats,
        }

        self.alerts.append(alert)

        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]

        logger.warning(f"[{severity}] Pool '{pool_name}': {message}")

    # ===== Statistics =====

    def get_system_stats(self) -> Dict:
        """Get system-wide statistics.

        Returns:
            Aggregated statistics across all pools
        """
        total_pools = len(self.pools)
        total_agents = sum(len(pool.agents) for pool in self.pools.values())
        total_executions = sum(
            sum(a.total_executions for a in pool.agents.values())
            for pool in self.pools.values()
        )
        total_successful = sum(
            sum(a.successful_executions for a in pool.agents.values())
            for pool in self.pools.values()
        )
        total_failed = sum(
            sum(a.failed_executions for a in pool.agents.values())
            for pool in self.pools.values()
        )

        return {
            "uptime_seconds": (datetime.now(timezone.utc) - self.started_at).total_seconds() if self.started_at else 0,
            "total_pools": total_pools,
            "total_agents": total_agents,
            "total_executions": total_executions,
            "successful_executions": total_successful,
            "failed_executions": total_failed,
            "success_rate": total_successful / total_executions if total_executions > 0 else 0,
            "recent_alerts": len([a for a in self.alerts if a["severity"] in ["WARNING", "ERROR"]]),
        }

    def get_pool_stats(self, pool_name: str) -> Optional[Dict]:
        """Get statistics for a specific pool.

        Args:
            pool_name: Pool name

        Returns:
            Pool statistics or None if not found
        """
        pool = self.pools.get(pool_name)
        if not pool:
            return None

        return pool.get_pool_stats()

    def get_all_pool_stats(self) -> Dict[str, Dict]:
        """Get statistics for all pools.

        Returns:
            Dictionary mapping pool names to statistics
        """
        return {
            pool_name: pool.get_pool_stats()
            for pool_name, pool in self.pools.items()
        }

    async def get_all_agent_health(self) -> Dict[str, List[Dict]]:
        """Get health status of all agents across all pools.

        Returns:
            Dictionary mapping pool names to agent health lists
        """
        health_data = {}

        for pool_name, pool in self.pools.items():
            health_data[pool_name] = await pool.get_all_agent_health()

        return health_data

    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """Get recent alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of recent alerts
        """
        return self.alerts[-limit:]

    # ===== Dashboard Data =====

    async def get_dashboard_data(self) -> Dict:
        """Get comprehensive data for monitoring dashboard.

        Returns:
            Dashboard data dictionary
        """
        system_stats = self.get_system_stats()
        pool_stats = self.get_all_pool_stats()
        agent_health = await self.get_all_agent_health()
        recent_alerts = self.get_recent_alerts()

        return {
            "system": system_stats,
            "pools": pool_stats,
            "agents": agent_health,
            "alerts": recent_alerts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global monitor instance
_global_monitor: Optional[AgentMonitor] = None


def get_agent_monitor() -> AgentMonitor:
    """Get or create global agent monitor instance.

    Returns:
        AgentMonitor instance
    """
    global _global_monitor

    if _global_monitor is None:
        _global_monitor = AgentMonitor()

    return _global_monitor
