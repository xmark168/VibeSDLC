"""
Base infrastructure for MetaGPT-style agent system.

This module provides the foundation for running agents in a single process
with in-memory message passing (Observe-Think-Act cycle).
"""

from .action import Action
from .action_node import ActionNode, ActionOutput, create_action_node
from .environment import Environment
from .message import Memory, Message, MessageQueue
from .plan import Plan, Task
from .planner import Planner
from .role import Role, RoleContext, RoleReactMode

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
    # Planning
    "Plan",
    "Task",
    "Planner",
    # ActionNode
    "ActionNode",
    "ActionOutput",
    "create_action_node",
]
