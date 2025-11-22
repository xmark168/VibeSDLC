"""Agent core components.

This module exports the core components for agent lifecycle management:
- BaseAgentRole: Enhanced base class with lifecycle management
- AgentPool: Pool manager for dynamic agent scaling
- AgentMonitor: System-wide monitoring
- AgentConsumer: Kafka consumer pattern
"""

from .base_role import BaseAgentRole
from .agent_pool import AgentPool, AgentPoolConfig
from .agent_monitor import AgentMonitor, get_agent_monitor
from .agent_consumer import AgentConsumer

# Import AgentStatus from models for convenience
from app.models import AgentStatus

__all__ = [
    "BaseAgentRole",
    "AgentStatus",  # Replaced AgentLifecycleState with AgentStatus
    "AgentPool",
    "AgentPoolConfig",
    "AgentMonitor",
    "get_agent_monitor",
    "AgentConsumer",
]
