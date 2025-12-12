"""SLA (Service Level Agreement) monitoring for agent executions.

Monitors execution times against configured SLA thresholds and tracks violations.
Integrates with metrics collector for alerting and reporting.

SLA Levels:
- p50: 50th percentile (median) - typical response time
- p95: 95th percentile - most users experience this or better
- p99: 99th percentile - worst case for most users
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class SLASeverity(str, Enum):
    """Severity levels for SLA violations."""
    INFO = "info"          # Approaching threshold
    WARNING = "warning"    # Exceeded p95
    CRITICAL = "critical"  # Exceeded p99


@dataclass
class SLAConfig:
    """SLA configuration for a task type."""
    task_type: str
    p50_threshold_ms: int = 5000      # 5 seconds
    p95_threshold_ms: int = 15000     # 15 seconds
    p99_threshold_ms: int = 30000     # 30 seconds
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_type": self.task_type,
            "p50_threshold_ms": self.p50_threshold_ms,
            "p95_threshold_ms": self.p95_threshold_ms,
            "p99_threshold_ms": self.p99_threshold_ms,
            "enabled": self.enabled,
        }


@dataclass
class SLAViolation:
    """Record of an SLA violation."""
    id: UUID = field(default_factory=uuid4)
    task_type: str = ""
    severity: SLASeverity = SLASeverity.WARNING
    threshold_ms: int = 0
    actual_ms: int = 0
    exceeded_by_ms: int = 0
    exceeded_by_percent: float = 0.0
    
    agent_id: Optional[UUID] = None
    agent_type: Optional[str] = None
    execution_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "task_type": self.task_type,
            "severity": self.severity.value,
            "threshold_ms": self.threshold_ms,
            "actual_ms": self.actual_ms,
            "exceeded_by_ms": self.exceeded_by_ms,
            "exceeded_by_percent": round(self.exceeded_by_percent, 2),
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "agent_type": self.agent_type,
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
        }


# Default SLA configurations per task type
DEFAULT_SLA_CONFIGS: Dict[str, SLAConfig] = {
    "MESSAGE": SLAConfig(
        task_type="MESSAGE",
        p50_threshold_ms=5000,
        p95_threshold_ms=10000,
        p99_threshold_ms=30000,
    ),
    "ANALYZE_REQUIREMENTS": SLAConfig(
        task_type="ANALYZE_REQUIREMENTS",
        p50_threshold_ms=30000,
        p95_threshold_ms=60000,
        p99_threshold_ms=120000,
    ),
    "CREATE_STORIES": SLAConfig(
        task_type="CREATE_STORIES",
        p50_threshold_ms=60000,
        p95_threshold_ms=120000,
        p99_threshold_ms=180000,
    ),
    "IMPLEMENT_STORY": SLAConfig(
        task_type="IMPLEMENT_STORY",
        p50_threshold_ms=180000,
        p95_threshold_ms=300000,
        p99_threshold_ms=600000,
    ),
    "WRITE_TESTS": SLAConfig(
        task_type="WRITE_TESTS",
        p50_threshold_ms=120000,
        p95_threshold_ms=180000,
        p99_threshold_ms=360000,
    ),
    "CODE_REVIEW": SLAConfig(
        task_type="CODE_REVIEW",
        p50_threshold_ms=60000,
        p95_threshold_ms=120000,
        p99_threshold_ms=180000,
    ),
    "RESUME_WITH_ANSWER": SLAConfig(
        task_type="RESUME_WITH_ANSWER",
        p50_threshold_ms=5000,
        p95_threshold_ms=15000,
        p99_threshold_ms=30000,
    ),
}


class SLAMonitor:
    """Monitor agent executions against SLA thresholds.
    
    Features:
    - Configurable SLA thresholds per task type
    - Violation tracking and alerting
    - Integration with metrics collector
    - Historical violation analysis
    """
    
    def __init__(
        self,
        configs: Optional[Dict[str, SLAConfig]] = None,
        max_violations_stored: int = 1000,
        alert_callback: Optional[Callable] = None,
    ):
        """Initialize SLA monitor.
        
        Args:
            configs: SLA configurations per task type (uses defaults if not provided)
            max_violations_stored: Maximum violations to keep in memory
            alert_callback: Async function to call on violations
        """
        self._configs = configs or DEFAULT_SLA_CONFIGS.copy()
        self._max_violations = max_violations_stored
        self._alert_callback = alert_callback
        
        self._violations: List[SLAViolation] = []
        self._violation_counts: Dict[str, Dict[str, int]] = {}  # task_type -> severity -> count
        
        # Statistics
        self._total_checks = 0
        self._total_violations = 0
        
        logger.info(
            f"SLAMonitor initialized with {len(self._configs)} task type configs"
        )
    
    def get_config(self, task_type: str) -> SLAConfig:
        """Get SLA config for task type.
        
        Args:
            task_type: Task type string
            
        Returns:
            SLAConfig (returns default if not found)
        """
        if task_type in self._configs:
            return self._configs[task_type]
        
        # Return default config for unknown task types
        return SLAConfig(
            task_type=task_type,
            p50_threshold_ms=30000,
            p95_threshold_ms=60000,
            p99_threshold_ms=120000,
        )
    
    def set_config(self, config: SLAConfig) -> None:
        """Set or update SLA config for a task type.
        
        Args:
            config: SLAConfig to set
        """
        self._configs[config.task_type] = config
        logger.info(f"Updated SLA config for {config.task_type}")
    
    async def check_execution(
        self,
        task_type: str,
        duration_ms: int,
        agent_id: Optional[UUID] = None,
        agent_type: Optional[str] = None,
        execution_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
    ) -> Optional[SLAViolation]:
        """Check if execution violates SLA.
        
        Args:
            task_type: Type of task executed
            duration_ms: Execution duration in milliseconds
            agent_id: Agent that executed the task
            agent_type: Type of agent
            execution_id: Execution UUID
            project_id: Project UUID
            
        Returns:
            SLAViolation if threshold exceeded, None otherwise
        """
        self._total_checks += 1
        
        config = self.get_config(task_type)
        if not config.enabled:
            return None
        
        violation: Optional[SLAViolation] = None
        
        # Check thresholds from most severe to least
        if duration_ms > config.p99_threshold_ms:
            violation = self._create_violation(
                config=config,
                severity=SLASeverity.CRITICAL,
                threshold_ms=config.p99_threshold_ms,
                actual_ms=duration_ms,
                agent_id=agent_id,
                agent_type=agent_type,
                execution_id=execution_id,
                project_id=project_id,
            )
        elif duration_ms > config.p95_threshold_ms:
            violation = self._create_violation(
                config=config,
                severity=SLASeverity.WARNING,
                threshold_ms=config.p95_threshold_ms,
                actual_ms=duration_ms,
                agent_id=agent_id,
                agent_type=agent_type,
                execution_id=execution_id,
                project_id=project_id,
            )
        elif duration_ms > config.p50_threshold_ms:
            # Just log info, don't create violation for p50
            logger.debug(
                f"[SLA] {task_type} approaching threshold: "
                f"{duration_ms}ms (p50={config.p50_threshold_ms}ms)"
            )
        
        if violation:
            await self._handle_violation(violation)
        
        return violation
    
    def _create_violation(
        self,
        config: SLAConfig,
        severity: SLASeverity,
        threshold_ms: int,
        actual_ms: int,
        **kwargs,
    ) -> SLAViolation:
        """Create SLA violation record.
        
        Args:
            config: SLA config
            severity: Violation severity
            threshold_ms: Threshold that was exceeded
            actual_ms: Actual duration
            **kwargs: Additional fields
            
        Returns:
            SLAViolation instance
        """
        exceeded_by = actual_ms - threshold_ms
        exceeded_percent = (exceeded_by / threshold_ms) * 100 if threshold_ms > 0 else 0
        
        return SLAViolation(
            task_type=config.task_type,
            severity=severity,
            threshold_ms=threshold_ms,
            actual_ms=actual_ms,
            exceeded_by_ms=exceeded_by,
            exceeded_by_percent=exceeded_percent,
            **kwargs,
        )
    
    async def _handle_violation(self, violation: SLAViolation) -> None:
        """Handle SLA violation - store, count, alert.
        
        Args:
            violation: SLAViolation to handle
        """
        self._total_violations += 1
        
        # Store violation
        self._violations.append(violation)
        if len(self._violations) > self._max_violations:
            self._violations = self._violations[-self._max_violations:]
        
        # Update counts
        if violation.task_type not in self._violation_counts:
            self._violation_counts[violation.task_type] = {}
        
        severity_key = violation.severity.value
        if severity_key not in self._violation_counts[violation.task_type]:
            self._violation_counts[violation.task_type][severity_key] = 0
        self._violation_counts[violation.task_type][severity_key] += 1
        
        # Log
        log_msg = (
            f"[SLA VIOLATION] {violation.severity.value.upper()}: "
            f"{violation.task_type} took {violation.actual_ms}ms "
            f"(threshold: {violation.threshold_ms}ms, exceeded by {violation.exceeded_by_percent:.1f}%)"
        )
        
        if violation.severity == SLASeverity.CRITICAL:
            logger.error(log_msg)
        else:
            logger.warning(log_msg)
        
        # Alert callback
        if self._alert_callback:
            try:
                await self._alert_callback(violation)
            except Exception as e:
                logger.error(f"SLA alert callback failed: {e}")
        
        # Emit to metrics collector
        try:
            from app.agents.core.metrics_collector import get_metrics_collector
            collector = get_metrics_collector()
            
            await collector.emit_counter(
                "sla.violation",
                1,
                tags={
                    "task_type": violation.task_type,
                    "severity": violation.severity.value,
                    "agent_type": violation.agent_type or "unknown",
                },
            )
        except Exception as e:
            logger.debug(f"Could not emit SLA metric: {e}")
    
    def get_violations(
        self,
        task_type: Optional[str] = None,
        severity: Optional[SLASeverity] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SLAViolation]:
        """Get filtered violations.
        
        Args:
            task_type: Filter by task type
            severity: Filter by severity
            since: Filter by timestamp
            limit: Maximum results
            
        Returns:
            List of violations
        """
        violations = self._violations
        
        if task_type:
            violations = [v for v in violations if v.task_type == task_type]
        
        if severity:
            violations = [v for v in violations if v.severity == severity]
        
        if since:
            violations = [v for v in violations if v.timestamp >= since]
        
        return violations[-limit:]
    
    def acknowledge_violation(
        self,
        violation_id: UUID,
        acknowledged_by: str,
    ) -> bool:
        """Acknowledge a violation.
        
        Args:
            violation_id: Violation UUID
            acknowledged_by: User/system that acknowledged
            
        Returns:
            True if found and acknowledged
        """
        for v in self._violations:
            if v.id == violation_id:
                v.acknowledged = True
                v.acknowledged_by = acknowledged_by
                v.acknowledged_at = datetime.now(timezone.utc)
                logger.info(f"SLA violation {violation_id} acknowledged by {acknowledged_by}")
                return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get SLA monitoring statistics.
        
        Returns:
            Statistics dictionary
        """
        unacknowledged = sum(1 for v in self._violations if not v.acknowledged)
        critical_count = sum(
            1 for v in self._violations 
            if v.severity == SLASeverity.CRITICAL and not v.acknowledged
        )
        
        return {
            "total_checks": self._total_checks,
            "total_violations": self._total_violations,
            "stored_violations": len(self._violations),
            "unacknowledged_violations": unacknowledged,
            "critical_unacknowledged": critical_count,
            "violation_rate": (
                self._total_violations / self._total_checks * 100
                if self._total_checks > 0 else 0
            ),
            "violations_by_task_type": self._violation_counts,
            "configured_task_types": list(self._configs.keys()),
        }
    
    def get_summary_report(self) -> Dict[str, Any]:
        """Get summary report of SLA status.
        
        Returns:
            Summary report dictionary
        """
        stats = self.get_stats()
        
        # Get recent violations (last hour)
        from datetime import timedelta
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent = self.get_violations(since=one_hour_ago)
        
        recent_critical = sum(1 for v in recent if v.severity == SLASeverity.CRITICAL)
        recent_warning = sum(1 for v in recent if v.severity == SLASeverity.WARNING)
        
        # Health status
        if recent_critical > 5:
            health = "critical"
        elif recent_critical > 0 or recent_warning > 10:
            health = "degraded"
        else:
            health = "healthy"
        
        return {
            "health_status": health,
            "stats": stats,
            "recent_violations": {
                "count": len(recent),
                "critical": recent_critical,
                "warning": recent_warning,
            },
            "top_violators": self._get_top_violators(),
        }
    
    def _get_top_violators(self, limit: int = 5) -> List[Dict]:
        """Get task types with most violations.
        
        Args:
            limit: Number of top violators to return
            
        Returns:
            List of task type violation summaries
        """
        task_totals = {}
        for task_type, severities in self._violation_counts.items():
            total = sum(severities.values())
            task_totals[task_type] = {
                "task_type": task_type,
                "total": total,
                **severities,
            }
        
        sorted_tasks = sorted(
            task_totals.values(),
            key=lambda x: x["total"],
            reverse=True,
        )
        
        return sorted_tasks[:limit]


# Singleton instance
_sla_monitor: Optional[SLAMonitor] = None


def get_sla_monitor() -> SLAMonitor:
    """Get singleton SLAMonitor instance.
    
    Returns:
        SLAMonitor instance
    """
    global _sla_monitor
    
    if _sla_monitor is None:
        from app.core.config import settings
        
        # Load custom SLA configs from settings if available
        custom_configs = getattr(settings, 'SLA_CONFIG', None)
        configs = None
        
        if custom_configs:
            configs = {}
            for task_type, thresholds in custom_configs.items():
                configs[task_type] = SLAConfig(
                    task_type=task_type,
                    p50_threshold_ms=thresholds.get("p50_ms", 5000),
                    p95_threshold_ms=thresholds.get("p95_ms", 15000),
                    p99_threshold_ms=thresholds.get("p99_ms", 30000),
                )
        
        _sla_monitor = SLAMonitor(configs=configs)
    
    return _sla_monitor
