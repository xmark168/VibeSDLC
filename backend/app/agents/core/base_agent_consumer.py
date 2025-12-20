"""Base consumer class for agent instances."""

import logging
import time
from abc import abstractmethod
from typing import Any, Dict, Optional

from app.kafka.consumer import EventHandlerConsumer
from app.kafka.event_schemas import  RouterTaskEvent, KafkaTopics
from app.models import Agent, AgentConversation
from sqlmodel import Session
from app.core.db import engine

logger = logging.getLogger(__name__)

class BaseAgentInstanceConsumer(EventHandlerConsumer):
    """Base consumer for individual agent instances."""

    def __init__(self, agent: Agent):
        """Initialize agent instance consumer."""
        self.agent = agent
        self.agent_id = agent.id
        self.project_id = agent.project_id
        self.role_type = agent.role_type
        self.human_name = agent.human_name

        topic = KafkaTopics.AGENT_TASKS.value

        group_id = f"agent_{self.agent_id}_tasks"

        super().__init__(topics=[topic], group_id=group_id)

        self.register_handler("router.task.dispatched", self._handle_router_task)
        logger.info(f"Initialized consumer for agent {self.human_name} ")

    async def _handle_router_task(self, event: RouterTaskEvent | Dict[str, Any]) -> None:
        """Handle task dispatched by Central Message Router.        """
        start_time = time.time()

        try:
            # Convert to dict if Pydantic model
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump(mode='json')
            else:
                event_data = event

            # Extract task info
            task_id = event_data.get("task_id")
            target_agent_id = event_data.get("agent_id")
            routing_reason = event_data.get("routing_reason", "unknown")
            source_event_type = event_data.get("source_event_type", "unknown")
            context = event_data.get("context", {})
            priority = event_data.get("priority", "medium")

            # FILTER: Only process tasks assigned to this agent
            if str(target_agent_id) != str(self.agent_id):
                logger.debug(
                    f"[{self.human_name}] Skipping task {task_id} - "
                    f"assigned to different agent (target: {target_agent_id}, me: {self.agent_id})"
                )
                return

            logger.info(
                f"[TASK] Agent {self.human_name}: task={task_id} RECEIVED - "
                f"source={source_event_type}, reason={routing_reason}, priority={priority}"
            )

            # Save conversation record if task originated from user message
            if source_event_type == "user.message.sent":
                self._save_conversation(
                    message_id=context.get("message_id"),
                    user_id=context.get("user_id"),
                    content=context.get("content", ""),
                    message_type=context.get("message_type", "text"),
                )

            # Call abstract method for agent to process task
            await self.process_task(event_data)

            # Log task completion
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"[TASK] Agent {self.human_name}: task={task_id} COMPLETED - "
                f"duration={duration_ms}ms"
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[TASK] Agent {self.human_name}: task={task_id if 'task_id' in dir() else 'unknown'} FAILED - "
                f"error={str(e)}, duration={duration_ms}ms",
                exc_info=True
            )

    def _save_conversation(
        self,
        message_id: Optional[str],
        user_id: Optional[str],
        content: str,
        message_type: str,
    ) -> None:
        """Save conversation record to database."""
        try:
            conversation = AgentConversation(
                project_id=self.project_id,
                sender_type="user",
                sender_name=str(user_id) if user_id else "unknown",
                recipient_type="agent",
                recipient_name=self.human_name,
                message_type=message_type,
                content=content[:2000] if content else "",
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
    async def process_task(self, task_data: Dict[str, Any]) -> None:
        """Process a task assigned by Router"""
        pass