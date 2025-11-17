"""
Message System for Agent Communication

Provides Message dataclass, MessageQueue for async buffering,
and Memory for message history storage and retrieval.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Type
from uuid import UUID, uuid4


@dataclass
class Message:
    """
    Message exchanged between agents.

    Inspired by MetaGPT's message system - agents communicate
    through messages rather than direct method calls.
    """
    content: str
    role: str = "assistant"  # system, user, assistant

    # Message routing
    cause_by: Optional[Type] = None  # Action class that created this
    sent_from: str = ""  # Agent name that sent this
    send_to: set[str] = field(default_factory=set)  # Target agents (empty = broadcast)

    # Metadata
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        return f"Message(from={self.sent_from}, cause_by={self.cause_by.__name__ if self.cause_by else 'None'})"

    def __hash__(self):
        return hash(self.id)


class MessageQueue:
    """
    Async message queue for non-blocking agent communication.

    Each agent has a message queue to buffer incoming messages.
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    def push(self, message: Message) -> None:
        """Add message to queue (non-blocking)."""
        self._queue.put_nowait(message)

    def pop(self) -> Optional[Message]:
        """Get one message from queue (non-blocking)."""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def pop_all(self) -> list[Message]:
        """Get all messages from queue (non-blocking)."""
        messages = []
        while True:
            msg = self.pop()
            if msg is None:
                break
            messages.append(msg)
        return messages

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def size(self) -> int:
        """Get queue size."""
        return self._queue.qsize()


class Memory:
    """
    Message history storage with indexing and retrieval.

    Stores all messages chronologically and provides efficient
    querying by action type, sender, or content.
    """

    def __init__(self):
        self.storage: list[Message] = []
        self.index: dict[str, list[Message]] = {}  # Index by cause_by

    def add(self, message: Message) -> None:
        """Add message to memory."""
        if message in self.storage:
            return  # Prevent duplicates

        self.storage.append(message)

        # Index by cause_by
        if message.cause_by:
            action_name = message.cause_by.__name__
            if action_name not in self.index:
                self.index[action_name] = []
            self.index[action_name].append(message)

    def add_batch(self, messages: list[Message]) -> None:
        """Add multiple messages."""
        for msg in messages:
            self.add(msg)

    def get_by_action(self, action: Type) -> list[Message]:
        """Get all messages caused by specific action."""
        action_name = action.__name__
        return self.index.get(action_name, [])

    def get_by_actions(self, actions: list[Type]) -> list[Message]:
        """Get messages caused by any of the specified actions."""
        messages = []
        for action in actions:
            messages.extend(self.get_by_action(action))
        return messages

    def get_by_role(self, role: str) -> list[Message]:
        """Get messages sent by specific agent."""
        return [msg for msg in self.storage if msg.sent_from == role]

    def get_by_content(self, keyword: str) -> list[Message]:
        """Search messages by content keyword."""
        return [msg for msg in self.storage if keyword.lower() in msg.content.lower()]

    def get(self, k: int = 0) -> list[Message]:
        """
        Get k most recent messages.

        Args:
            k: Number of messages to retrieve. 0 = all messages.

        Returns:
            List of messages, most recent first.
        """
        if k == 0:
            return list(reversed(self.storage))
        return list(reversed(self.storage[-k:]))

    def clear(self) -> None:
        """Clear all messages."""
        self.storage.clear()
        self.index.clear()

    def count(self) -> int:
        """Get total message count."""
        return len(self.storage)

    def find_news(self, observed: list[Message], action: Type) -> list[Message]:
        """
        Find new messages not yet in memory for specific action.

        Used to detect new messages to process (idempotent processing).
        """
        already_observed = set(self.get_by_action(action))
        return [msg for msg in observed if msg not in already_observed]

    def __len__(self):
        return len(self.storage)

    def __iter__(self):
        return iter(self.storage)
