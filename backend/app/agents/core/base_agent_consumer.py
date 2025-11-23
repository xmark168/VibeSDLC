"""Base consumer class for agent instances.

Each agent instance gets its own consumer that listens to project-specific topics.
This replaces the old role-based global consumer pattern.
"""

import asyncio
import logging
import time
from abc import abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from app.kafka.consumer import EventHandlerConsumer
from app.kafka.event_schemas import BaseKafkaEvent, UserMessageEvent, KafkaTopics
from app.models import Agent, AgentConversation

logger = logging.getLogger(__name__)


# ===== Message Logging Helper =====

def _log_message(agent_name: str, event: str, message_id: Optional[str] = None, details: str = "") -> None:
    """Log a message event with standard format."""
    msg_str = f" message={message_id}" if message_id else ""
    detail_str = f" - {details}" if details else ""
    logger.info(f"[MESSAGE] Agent {agent_name}:{msg_str} {event}{detail_str}")


class BaseAgentInstanceConsumer(EventHandlerConsumer):
    """Base consumer for individual agent instances.

    HYBRID CONSUMER GROUP STRATEGY:
    - Topic: USER_MESSAGES (global topic, partitioned by project_id)
    - Group ID: project_{project_id}_role_{role_type}
    - Load Balancing: Multiple agents of same role in project share messages via Kafka consumer group

    This allows:
    - Efficient message delivery (only project messages delivered to group)
    - Automatic load balancing across agents of same role
    - Kafka handles partition assignment and rebalancing
    - Direct message routing via agent_id field (filtered in handler)
    - Team leader default routing for unmention messages

    Example:
    - Project A has 3 developers → Consumer group "project_A_role_developer"
    - Kafka automatically distributes messages across the 3 developers
    - If message has agent_id, only matching developer processes it
    - If no agent_id, all 3 developers skip (unless team leader)
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
        # Use global USER_MESSAGES topic (partitioned by project_id for load balancing)
        topic = KafkaTopics.USER_MESSAGES.value

        # HYBRID STRATEGY: Group by project + role for load balancing
        # Multiple agents of same role in project share workload via consumer group
        group_id = f"project_{self.project_id}_role_{self.role_type}"

        # Initialize parent EventHandlerConsumer
        super().__init__(topics=[topic], group_id=group_id)

        # Register handlers for user messages
        self.register_handler("user.message.sent", self._handle_user_message)

        logger.info(
            f"Initialized consumer for agent {self.human_name} "
            f"({self.role_type}) in project {self.project_id}\n"
            f"  Topic: {topic} (global)\n"
            f"  Group ID: {group_id} (project-role load balanced)\n"
            f"  Agent ID: {self.agent_id}\n"
            f"  Strategy: Share workload with other {self.role_type}s in project"
        )

    async def _handle_user_message(self, event: UserMessageEvent | Dict[str, Any]) -> None:
        """Internal handler that routes user messages to agent.

        This method:
        1. Filters by project_id (since using global topic now)
        2. Checks if message is targeted to this specific agent
        3. Checks if message has no target (Team Leader handles these)
        4. Calls abstract process_user_message() if agent should process

        Args:
            event: UserMessageEvent or dict
        """
        start_time = time.time()

        try:
            # Convert to dict if Pydantic model
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump(mode='json')
            else:
                event_data = event

            # Extract routing info
            message_project_id = event_data.get("project_id")
            target_agent_id = event_data.get("agent_id")
            message_id = event_data.get("message_id")
            content = event_data.get("content", "")
            user_id = event_data.get("user_id")
            message_type = event_data.get("message_type", "text")

            # FILTER 1: Check project_id (since we're using global topic)
            if message_project_id and str(message_project_id) != str(self.project_id):
                logger.debug(
                    f"[{self.human_name}] Skipping message {message_id} - "
                    f"wrong project (message project: {message_project_id}, my project: {self.project_id})"
                )
                return

            logger.debug(
                f"[{self.human_name}] Received Kafka event - "
                f"message_id={message_id}, target_agent={target_agent_id}, "
                f"my_agent_id={self.agent_id}, my_role={self.role_type}"
            )

            # Routing logic:
            # 1. If message has agent_id and it's this agent -> process
            # 2. If message has no agent_id and this is Team Leader -> process
            # 3. Otherwise -> skip

            should_process = False
            routing_reason = ""

            if target_agent_id:
                # Direct mention - check if it's this agent
                if str(target_agent_id) == str(self.agent_id):
                    should_process = True
                    routing_reason = "direct_mention"
                    _log_message(
                        self.human_name, "RECEIVED",
                        message_id, f"type={message_type}, routing=direct_mention"
                    )
            else:
                # No mention - Team Leader handles
                if self.role_type == "team_leader":
                    should_process = True
                    routing_reason = "team_leader_default"
                    _log_message(
                        self.human_name, "RECEIVED",
                        message_id, f"type={message_type}, routing=team_leader_default"
                    )

            if should_process:
                # Log processing start
                _log_message(
                    self.human_name, "PROCESSING",
                    message_id, f"content_length={len(content)}"
                )

                # Persist conversation record
                self._save_conversation(
                    message_id=message_id,
                    user_id=user_id,
                    content=content,
                    message_type=message_type,
                )

                # Call abstract method for agent to process
                await self.process_user_message(event_data)

                # Log processing complete
                duration_ms = int((time.time() - start_time) * 1000)
                _log_message(
                    self.human_name, "PROCESSED",
                    message_id, f"duration={duration_ms}ms"
                )
            else:
                # Message not for this agent, skip quietly
                logger.debug(
                    f"[MESSAGE] Agent {self.human_name}: message={message_id} SKIPPED - "
                    f"target={target_agent_id or 'TeamLeader'}"
                )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            _log_message(
                self.human_name, "FAILED",
                str(message_id) if 'message_id' in dir() else None,
                f"error={str(e)}, duration={duration_ms}ms"
            )
            logger.error(
                f"Error in {self.human_name} consumer handling message: {e}",
                exc_info=True
            )

    def _save_conversation(
        self,
        message_id: Optional[str],
        user_id: Optional[str],
        content: str,
        message_type: str,
    ) -> None:
        """Save conversation record to database.

        Args:
            message_id: ID of the message
            user_id: ID of the user who sent the message
            content: Message content
            message_type: Type of message
        """
        try:
            from sqlmodel import Session
            from app.core.db import engine

            conversation = AgentConversation(
                project_id=self.project_id,
                sender_type="user",
                sender_name=str(user_id) if user_id else "unknown",
                recipient_type="agent",
                recipient_name=self.human_name,
                message_type=message_type,
                content=content[:1000] if content else "",  # Truncate long content
                extra_metadata={
                    "original_message_id": str(message_id) if message_id else None,
                    "agent_id": str(self.agent_id),
                    "role_type": self.role_type,
                }
            )

            with Session(engine) as db_session:
                db_session.add(conversation)
                db_session.commit()

        except Exception as e:
            logger.error(f"Failed to save conversation record: {e}", exc_info=True)

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
