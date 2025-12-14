"""Base consumer class for agent instances.

NEW ARCHITECTURE (Post-Router Refactor):
- Agents subscribe to AGENT_TASKS topic only
- All routing logic handled by Central Message Router
- Agents receive RouterTaskEvent with tasks assigned to them
- Consumer group: project_{project_id}_agent_tasks (all agents in project)
"""

import asyncio
import logging
import time
from abc import abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from app.kafka.consumer import EventHandlerConsumer
from app.kafka.event_schemas import BaseKafkaEvent, RouterTaskEvent, KafkaTopics
from app.models import Agent, AgentConversation

logger = logging.getLogger(__name__)

class BaseAgentInstanceConsumer(EventHandlerConsumer):
    """Base consumer for individual agent instances.

    NEW ARCHITECTURE:
    - Topic: AGENT_TASKS (global topic with RouterTaskEvent)
    - Group ID: project_{project_id}_agent_tasks (all agents in project share this group)
    - Filtering: Each agent only processes tasks where agent_id matches
    - Routing: Handled by Central Message Router (not here)

    This provides:
    - Centralized routing logic in Router
    - Clean separation of concerns
    - Agents focus on task execution, not routing
    - Automatic load balancing via Kafka consumer groups
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

        # NEW: Subscribe to AGENT_TASKS topic
        topic = KafkaTopics.AGENT_TASKS.value

        # FIXED: Each agent has unique consumer group
        # This ensures ALL agents receive ALL tasks
        # Each agent filters by agent_id to only process its own tasks
        # Tradeoff: More messages consumed, but guaranteed delivery
        group_id = f"agent_{self.agent_id}_tasks"

        # Initialize parent EventHandlerConsumer
        super().__init__(topics=[topic], group_id=group_id)

        # Register handler for router tasks
        self.register_handler("router.task.dispatched", self._handle_router_task)

        logger.info(
            f"Initialized consumer for agent {self.human_name} "
            f"({self.role_type}) in project {self.project_id}\n"
            f"  Topic: {topic} (global task queue)\n"
            f"  Group ID: {group_id} (project-wide)\n"
            f"  Agent ID: {self.agent_id}\n"
            f"  Strategy: Filter tasks by agent_id"
        )

    async def _handle_router_task(self, event: RouterTaskEvent | Dict[str, Any]) -> None:
        """Handle task dispatched by Central Message Router.

        This method:
        1. Filters tasks by agent_id (only process tasks assigned to this agent)
        2. Extracts task context (contains original event data)
        3. Calls process_task() for agent to execute

        Args:
            event: RouterTaskEvent or dict
        """
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
    async def process_task(self, task_data: Dict[str, Any]) -> None:
        """Process a task assigned by Central Message Router.

        This method must be implemented by agent role classes.
        It should:
        1. Extract context from task_data
        2. Execute agent crew/logic based on task source
        3. Publish response back to appropriate channel

        Args:
            task_data: Dictionary containing RouterTaskEvent fields:
                - task_id: UUID of the task
                - agent_id: UUID of the agent (this agent)
                - source_event_type: Type of original event (user.message.sent, etc.)
                - source_event_id: ID of original event
                - routing_reason: Why task was routed to this agent
                - priority: Task priority level
                - context: Dict containing original event data
                    - For user messages:
                        - message_id: UUID of the message
                        - project_id: UUID of the project
                        - user_id: UUID of the user
                        - content: Message content text
                        - message_type: Type of message (text, etc.)
                    - For other events: varies by source_event_type
        """
        pass

    def __repr__(self) -> str:
        """String representation of consumer."""
        return (
            f"<AgentConsumer agent={self.human_name} "
            f"role={self.role_type} project={self.project_id}>"
        )
