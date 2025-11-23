"""Agent core components.

This module exports the core components for agent lifecycle management:
- AgentPool: Pool manager for dynamic agent scaling (single-process)
- AgentPoolManager: Auto-scaling pool manager (multiprocessing)
- AgentMonitor: System-wide monitoring
- Redis Client: Shared state and IPC
- Registry: Agent and process tracking

NOTE: BaseAgent pattern is now the standard. All agents (TeamLeader, Developer, 
Tester, BusinessAnalyst) inherit from BaseAgent directly.
"""

from .agent_pool import AgentPool, AgentPoolConfig
from .agent_pool_manager import AgentPoolManager
from .agent_monitor import AgentMonitor, get_agent_monitor
from .redis_client import RedisClient, get_redis_client, init_redis, close_redis
from .registry import AgentRegistry, ProcessRegistry

# Import AgentStatus from models for convenience
from app.models import AgentStatus

__all__ = [
    "AgentStatus",
    "AgentPool",
    "AgentPoolConfig",
    "AgentPoolManager",
    "AgentMonitor",
    "get_agent_monitor",
    "RedisClient",
    "get_redis_client",
    "init_redis",
    "close_redis",
    "AgentRegistry",
    "ProcessRegistry",
]
