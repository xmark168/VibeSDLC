"""
Base infrastructure for MetaGPT-style agent system.

This module provides the foundation for running agents in a single process
with in-memory message passing (Observe-Think-Act cycle).
"""

from .message import Message, MessageQueue, Memory
from .action import Action
from .role import Role, RoleReactMode, RoleContext
from .environment import Environment

__all__ = [
    # Message system
    "Message",
    "MessageQueue",
    "Memory",
    # Action & Role
    "Action",
    "Role",
    "RoleReactMode",
    "RoleContext",
    # Environment
    "Environment",
]
