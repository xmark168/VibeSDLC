"""Agent core components.

This module exports the core components for agent lifecycle management:
- BaseAgentRole: Enhanced base class with lifecycle management
- AgentPool: Pool manager for dynamic agent scaling
- AgentMonitor: System-wide monitoring
- AgentConsumer: Kafka consumer pattern
"""

from .base_role import BaseAgentRole, AgentLifecycleState
from .agent_pool import AgentPool, AgentPoolConfig
from .agent_monitor import AgentMonitor, get_agent_monitor
from .agent_consumer import AgentConsumer

__all__ = [
    "BaseAgentRole",
    "AgentLifecycleState",
    "AgentPool",
    "AgentPoolConfig",
    "AgentMonitor",
    "get_agent_monitor",
    "AgentConsumer",
]
