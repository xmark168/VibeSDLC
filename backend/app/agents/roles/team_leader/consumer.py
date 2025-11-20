"""Team Leader Kafka consumer.

Consumes user message events and triggers Team Leader crew execution.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.kafka.consumer import EventHandlerConsumer
from app.kafka.event_schemas import KafkaTopics, UserMessageEvent
from app.kafka.producer import get_kafka_producer
from app.agents.roles.team_leader.crew import TeamLeaderCrew
from app.models import BASession, BASessionStatus

logger = logging.getLogger(__name__)


def is_simple_message(content: str) -> bool:
    """Check if the message is a simple greeting or acknowledgment.

    These should be handled by Team Leader directly, not routed to specialists.

    Args:
        content: The message content

    Returns:
        True if it's a simple message
    """
    content_lower = content.lower().strip()

    # Simple greetings and start commands
    greetings = [
        "hi", "hello", "hey", "xin chào", "chào", "chào bạn",
        "good morning", "good afternoon", "good evening",
        "buổi sáng tốt lành", "chào buổi sáng",
        "bắt đầu", "start", "begin"
    ]

    # Simple acknowledgments
    acknowledgments = [
        "ok", "okay", "thanks", "thank you", "cảm ơn",
        "understood", "got it", "hiểu rồi", "được", "vâng"
    ]

    # Check exact match or starts with greeting
    for greeting in greetings:
        if content_lower == greeting or content_lower.startswith(greeting + " "):
            return True

    for ack in acknowledgments:
        if content_lower == ack or content_lower.startswith(ack + " "):
            return True

    return False


class TeamLeaderConsumer:
    """Kafka consumer for Team Leader crew.

    Consumes:
    - UserMessageEvent from user.messages topic

    Triggers:
    - TeamLeaderCrew.execute() for each user message
    - Publishes AgentRoutingEvent to delegate to specialists
    """

    def __init__(self, group_id: str = "team-leader-consumer"):
        """Initialize Team Leader consumer.

        Args:
            group_id: Kafka consumer group ID
        """
        self.group_id = group_id
        self.crew = TeamLeaderCrew()
        self.engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
        self.consumer: Optional[EventHandlerConsumer] = None
        self._running = False

    async def handle_user_message(self, event_data: Any) -> None:
        """Handle incoming user message event.

        Args:
            event_data: Deserialized UserMessageEvent data (dict or Pydantic model)
        """
        try:
            # Convert Pydantic model to dict if needed
            if hasattr(event_data, 'model_dump'):
                event_data = event_data.model_dump(mode='json')

            logger.info(f"Team Leader received user message: {event_data.get('message_id')}")

            # Extract relevant data
            message_id = UUID(event_data.get("message_id", str(uuid4())))
            project_id = event_data.get("project_id")
            if project_id:
                project_id = UUID(project_id) if isinstance(project_id, str) else project_id
            user_id = event_data.get("user_id")
            if user_id:
                user_id = UUID(user_id) if isinstance(user_id, str) else user_id
            content = event_data.get("content", "")

            # Check if this is a simple message (greeting, acknowledgment)
            # If so, let Team Leader analyze and potentially respond directly
            if not is_simple_message(content):
                # Check for active BA session in analysis phase
                with Session(self.engine) as db_session:
                    active_ba_session = db_session.exec(
                        select(BASession)
                        .where(BASession.project_id == project_id)
                        .where(BASession.status == BASessionStatus.ANALYSIS)
                        .where(BASession.current_phase == "analysis")
                        .order_by(BASession.created_at.desc())
                    ).first()

                    if active_ba_session:
                        # Route directly to BA without analysis
                        logger.info(f"Active BA session found ({active_ba_session.id}), routing directly to BA")
                        await self._route_to_ba_directly(
                            message_id=message_id,
                            project_id=project_id,
                            user_id=user_id,
                            content=content
                        )
                        return
            else:
                logger.info(f"Simple message detected: '{content}', letting Team Leader analyze")

            # No active BA session, execute Team Leader crew to analyze and route
            context = {
                "user_message": content,
                "message_id": str(message_id),
                "message_type": event_data.get("message_type", "text"),
            }

            # Execute Team Leader crew
            result = await self.crew.execute(
                context=context,
                project_id=project_id,
                user_id=user_id,
            )

            if result.get("success"):
                logger.info(f"Team Leader successfully delegated task: {result.get('delegation')}")
            else:
                logger.error(f"Team Leader execution failed: {result.get('error')}")

            # Reset crew for next execution
            self.crew.reset()

        except Exception as e:
            logger.error(f"Error handling user message: {e}", exc_info=True)

    async def _route_to_ba_directly(
        self,
        message_id: UUID,
        project_id: UUID,
        user_id: UUID,
        content: str
    ) -> None:
        """Route message directly to BA agent without LLM analysis.

        Args:
            message_id: The message ID
            project_id: The project ID
            user_id: The user ID
            content: The message content
        """
        from app.kafka.event_schemas import AgentRoutingEvent

        routing_event = AgentRoutingEvent(
            from_agent="Team Leader",
            to_agent="business_analyst",
            delegation_reason="Continuing active BA session in analysis phase",
            context={
                "user_message": content,
                "task_description": "Continue requirements gathering",
                "priority": "medium",
                "additional_context": "User is continuing conversation with BA agent",
                "message_id": str(message_id),
            },
            project_id=project_id,
            user_id=user_id
        )

        producer = await get_kafka_producer()
        await producer.publish(
            topic=KafkaTopics.AGENT_ROUTING,
            event=routing_event
        )

        logger.info(f"Routed message directly to BA agent for project {project_id}")

    def _create_consumer(self) -> EventHandlerConsumer:
        """Create and configure the Kafka consumer.

        Returns:
            Configured EventHandlerConsumer
        """
        consumer = EventHandlerConsumer(
            topics=[KafkaTopics.USER_MESSAGES.value],
            group_id=self.group_id,
        )

        # Register handler for user message events
        consumer.register_handler(
            "user.message.sent",
            lambda event_data: asyncio.create_task(self.handle_user_message(event_data))
        )

        return consumer

    async def start(self) -> None:
        """Start consuming messages."""
        if self._running:
            logger.warning("Team Leader consumer already running")
            return

        self.consumer = self._create_consumer()
        self._running = True

        logger.info(f"Starting Team Leader consumer (group: {self.group_id})")

        # Start consumer (runs consume loop in background)
        await self.consumer.start()

    async def stop(self) -> None:
        """Stop consuming messages."""
        if not self._running:
            return

        self._running = False
        if self.consumer:
            self.consumer.stop()
            self.consumer = None

        logger.info("Team Leader consumer stopped")

    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running
