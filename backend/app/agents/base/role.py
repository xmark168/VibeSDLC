"""
Base Role Class

Implements the Observe-Think-Act cycle for agent behavior.
Inspired by MetaGPT's role architecture.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Type

from app.agents.base.action import Action
from app.agents.base.message import Message, MessageQueue, Memory

logger = logging.getLogger(__name__)


class RoleReactMode(str, Enum):
    """Reaction mode for role thinking."""
    REACT = "react"  # LLM decides dynamically
    BY_ORDER = "by_order"  # Execute actions in sequence
    PLAN_AND_ACT = "plan_and_act"  # Plan first, then execute


class RoleContext:
    """
    Context for role execution.

    Holds the role's state including message buffers, memory,
    current action, and configuration.
    """

    def __init__(self):
        # Message management
        self.msg_buffer = MessageQueue()  # Inbox
        self.working_memory = Memory()  # Short-term memory for current task
        self.memory = Memory()  # Long-term memory

        # Current state
        self.news: list[Message] = []  # New messages from observe
        self.todo: Optional[Action] = None  # Current action to execute
        self.watch: set[Type[Action]] = set()  # Actions this role watches for

        # Execution mode
        self.react_mode: RoleReactMode = RoleReactMode.BY_ORDER
        self.state: int = -1  # -1 = idle, 0+ = action index
        self.plan: list[Action] = []  # Planned actions (for PLAN_AND_ACT mode)

    @property
    def is_idle(self) -> bool:
        """Check if role has work to do."""
        return self.todo is None and not self.news

    @property
    def important_memory(self) -> Memory:
        """Get relevant memory for current context."""
        # For now, return all memory
        # Could be filtered based on context in future
        return self.memory


class Role(ABC):
    """
    Abstract base class for all agents/roles.

    Implements the core Observe-Think-Act cycle:
    1. Observe: Check for new messages matching watched actions
    2. Think: Decide what action to take next
    3. Act: Execute the chosen action
    4. Publish: Share results with other agents

    Example:
        class Developer(Role):
            def __init__(self):
                super().__init__(name="Developer", profile="Senior Developer")
                self.set_actions([WriteCode, WriteTests])
                self._watch([WriteDesign])  # React when design is done

            async def _think(self):
                # Custom thinking logic if needed
                await super()._think()

            async def _act(self):
                # Execute current action
                result = await self.rc.todo.run(self.rc.important_memory)
                return Message(content=result, sent_from=self.name)
    """

    def __init__(self, name: str = "", profile: str = "", context: Any = None):
        self.name = name or self.__class__.__name__
        self.profile = profile or name
        self.rc = RoleContext()
        self.context = context  # Shared context (config, LLM, etc.)

        self.actions: list[Action] = []
        self.env: Optional[Any] = None  # Set by Environment when registered

    def set_env(self, env: Any) -> None:
        """Set environment reference."""
        self.env = env

    def set_actions(self, actions: list[Action]) -> None:
        """Set available actions for this role."""
        self.actions = actions
        self.rc.state = 0 if actions else -1

    def _watch(self, actions: list[Type[Action]]) -> None:
        """
        Subscribe to specific action types.

        Role will only react to messages caused by these actions.

        Args:
            actions: List of Action classes to watch for
        """
        self.rc.watch = set(actions)

    def _set_react_mode(self, mode: RoleReactMode) -> None:
        """Set how role decides next action."""
        self.rc.react_mode = mode

    @property
    def is_idle(self) -> bool:
        """Check if role is idle (no pending work)."""
        return self.rc.is_idle

    def put_message(self, message: Message) -> None:
        """Receive a message (add to buffer)."""
        self.rc.msg_buffer.push(message)

    def is_send_to(self, message: Message) -> bool:
        """Check if message is addressed to this role."""
        if not message.send_to:
            return True  # Broadcast message
        return self.name in message.send_to

    # ============================================================================
    # Observe-Think-Act Cycle
    # ============================================================================

    async def _observe(self) -> None:
        """
        Observe phase: Check for new messages.

        Gets messages from buffer, filters by watched actions,
        and adds to memory.
        """
        # Get all buffered messages
        news = self.rc.msg_buffer.pop_all()

        # Filter by watched actions and recipients
        self.rc.news = [
            msg for msg in news
            if (not self.rc.watch or msg.cause_by in self.rc.watch)
            and self.is_send_to(msg)
        ]

        # Add to memory
        for msg in self.rc.news:
            self.rc.memory.add(msg)

        if self.rc.news:
            logger.info(f"{self.name} observed {len(self.rc.news)} new messages")

    async def _think(self) -> None:
        """
        Think phase: Decide next action.

        Supports three modes:
        - BY_ORDER: Execute actions sequentially
        - REACT: LLM decides dynamically (TODO)
        - PLAN_AND_ACT: Create plan then execute (TODO)
        """
        if self.rc.react_mode == RoleReactMode.BY_ORDER:
            # Execute actions in order
            if self.rc.state < len(self.actions):
                self.rc.todo = self.actions[self.rc.state]
                self.rc.state += 1
            else:
                self.rc.todo = None  # All actions completed
                self.rc.state = -1  # Back to idle

        elif self.rc.react_mode == RoleReactMode.REACT:
            # TODO: LLM decides next action
            raise NotImplementedError("REACT mode not yet implemented")

        elif self.rc.react_mode == RoleReactMode.PLAN_AND_ACT:
            # TODO: Plan first, then execute
            raise NotImplementedError("PLAN_AND_ACT mode not yet implemented")

    @abstractmethod
    async def _act(self) -> Message:
        """
        Act phase: Execute current action.

        Must be implemented by subclasses to define specific behavior.

        Returns:
            Message with action result
        """
        pass

    async def react(self) -> Optional[Message]:
        """
        Main reaction cycle: Observe → Think → Act.

        Returns:
            Message if action was taken, None if idle
        """
        # Only react if we have new messages
        if not self.rc.news:
            return None

        # Think about what to do
        await self._think()

        # Act if there's something to do
        if self.rc.todo:
            msg = await self._act()
            return msg

        return None

    async def run(self, message: Optional[Message] = None) -> Optional[Message]:
        """
        Run one execution cycle.

        Args:
            message: Optional message to process immediately

        Returns:
            Response message if any
        """
        # Add incoming message to buffer
        if message:
            self.put_message(message)

        # Observe new messages
        await self._observe()

        # React to observations
        response = await self.react()

        # Publish response if any
        if response and self.env:
            self.env.publish_message(response)

        return response

    def __str__(self):
        return f"Role({self.name}, profile={self.profile})"

    def __repr__(self):
        return self.__str__()
