"""
Base Role Class

Implements the Observe-Think-Act cycle for agent behavior.
Inspired by MetaGPT's role architecture.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Type

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

        # Planner (for PLAN_AND_ACT mode)
        self.planner: Optional[Any] = None  # Will be Planner instance

        # Database session (for database operations)
        self.db_session: Optional[Any] = None

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
        - REACT: LLM decides dynamically
        - PLAN_AND_ACT: Create plan then execute
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
            # LLM decides next action dynamically
            await self._think_react()

        elif self.rc.react_mode == RoleReactMode.PLAN_AND_ACT:
            # Plan first, then execute tasks
            await self._think_plan_and_act()

    async def _think_react(self) -> None:
        """REACT mode: LLM decides which action to take next.

        Uses the most recent messages and memory to dynamically select
        the best action from available actions.
        """
        if not self.actions:
            self.rc.todo = None
            return

        # Build prompt for LLM to select action
        action_descriptions = []
        for i, action in enumerate(self.actions):
            action_descriptions.append(
                f"{i}: {action.__class__.__name__} - {getattr(action, 'description', 'No description')}"
            )

        recent_context = "\n".join([
            f"- {msg.content[:100]}" for msg in self.rc.news[:5]
        ])

        prompt = f"""
You are {self.name} ({self.profile}).

Recent context:
{recent_context}

Available actions:
{chr(10).join(action_descriptions)}

Based on the context, which action should you take next?
Respond with ONLY the action number (0-{len(self.actions)-1}), or -1 if no action needed.

Your choice:"""

        try:
            # Get LLM response (assuming first action can be used as LLM proxy)
            if self.actions:
                llm_action = self.actions[0]
                response = await llm_action.run(prompt)
                response_text = str(response).strip()

                # Parse action index
                try:
                    action_idx = int(response_text.split()[0])
                    if 0 <= action_idx < len(self.actions):
                        self.rc.todo = self.actions[action_idx]
                        logger.info(f"{self.name} selected action {action_idx} via REACT")
                    else:
                        self.rc.todo = None
                except ValueError:
                    logger.warning(f"Invalid REACT response: {response_text}, defaulting to first action")
                    self.rc.todo = self.actions[0]
        except Exception as e:
            logger.error(f"REACT mode error: {e}, falling back to first action")
            self.rc.todo = self.actions[0] if self.actions else None

    async def _think_plan_and_act(self) -> None:
        """PLAN_AND_ACT mode: Create/follow plan to execute tasks.

        Uses the Planner to create a task plan, then executes tasks in order.
        """
        if not self.rc.planner:
            logger.warning("PLAN_AND_ACT mode requires planner, falling back to BY_ORDER")
            self.rc.react_mode = RoleReactMode.BY_ORDER
            await self._think()
            return

        # Check if we need to create a plan
        if not self.rc.planner.plan or not self.rc.planner.plan.tasks:
            # Extract goal from recent messages
            goal = self._extract_goal_from_messages()
            if goal:
                # Create plan (assuming first action is LLM-capable)
                llm_action = self.actions[0] if self.actions else None
                if llm_action:
                    await self.rc.planner.create_plan(
                        goal=goal,
                        context=self._build_context_string(),
                        llm_action=llm_action,
                    )
                    logger.info(
                        f"{self.name} created plan with {len(self.rc.planner.plan.tasks)} tasks"
                    )

        # Get next task from plan
        current_task = self.rc.planner.get_next_task()
        if current_task:
            # Map task to action based on assignee or task_type
            action = self._map_task_to_action(current_task)
            self.rc.todo = action
        else:
            self.rc.todo = None

    def _extract_goal_from_messages(self) -> str:
        """Extract goal from recent messages."""
        if not self.rc.news:
            return ""
        # Use first message content as goal
        return self.rc.news[0].content

    def _build_context_string(self) -> str:
        """Build context string from memory."""
        recent_messages = self.rc.memory.get(k=5)
        return "\n".join([msg.content for msg in recent_messages])

    def _map_task_to_action(self, task: Any) -> Optional[Action]:
        """Map a task to an available action.

        Args:
            task: Task from plan

        Returns:
            Matching Action or first action as default
        """
        # Try to match by task_type or assignee
        task_type = getattr(task, 'task_type', '').lower()
        assignee = getattr(task, 'assignee', '').lower()

        for action in self.actions:
            action_name = action.__class__.__name__.lower()
            if task_type in action_name or assignee in action_name:
                return action

        # Default to first action
        return self.actions[0] if self.actions else None

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

    # ============================================================================
    # Serialization & State Management
    # ============================================================================

    def save_state(self) -> Dict[str, Any]:
        """Save role state to dictionary for persistence.

        Returns:
            Dictionary with serialized state
        """
        state = {
            "name": self.name,
            "profile": self.profile,
            "react_mode": self.rc.react_mode.value,
            "state_index": self.rc.state,
            "memory": [msg.to_dict() for msg in self.rc.memory.storage],
            "working_memory": [msg.to_dict() for msg in self.rc.working_memory.storage],
            "action_names": [action.__class__.__name__ for action in self.actions],
            "watch_actions": [action.__name__ for action in self.rc.watch],
        }

        # Save planner state if in PLAN_AND_ACT mode
        if self.rc.planner:
            state["planner"] = self.rc.planner.to_dict()

        return state

    def load_state(self, state: Dict[str, Any]):
        """Restore role state from dictionary.

        Args:
            state: Dictionary with serialized state
        """
        self.name = state.get("name", self.name)
        self.profile = state.get("profile", self.profile)

        # Restore react mode
        mode_str = state.get("react_mode", "by_order")
        self.rc.react_mode = RoleReactMode(mode_str)

        # Restore state index
        self.rc.state = state.get("state_index", -1)

        # Restore memory
        if "memory" in state:
            self.rc.memory = Memory()
            for msg_data in state["memory"]:
                self.rc.memory.add(Message.from_dict(msg_data))

        if "working_memory" in state:
            self.rc.working_memory = Memory()
            for msg_data in state["working_memory"]:
                self.rc.working_memory.add(Message.from_dict(msg_data))

        # Restore planner if exists
        if "planner" in state and self.rc.planner:
            # Import here to avoid circular import
            from app.agents.base.planner import Planner
            self.rc.planner = Planner.from_dict(state["planner"])

        logger.info(f"Loaded state for {self.name}")

    async def save_to_redis(self, redis_client: Any, key_prefix: str = "agent_state"):
        """Save role state to Redis.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for Redis key
        """
        import json

        state = self.save_state()
        key = f"{key_prefix}:{self.name}"

        try:
            await redis_client.set(key, json.dumps(state))
            # Set expiration to 24 hours
            await redis_client.expire(key, 86400)
            logger.info(f"Saved {self.name} state to Redis: {key}")
        except Exception as e:
            logger.error(f"Failed to save state to Redis: {e}")

    async def load_from_redis(self, redis_client: Any, key_prefix: str = "agent_state"):
        """Load role state from Redis.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for Redis key

        Returns:
            True if state was loaded, False otherwise
        """
        import json

        key = f"{key_prefix}:{self.name}"

        try:
            state_json = await redis_client.get(key)
            if state_json:
                state = json.loads(state_json)
                self.load_state(state)
                logger.info(f"Loaded {self.name} state from Redis: {key}")
                return True
            else:
                logger.info(f"No saved state found in Redis for {self.name}")
                return False
        except Exception as e:
            logger.error(f"Failed to load state from Redis: {e}")
            return False

    def __str__(self):
        return f"Role({self.name}, profile={self.profile})"

    def __repr__(self):
        return self.__str__()
