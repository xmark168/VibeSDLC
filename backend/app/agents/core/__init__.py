"""Agent core components.

This module exports the agent pool manager and monitoring system.

ARCHITECTURE:
- AgentPoolManager: In-memory single-process pool management
- AgentMonitor: Lightweight monitoring coordinator (aggregates pool stats)
- BaseAgent pattern: All agents (TeamLeader, Developer, Tester, BusinessAnalyst)
  inherit from BaseAgent directly

REMOVED (old multiprocessing architecture):
- AgentPool (382 lines) - merged into AgentPoolManager
- MultiprocessingAgentPoolManager (512 lines) - replaced by current AgentPoolManager
- AgentPoolWorker (536 lines) - no longer needed (no multiprocessing)
- RedisClient (625 lines) - no longer needed (no IPC coordination)
- AgentRegistry/ProcessRegistry (406 lines) - no longer needed
- Old AgentMonitor (323 lines) - replaced with lightweight coordinator

Total removed: ~2,784 lines of complex multiprocessing code
"""

from typing import Optional

# Light imports (no heavy dependencies)
from .prompt_utils import (
    load_prompts_yaml,
    resolve_shared_context,
    get_task_prompts,
    extract_agent_personality,
    build_system_prompt,
    build_user_prompt,
)

# Singleton monitor instance
_monitor_instance: Optional["AgentMonitor"] = None


def get_agent_monitor() -> "AgentMonitor":
    """Get singleton AgentMonitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        from app.api.routes.agent_management import _manager_registry
        from .agent_monitor import AgentMonitor
        _monitor_instance = AgentMonitor(_manager_registry)
    return _monitor_instance


__all__ = [
    "AgentStatus",
    "AgentPoolManager",
    "AgentMonitor",
    "get_agent_monitor",
    # Prompt utilities
    "load_prompts_yaml",
    "resolve_shared_context",
    "get_task_prompts",
    "extract_agent_personality",
    "build_system_prompt",
    "build_user_prompt",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitState",
    "get_circuit_breaker_manager",
    # Metrics
    "MetricsCollector",
    "ExecutionMetrics",
    "get_metrics_collector",
    "init_metrics_collector",
    # SLA
    "SLAMonitor",
    "SLAConfig",
    "SLAViolation",
    "get_sla_monitor",
    # Warm pool
    "WarmPoolManager",
    "get_warm_pool_manager",
    "init_warm_pool_manager",
]


def __getattr__(name: str):
    """Lazy import heavy dependencies."""
    if name == "AgentPoolManager":
        from .agent_pool_manager import AgentPoolManager
        return AgentPoolManager
    elif name == "AgentMonitor":
        from .agent_monitor import AgentMonitor
        return AgentMonitor
    elif name == "AgentStatus":
        from app.models import AgentStatus
        return AgentStatus
    # Circuit breaker
    elif name == "CircuitBreaker":
        from .circuit_breaker import CircuitBreaker
        return CircuitBreaker
    elif name == "CircuitBreakerManager":
        from .circuit_breaker import CircuitBreakerManager
        return CircuitBreakerManager
    elif name == "CircuitState":
        from .circuit_breaker import CircuitState
        return CircuitState
    elif name == "get_circuit_breaker_manager":
        from .circuit_breaker import get_circuit_breaker_manager
        return get_circuit_breaker_manager
    # Metrics
    elif name == "MetricsCollector":
        from .metrics_collector import MetricsCollector
        return MetricsCollector
    elif name == "ExecutionMetrics":
        from .metrics_collector import ExecutionMetrics
        return ExecutionMetrics
    elif name == "get_metrics_collector":
        from .metrics_collector import get_metrics_collector
        return get_metrics_collector
    elif name == "init_metrics_collector":
        from .metrics_collector import init_metrics_collector
        return init_metrics_collector
    # SLA
    elif name == "SLAMonitor":
        from .sla_monitor import SLAMonitor
        return SLAMonitor
    elif name == "SLAConfig":
        from .sla_monitor import SLAConfig
        return SLAConfig
    elif name == "SLAViolation":
        from .sla_monitor import SLAViolation
        return SLAViolation
    elif name == "get_sla_monitor":
        from .sla_monitor import get_sla_monitor
        return get_sla_monitor
    # Warm pool
    elif name == "WarmPoolManager":
        from .warm_pool import WarmPoolManager
        return WarmPoolManager
    elif name == "get_warm_pool_manager":
        from .warm_pool import get_warm_pool_manager
        return get_warm_pool_manager
    elif name == "init_warm_pool_manager":
        from .warm_pool import init_warm_pool_manager
        return init_warm_pool_manager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
