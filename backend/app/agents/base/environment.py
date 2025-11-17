"""
Environment - Agent Orchestration and Message Broker

Manages agent lifecycle, message routing, and execution coordination.
Inspired by MetaGPT's Environment class.
"""

import asyncio
import logging
from typing import Any, Optional

from app.agents.base.message import Message, Memory
from app.agents.base.role import Role

logger = logging.getLogger(__name__)


class Environment:
    """
    Environment orchestrates agent execution and message passing.

    Responsibilities:
    - Register agents/roles
    - Route messages between agents
    - Execute agents in rounds
    - Maintain message history
    - Detect completion (all agents idle)

    Example:
        env = Environment()
        env.add_role(TeamLeaderAgent())
        env.add_role(DeveloperAgent())

        # Publish initial message
        env.publish_message(Message(
            content="Build a feature",
            cause_by=UserRequest
        ))

        # Run for 10 rounds
        await env.run(n_round=10)

        # Get all message history
        history = env.history
    """

    def __init__(self, context: Any = None):
        self.roles: dict[str, Role] = {}  # name -> role mapping
        self.history = Memory()  # All messages ever published
        self.context = context  # Shared context (config, LLM, etc.)

    def add_role(self, role: Role) -> None:
        """
        Register a role/agent in the environment.

        Sets role's environment reference and shares context.

        Args:
            role: Role instance to register
        """
        role.set_env(self)

        if self.context:
            role.context = self.context

        self.roles[role.name] = role
        logger.info(f"Registered role: {role.name}")

    def add_roles(self, roles: list[Role]) -> None:
        """Register multiple roles."""
        for role in roles:
            self.add_role(role)

    def publish_message(self, message: Message) -> None:
        """
        Publish message to relevant agents.

        Routes message to agents based on send_to field:
        - Empty send_to: Broadcast to all agents
        - Specific names: Only to those agents

        Also archives message in history.

        Args:
            message: Message to publish
        """
        # Archive in history
        self.history.add(message)

        # Route to matching roles
        for role in self.roles.values():
            if self._is_send_to(message, role):
                role.put_message(message)

        logger.debug(f"Published message from {message.sent_from}")

    def _is_send_to(self, message: Message, role: Role) -> bool:
        """Check if message should be delivered to role."""
        if not message.send_to:
            return True  # Broadcast
        return role.name in message.send_to

    @property
    def is_idle(self) -> bool:
        """Check if all roles are idle (no pending work)."""
        return all(role.is_idle for role in self.roles.values())

    async def run(self, n_round: int = 10) -> Memory:
        """
        Execute all agents for n rounds.

        A round consists of:
        1. Each agent observes new messages
        2. Each agent reacts (think + act)
        3. Check if all agents idle (early termination)

        Args:
            n_round: Maximum number of rounds to execute

        Returns:
            Message history
        """
        logger.info(f"Starting environment execution for {n_round} rounds")
        logger.info(f"Registered roles: {list(self.roles.keys())}")

        for round_num in range(n_round):
            logger.info(f"\n{'='*60}")
            logger.info(f"Round {round_num + 1}/{n_round}")
            logger.info(f"{'='*60}")

            # Execute all roles concurrently
            futures = []
            for role in self.roles.values():
                if not role.is_idle:
                    futures.append(role.run())

            if futures:
                await asyncio.gather(*futures)
            else:
                logger.info("All roles idle in round")

            # Check if all roles are idle
            if self.is_idle:
                logger.info(f"All roles idle after round {round_num + 1}, stopping")
                break

        logger.info(f"\n{'='*60}")
        logger.info(f"Environment execution complete")
        logger.info(f"Total messages: {len(self.history)}")
        logger.info(f"{'='*60}\n")

        return self.history

    async def run_until_idle(self, max_rounds: int = 100) -> Memory:
        """
        Run until all agents are idle or max_rounds reached.

        Args:
            max_rounds: Safety limit to prevent infinite loops

        Returns:
            Message history
        """
        return await self.run(n_round=max_rounds)

    def get_role(self, name: str) -> Optional[Role]:
        """Get role by name."""
        return self.roles.get(name)

    def get_history_by_role(self, role_name: str) -> list[Message]:
        """Get all messages from specific role."""
        return self.history.get_by_role(role_name)

    def clear_history(self) -> None:
        """Clear message history."""
        self.history.clear()

    def __str__(self):
        return f"Environment(roles={len(self.roles)}, history={len(self.history)})"

    def __repr__(self):
        return self.__str__()
