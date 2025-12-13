"""Agent core components."""

from typing import Optional

from .prompt_utils import (
    load_prompts_yaml,
    resolve_shared_context,
    get_task_prompts,
    extract_agent_personality,
    build_system_prompt,
    build_user_prompt,
)

_monitor_instance: Optional["AgentMonitor"] = None


def get_agent_monitor() -> "AgentMonitor":
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
    "load_prompts_yaml",
    "resolve_shared_context",
    "get_task_prompts",
    "extract_agent_personality",
    "build_system_prompt",
    "build_user_prompt",
    "MetricsCollector",
    "ExecutionMetrics",
    "get_metrics_collector",
    "init_metrics_collector",
]


def __getattr__(name: str):
    if name == "AgentPoolManager":
        from .agent_pool_manager import AgentPoolManager
        return AgentPoolManager
    elif name == "AgentMonitor":
        from .agent_monitor import AgentMonitor
        return AgentMonitor
    elif name == "AgentStatus":
        from app.models import AgentStatus
        return AgentStatus
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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
