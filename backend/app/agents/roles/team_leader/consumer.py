"""Team Leader Kafka consumer.

Consumes user message events and triggers Team Leader crew execution.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from app.kafka.consumer import EventHandlerConsumer
from app.kafka.event_schemas import KafkaTopics, UserMessageEvent
from app.agents.roles.team_leader.crew import TeamLeaderCrew

logger = logging.getLogger(__name__)


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

            # Prepare context for crew execution
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
