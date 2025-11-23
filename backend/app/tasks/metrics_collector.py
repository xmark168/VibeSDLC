"""Background task for collecting agent metrics snapshots"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import Optional
from sqlmodel import Session, select, func, and_
from sqlalchemy import create_engine

from app.models import (
    AgentMetricsSnapshot,
    Agent,
    AgentStatus,
    AgentExecution,
    AgentExecutionStatus,
)
from app.core.db import get_worker_engine
from app.api.routes.agent_management import get_manager, _manager_registry
from app.agents.core.registry import ProcessRegistry, AgentRegistry
from app.agents.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and stores agent metrics snapshots periodically"""

    def __init__(
        self,
        interval_seconds: int = 300,  # 5 minutes default
        retention_days: int = 30,
    ):
        """
        Initialize metrics collector

        Args:
            interval_seconds: Time between snapshots (default 5 minutes)
            retention_days: How long to keep snapshots (default 30 days)
        """
        self.interval_seconds = interval_seconds
        self.retention_days = retention_days
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self.engine = None

    async def start(self):
        """Start the metrics collector background task"""
        if self.running:
            logger.warning("Metrics collector is already running")
            return

        self.running = True
        self.engine = get_worker_engine(pool_size=2, max_overflow=5)
        self._task = asyncio.create_task(self._collection_loop())
        logger.info(
            f"Metrics collector started (interval: {self.interval_seconds}s, "
            f"retention: {self.retention_days} days)"
        )

    async def stop(self):
        """Stop the metrics collector"""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self.engine:
            self.engine.dispose()

        logger.info("Metrics collector stopped")

    async def _collection_loop(self):
        """Main collection loop"""
        while self.running:
            try:
                await self.collect_snapshot()
                await self.cleanup_old_snapshots()
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def collect_snapshot(self):
        """Collect metrics snapshot for all pools"""
        try:
            snapshot_time = datetime.now(timezone.utc)

            for pool_name, manager in _manager_registry.items():
                try:
                    await self._collect_pool_snapshot(pool_name, snapshot_time)
                except Exception as e:
                    logger.error(
                        f"Error collecting snapshot for pool {pool_name}: {e}",
                        exc_info=True,
                    )

            logger.debug(f"Collected metrics snapshot at {snapshot_time}")
        except Exception as e:
            logger.error(f"Error collecting metrics snapshot: {e}", exc_info=True)

    async def _collect_pool_snapshot(
        self, pool_name: str, snapshot_time: datetime
    ):
        """Collect snapshot for a specific pool"""
        try:
            # Get pool stats from manager
            manager = _manager_registry.get(pool_name)
            if not manager:
                logger.warning(f"No manager found for pool {pool_name}")
                return

            stats = await manager.get_stats()

            # Get agent state distribution from Redis
            redis = get_redis_client()
            agent_registry = AgentRegistry(redis_client=redis)
            process_registry = ProcessRegistry(redis_client=redis)

            # Count agents by state
            agent_ids = await agent_registry.get_pool_agents(pool_name)
            state_counts = {
                "idle": 0,
                "busy": 0,
                "error": 0,
                "total": len(agent_ids),
            }

            for agent_id_str in agent_ids:
                try:
                    agent_info = await agent_registry.get_info(UUID(agent_id_str))
                    if agent_info:
                        state = agent_info.get("state", "idle")
                        if state == "idle":
                            state_counts["idle"] += 1
                        elif state in ["busy", "thinking", "working"]:
                            state_counts["busy"] += 1
                        elif state == "error":
                            state_counts["error"] += 1
                except Exception as e:
                    logger.warning(f"Error getting agent {agent_id_str} info: {e}")

            # Get execution metrics from database
            execution_metrics = await self._get_execution_metrics(pool_name)

            # Get process metrics from Redis
            process_count = stats.get("process_count", 0)
            total_capacity = stats.get("total_capacity", 0)
            used_capacity = state_counts["total"]
            utilization = (
                (used_capacity / total_capacity * 100) if total_capacity > 0 else 0
            )

            # Create snapshot
            snapshot = AgentMetricsSnapshot(
                snapshot_timestamp=snapshot_time,
                pool_name=pool_name,
                # Agent state counts
                total_agents=state_counts["total"],
                idle_agents=state_counts["idle"],
                busy_agents=state_counts["busy"],
                error_agents=state_counts["error"],
                # Execution metrics
                total_executions=execution_metrics["total_executions"],
                successful_executions=execution_metrics["successful_executions"],
                failed_executions=execution_metrics["failed_executions"],
                # Resource usage
                total_tokens=execution_metrics["total_tokens"],
                total_llm_calls=execution_metrics["total_llm_calls"],
                # Performance
                avg_execution_duration_ms=execution_metrics["avg_duration_ms"],
                # Process metrics
                process_count=process_count,
                total_capacity=total_capacity,
                used_capacity=used_capacity,
                utilization_percentage=utilization,
                # Metadata
                snapshot_metadata={
                    "stats": stats,
                    "agent_ids": [str(aid) for aid in agent_ids],
                },
            )

            # Save to database
            with Session(self.engine) as session:
                session.add(snapshot)
                session.commit()

            logger.debug(
                f"Saved snapshot for {pool_name}: "
                f"{state_counts['total']} agents, "
                f"{execution_metrics['total_executions']} executions"
            )

        except Exception as e:
            logger.error(
                f"Error collecting pool snapshot for {pool_name}: {e}", exc_info=True
            )

    async def _get_execution_metrics(self, pool_name: str) -> dict:
        """Get execution metrics from database for the last collection interval"""
        try:
            # Calculate time window (since last snapshot)
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                seconds=self.interval_seconds * 2
            )

            with Session(self.engine) as session:
                # Get agent types for this pool
                # Pool name format: "{role_type}_pool"
                role_type = pool_name.replace("_pool", "")

                # Query executions
                query = select(
                    func.count(AgentExecution.id).label("total"),
                    func.count(
                        AgentExecution.id
                    ).filter(
                        AgentExecution.status == AgentExecutionStatus.COMPLETED
                    ).label("successful"),
                    func.count(
                        AgentExecution.id
                    ).filter(
                        AgentExecution.status == AgentExecutionStatus.FAILED
                    ).label("failed"),
                    func.sum(AgentExecution.token_used).label("total_tokens"),
                    func.sum(AgentExecution.llm_calls).label("total_llm_calls"),
                    func.avg(AgentExecution.duration_ms).label("avg_duration"),
                ).where(
                    and_(
                        AgentExecution.agent_type.ilike(f"%{role_type}%"),
                        AgentExecution.created_at >= cutoff_time,
                    )
                )

                result = session.exec(query).first()

                if result:
                    return {
                        "total_executions": result.total or 0,
                        "successful_executions": result.successful or 0,
                        "failed_executions": result.failed or 0,
                        "total_tokens": result.total_tokens or 0,
                        "total_llm_calls": result.total_llm_calls or 0,
                        "avg_duration_ms": (
                            float(result.avg_duration) if result.avg_duration else None
                        ),
                    }

        except Exception as e:
            logger.error(f"Error getting execution metrics: {e}", exc_info=True)

        # Return empty metrics on error
        return {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_tokens": 0,
            "total_llm_calls": 0,
            "avg_duration_ms": None,
        }

    async def cleanup_old_snapshots(self):
        """Delete snapshots older than retention period"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.retention_days
            )

            with Session(self.engine) as session:
                # Delete old snapshots
                stmt = select(AgentMetricsSnapshot).where(
                    AgentMetricsSnapshot.snapshot_timestamp < cutoff_date
                )
                old_snapshots = session.exec(stmt).all()

                if old_snapshots:
                    for snapshot in old_snapshots:
                        session.delete(snapshot)
                    session.commit()
                    logger.info(
                        f"Cleaned up {len(old_snapshots)} old metric snapshots "
                        f"(older than {self.retention_days} days)"
                    )

        except Exception as e:
            logger.error(f"Error cleaning up old snapshots: {e}", exc_info=True)


# Global collector instance
_metrics_collector: Optional[MetricsCollector] = None


async def start_metrics_collector(
    interval_seconds: int = 300, retention_days: int = 30
) -> MetricsCollector:
    """
    Start the global metrics collector

    Args:
        interval_seconds: Time between snapshots (default 5 minutes)
        retention_days: How long to keep snapshots (default 30 days)

    Returns:
        MetricsCollector instance
    """
    global _metrics_collector

    if _metrics_collector and _metrics_collector.running:
        logger.warning("Metrics collector is already running")
        return _metrics_collector

    _metrics_collector = MetricsCollector(
        interval_seconds=interval_seconds, retention_days=retention_days
    )
    await _metrics_collector.start()

    return _metrics_collector


async def stop_metrics_collector():
    """Stop the global metrics collector"""
    global _metrics_collector

    if _metrics_collector:
        await _metrics_collector.stop()
        _metrics_collector = None


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector instance"""
    return _metrics_collector
