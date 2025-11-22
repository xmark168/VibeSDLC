"""Base consumer class for agent instances.

Each agent instance gets its own consumer that listens to project-specific topics.
This replaces the old role-based global consumer pattern.
"""

import asyncio
import logging
from abc import abstractmethod
from typing import Any, Dict
from uuid import UUID

from app.kafka.consumer import EventHandlerConsumer
from app.kafka.event_schemas import BaseKafkaEvent, UserMessageEvent, get_project_topic
from app.models import Agent

logger = logging.getLogger(__name__)


class BaseAgentInstanceConsumer(EventHandlerConsumer):
    """Base consumer for individual agent instances.

    Each agent instance (not role) gets its own consumer with:
    - Topic: project_{project_id}_messages (all agents in same project share topic)
    - Group ID: agent_{agent_id} (each agent has unique group)

    This allows:
    - Agents to receive messages from their project
    - Direct message routing via agent_id
    - Multiple agents per role per project
    """

    def __init__(self, agent: Agent):
        """Initialize agent instance consumer.

        Args:
            agent: Agent model instance from database
        """
        self.agent = agent
        self.agent_id = agent.id
        self.project_id = agent.project_id
        self.role_type = agent.role_type
        self.human_name = agent.human_name

        # Configure topic and group ID
        topic = get_project_topic(self.project_id)
        group_id = f"agent_{self.agent_id}"

        # Initialize parent EventHandlerConsumer
        super().__init__(topics=[topic], group_id=group_id)

        # Register handlers for user messages
        self.register_handler("user.message.sent", self._handle_user_message)

        logger.info(
            f"Initialized consumer for agent {self.human_name} "
            f"({self.role_type}) in project {self.project_id}"
        )

    async def _handle_user_message(self, event: UserMessageEvent | Dict[str, Any]) -> None:
        """Internal handler that routes user messages to agent.

        This method:
        1. Checks if message is targeted to this specific agent
        2. Checks if message has no target (Team Leader handles these)
        3. Calls abstract process_user_message() if agent should process

        Args:
            event: UserMessageEvent or dict
        """
        try:
            # Convert to dict if Pydantic model
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump(mode='json')
            else:
                event_data = event

            # Extract routing info
            target_agent_id = event_data.get("agent_id")
            message_id = event_data.get("message_id")
            content = event_data.get("content", "")

            # Routing logic:
            # 1. If message has agent_id and it's this agent -> process
            # 2. If message has no agent_id and this is Team Leader -> process
            # 3. Otherwise -> skip

            should_process = False

            if target_agent_id:
                # Direct mention - check if it's this agent
                if str(target_agent_id) == str(self.agent_id):
                    should_process = True
                    logger.info(
                        f"Agent {self.human_name} received direct mention in message {message_id}"
                    )
            else:
                # No mention - Team Leader handles
                if self.role_type == "team_leader":
                    should_process = True
                    logger.info(
                        f"Team Leader {self.human_name} received general message {message_id}"
                    )

            if should_process:
                # Call abstract method for agent to process
                await self.process_user_message(event_data)
            else:
                # Message not for this agent, skip quietly
                logger.debug(
                    f"Agent {self.human_name} skipping message {message_id} "
                    f"(target: {target_agent_id or 'Team Leader'})"
                )

        except Exception as e:
            logger.error(
                f"Error in {self.human_name} consumer handling message: {e}",
                exc_info=True
            )

    @abstractmethod
    async def process_user_message(self, message_data: Dict[str, Any]) -> None:
        """Process a user message targeted to this agent.

        This method must be implemented by agent role classes.
        It should:
        1. Parse the message content
        2. Execute agent crew/logic
        3. Publish response back to WebSocket

        Args:
            message_data: Dictionary containing message fields:
                - message_id: UUID of the message
                - project_id: UUID of the project
                - user_id: UUID of the user
                - content: Message content text
                - agent_id: UUID of targeted agent (if mentioned)
                - agent_name: Name of targeted agent (if mentioned)
                - message_type: Type of message (text, etc.)
        """
        pass

    def __repr__(self) -> str:
        """String representation of consumer."""
        return (
            f"<AgentConsumer agent={self.human_name} "
            f"role={self.role_type} project={self.project_id}>"
        )
