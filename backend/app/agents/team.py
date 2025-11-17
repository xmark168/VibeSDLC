"""
Agent Team Orchestrator

Simplified team management inspired by MetaGPT.
"""

import logging
from typing import Optional

from app.agents.base import Environment, Role

logger = logging.getLogger(__name__)


class AgentTeam:
    """
    Agent Team - manages and orchestrates multiple agents.

    Simple wrapper around Environment with convenient methods.

    Example:
        team = AgentTeam()
        team.hire([TeamLeaderAgent(), DeveloperAgent()])
        await team.start("Build a login feature")
    """

    def __init__(self, context: Optional[any] = None):
        self.env = Environment(context=context)

    def hire(self, roles: list[Role]) -> None:
        """
        Register agents in the team.

        Args:
            roles: List of Role instances to add
        """
        self.env.add_roles(roles)
        logger.info(f"Hired {len(roles)} agents: {[r.name for r in roles]}")

    async def start(self, initial_message: str = "", n_round: int = 10):
        """
        Start the team with an optional initial message.

        Args:
            initial_message: Optional user message to kick off work
            n_round: Maximum rounds to execute

        Returns:
            Message history
        """
        if initial_message:
            # Import here to avoid circular dependency
            from app.agents.base import Message
            from app.agents.implementations.team_leader import UserRequest

            msg = Message(
                content=initial_message,
                cause_by=UserRequest,
                sent_from="User"
            )
            self.env.publish_message(msg)

        return await self.env.run(n_round=n_round)

    async def run(self, n_round: int = 10):
        """Run the team for n rounds."""
        return await self.env.run(n_round=n_round)

    def get_history(self):
        """Get all message history."""
        return self.env.history

    def __str__(self):
        return f"AgentTeam(agents={len(self.env.roles)})"
