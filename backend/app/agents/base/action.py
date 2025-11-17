"""
Base Action Class

Actions are reusable units of work that agents can perform.
Inspired by MetaGPT's action-based architecture.
"""

from abc import ABC, abstractmethod
from typing import Any


class Action(ABC):
    """
    Abstract base class for agent actions.

    Actions encapsulate specific tasks that agents can perform.
    They are composable and reusable across different roles.

    Example:
        class WriteCode(Action):
            async def run(self, context):
                code = await self.llm.ask("Write code for: " + context)
                return code

        class Developer(Role):
            def __init__(self):
                super().__init__()
                self.set_actions([WriteCode])
    """

    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__

    @abstractmethod
    async def run(self, context: Any) -> str:
        """
        Execute the action.

        Args:
            context: Input context for the action (can be dict, str, Message, etc.)

        Returns:
            Action result as string

        Raises:
            Exception: If action execution fails
        """
        pass

    def __str__(self):
        return f"Action({self.name})"

    def __repr__(self):
        return self.__str__()
