"""
Task Receiver Subagent

Receives task assignments from Scrum Master and prepares them for Developer Agent execution.
This is NOT a standalone agent - it's a helper module for task assignment workflow.
"""

from .agent import TaskReceiverAgent

__all__ = ["TaskReceiverAgent"]

