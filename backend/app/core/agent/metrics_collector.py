"""Real-time metrics collection and streaming for agent system.

Provides centralized metrics collection with buffering, batch persistence,
and SSE broadcasting for real-time monitoring dashboards.

Metrics types:
- Execution metrics (duration, tokens, success/failure)
- Pool metrics (utilization, agent counts)
- SLA metrics (latency percentiles, violations)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricEvent:
    """Single metric event."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass
class ExecutionMetrics:
    """Metrics for a single agent execution."""
    execution_id: UUID
    agent_id: UUID
    agent_type: str
    project_id: UUID
    
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    tokens_used: int = 0
    llm_calls: int = 0
    
    success: bool = False
    error_type: Optional[str] = None
    
    task_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": str(self.execution_id),
            "agent_id": str(self.agent_id),
            "agent_type": self.agent_type,
            "project_id": str(self.project_id),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "llm_calls": self.llm_calls,
            "success": self.success,
            "error_type": self.error_type,
            "task_type": self.task_type,
        }


class MetricsCollector:
    """Real-time metrics collection with buffering and streaming.
    
    Features:
    - Buffered metric collection to reduce DB writes
    - Automatic flushing based on buffer size or time interval
    - SSE broadcasting for real-time updates
    - Aggregation support for histograms
    """
    
    def __init__(
        self,
        flush_interval: int = 10,
        buffer_size: int = 100,
        enable_sse: bool = True,
    ):
        """Initialize metrics collector.
        
        Args:
            flush_interval: Seconds between automatic flushes
            buffer_size: Max events before auto-flush
            enable_sse: Enable SSE broadcasting
        """
        self.flush_interval = flush_interval
        self.buffer_size = buffer_size
        self.enable_sse = enable_sse
        
        self._buffer: List[MetricEvent] = []
        self._execution_buffer: List[ExecutionMetrics] = []
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Aggregation buckets for histograms
        self._histogram_buckets: Dict[str, List[float]] = {}
        
        # SSE subscribers
        self._sse_callbacks: List[Callable] = []
        
        # Statistics
        self._total_events = 0
        self._total_flushes = 0
        
        logger.info(
            f"MetricsCollector initialized "
            f"(flush_interval={flush_interval}s, buffer_size={buffer_size})"
        )
    
    async def start(self) -> None:
        """Start the metrics collector background flush task."""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("MetricsCollector started")
    
    async def stop(self) -> None:
        """Stop the metrics collector and flush remaining metrics."""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self.flush()
        logger.info("MetricsCollector stopped")
    
    async def emit(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Emit a metric event.
        
        Args:
            name: Metric name (e.g., "agent.execution.duration_ms")
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags for filtering/grouping
        """
        event = MetricEvent(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {},
        )
        
        self._buffer.append(event)
        self._total_events += 1
        
        # Track histogram values
        if metric_type == MetricType.HISTOGRAM:
            if name not in self._histogram_buckets:
                self._histogram_buckets[name] = []
            self._histogram_buckets[name].append(value)
        
        # Auto-flush if buffer full
        if len(self._buffer) >= self.buffer_size:
            await self.flush()
    
    async def emit_counter(
        self,
        name: str,
        increment: float = 1,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Emit a counter increment.
        
        Args:
            name: Counter name
            increment: Amount to increment (default 1)
            tags: Optional tags
        """
        await self.emit(name, increment, MetricType.COUNTER, tags)
    
    async def emit_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Emit a gauge value.
        
        Args:
            name: Gauge name
            value: Current value
            tags: Optional tags
        """
        await self.emit(name, value, MetricType.GAUGE, tags)
    
    async def emit_timer(
        self,
        name: str,
        duration_ms: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Emit a timer/duration metric.
        
        Args:
            name: Timer name
            duration_ms: Duration in milliseconds
            tags: Optional tags
        """
        await self.emit(name, duration_ms, MetricType.TIMER, tags)
        # Also add to histogram for percentile calculation
        await self.emit(f"{name}.histogram", duration_ms, MetricType.HISTOGRAM, tags)
    
    async def record_execution(self, metrics: ExecutionMetrics) -> None:
        """Record execution metrics.
        
        Args:
            metrics: ExecutionMetrics instance
        """
        self._execution_buffer.append(metrics)
        
        # Also emit individual metrics
        tags = {
            "agent_type": metrics.agent_type,
            "task_type": metrics.task_type or "unknown",
            "success": str(metrics.success).lower(),
        }
        
        if metrics.duration_ms:
            await self.emit_timer("agent.execution.duration_ms", metrics.duration_ms, tags)
        
        await self.emit_counter("agent.execution.count", 1, tags)
        await self.emit_gauge("agent.execution.tokens", metrics.tokens_used, tags)
        await self.emit_gauge("agent.execution.llm_calls", metrics.llm_calls, tags)
        
        if metrics.success:
            await self.emit_counter("agent.execution.success", 1, tags)
        else:
            await self.emit_counter("agent.execution.failure", 1, tags)
    
    async def flush(self) -> None:
        """Flush buffered metrics to database and broadcast via SSE."""
        if not self._buffer and not self._execution_buffer:
            return
        
        events = self._buffer.copy()
        executions = self._execution_buffer.copy()
        self._buffer.clear()
        self._execution_buffer.clear()
        
        self._total_flushes += 1
        
        # Persist to database
        await self._persist_metrics(events, executions)
        
        # Broadcast via SSE
        if self.enable_sse and events:
            await self._broadcast_sse(events)
        
        logger.debug(
            f"Flushed {len(events)} metrics, {len(executions)} executions "
            f"(total flushes: {self._total_flushes})"
        )
    
    async def _persist_metrics(
        self,
        events: List[MetricEvent],
        executions: List[ExecutionMetrics],
    ) -> None:
        """Persist metrics to database.
        
        Args:
            events: List of metric events
            executions: List of execution metrics
        """
        if not events and not executions:
            return
        
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.models import AgentMetricsSnapshot
            
            with Session(engine) as session:
                # Aggregate events by pool
                pool_metrics: Dict[str, Dict] = {}
                
                for event in events:
                    pool_name = event.tags.get("pool_name", "default")
                    if pool_name not in pool_metrics:
                        pool_metrics[pool_name] = {
                            "total_tokens": 0,
                            "total_llm_calls": 0,
                            "total_executions": 0,
                            "successful_executions": 0,
                            "failed_executions": 0,
                            "durations": [],
                        }
                    
                    pm = pool_metrics[pool_name]
                    
                    if "tokens" in event.name:
                        pm["total_tokens"] += int(event.value)
                    elif "llm_calls" in event.name:
                        pm["total_llm_calls"] += int(event.value)
                    elif "execution.count" in event.name:
                        pm["total_executions"] += int(event.value)
                    elif "execution.success" in event.name:
                        pm["successful_executions"] += int(event.value)
                    elif "execution.failure" in event.name:
                        pm["failed_executions"] += int(event.value)
                    elif "duration" in event.name and event.metric_type == MetricType.TIMER:
                        pm["durations"].append(event.value)
                
                # Create snapshots
                for pool_name, pm in pool_metrics.items():
                    avg_duration = (
                        sum(pm["durations"]) / len(pm["durations"])
                        if pm["durations"] else None
                    )
                    
                    snapshot = AgentMetricsSnapshot(
                        pool_name=pool_name,
                        total_tokens=pm["total_tokens"],
                        total_llm_calls=pm["total_llm_calls"],
                        total_executions=pm["total_executions"],
                        successful_executions=pm["successful_executions"],
                        failed_executions=pm["failed_executions"],
                        avg_execution_duration_ms=avg_duration,
                        snapshot_metadata={"event_count": len(events)},
                    )
                    session.add(snapshot)
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}", exc_info=True)
    
    async def _broadcast_sse(self, events: List[MetricEvent]) -> None:
        """Broadcast metrics via SSE to subscribers.
        
        Args:
            events: List of metric events to broadcast
        """
        if not self._sse_callbacks:
            return
        
        data = {
            "type": "metrics_batch",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "events": [e.to_dict() for e in events[:50]],  # Limit for SSE
            "count": len(events),
        }
        
        for callback in self._sse_callbacks:
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"SSE callback error: {e}")
    
    def register_sse_callback(self, callback: Callable) -> None:
        """Register SSE broadcast callback.
        
        Args:
            callback: Async function to receive metric batches
        """
        self._sse_callbacks.append(callback)
    
    def unregister_sse_callback(self, callback: Callable) -> None:
        """Unregister SSE broadcast callback.
        
        Args:
            callback: Previously registered callback
        """
        if callback in self._sse_callbacks:
            self._sse_callbacks.remove(callback)
    
    async def _flush_loop(self) -> None:
        """Background task for periodic flushing."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}", exc_info=True)
    
    def get_histogram_percentiles(
        self,
        name: str,
        percentiles: List[int] = None,
    ) -> Dict[str, float]:
        """Calculate percentiles for a histogram metric.
        
        Args:
            name: Histogram metric name
            percentiles: Percentiles to calculate (default: p50, p95, p99)
            
        Returns:
            Dictionary of percentile values
        """
        if percentiles is None:
            percentiles = [50, 95, 99]
        
        values = self._histogram_buckets.get(name, [])
        if not values:
            return {f"p{p}": 0 for p in percentiles}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        result = {}
        for p in percentiles:
            idx = int((p / 100) * n)
            idx = min(idx, n - 1)
            result[f"p{p}"] = sorted_values[idx]
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_events": self._total_events,
            "total_flushes": self._total_flushes,
            "buffer_size": len(self._buffer),
            "execution_buffer_size": len(self._execution_buffer),
            "histogram_metrics": list(self._histogram_buckets.keys()),
            "sse_subscribers": len(self._sse_callbacks),
            "running": self._running,
        }


# Singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get singleton MetricsCollector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    
    if _metrics_collector is None:
        from app.core.config import settings
        
        _metrics_collector = MetricsCollector(
            flush_interval=getattr(settings, 'METRICS_FLUSH_INTERVAL', 10),
            buffer_size=getattr(settings, 'METRICS_BUFFER_SIZE', 100),
            enable_sse=True,
        )
    
    return _metrics_collector


async def init_metrics_collector() -> MetricsCollector:
    """Initialize and start metrics collector.
    
    Returns:
        Started MetricsCollector instance
    """
    collector = get_metrics_collector()
    await collector.start()
    return collector
