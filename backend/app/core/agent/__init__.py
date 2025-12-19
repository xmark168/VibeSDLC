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

#Singleton declaration for Agent monitor
_monitor_instance: Optional["AgentMonitor"] = None


def get_agent_monitor() -> "AgentMonitor":
    from app.services.singletons import get_pool_registry
    from .agent_monitor import AgentMonitor
    global _monitor_instance
    if _monitor_instance is None:
        registry = get_pool_registry()
        _monitor_instance = AgentMonitor(registry.get_all(), 10)
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

