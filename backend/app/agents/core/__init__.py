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
from .agent_pool_manager import AgentPoolManager
from .agent_monitor import AgentMonitor
from .prompt_utils import (
    load_prompts_yaml,
    resolve_shared_context,
    get_task_prompts,
    extract_agent_personality,
    build_system_prompt,
    build_user_prompt,
)

# Import AgentStatus from models for convenience
from app.models import AgentStatus

# Singleton monitor instance
_monitor_instance: Optional[AgentMonitor] = None


def get_agent_monitor() -> AgentMonitor:
    """Get singleton AgentMonitor instance.
    
    The monitor aggregates statistics from all AgentPoolManager instances
    registered in the system.
    
    Returns:
        AgentMonitor singleton instance
    """
    global _monitor_instance
    if _monitor_instance is None:
        # Lazy import to avoid circular dependency
        from app.api.routes.agent_management import _manager_registry
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
]
