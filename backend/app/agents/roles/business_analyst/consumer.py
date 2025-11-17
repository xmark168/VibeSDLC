"""Business Analyst Kafka consumer.

Consumes agent routing events and triggers BA crew execution.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from app.kafka.consumer import EventHandlerConsumer
from app.kafka.event_schemas import KafkaTopics
from app.agents.roles.business_analyst.crew import BusinessAnalystCrew

logger = logging.getLogger(__name__)


class BusinessAnalystConsumer:
    """Kafka consumer for Business Analyst crew.

    Consumes:
    - AgentRoutingEvent from agent.routing topic (where to_agent = "business_analyst")

    Triggers:
    - BusinessAnalystCrew.execute() for each delegation
    - Publishes AgentResponseEvent with analysis results
    """

    def __init__(self, group_id: str = "business-analyst-consumer"):
        """Initialize Business Analyst consumer.

        Args:
            group_id: Kafka consumer group ID
        """
        self.group_id = group_id
        self.crew = BusinessAnalystCrew()
        self.consumer: Optional[EventHandlerConsumer] = None
        self._running = False

    async def handle_routing_event(self, event_data: Dict[str, Any]) -> None:
        """Handle incoming agent routing event.

        Args:
            event_data: Deserialized AgentRoutingEvent data
        """
        try:
            # Check if this event is for us
            to_agent = event_data.get("to_agent", "")
            if to_agent != "business_analyst":
                logger.debug(f"Routing event not for BA, skipping (to_agent={to_agent})")
                return

            logger.info(f"Business Analyst received delegation from {event_data.get('from_agent')}")

            # Extract context from routing event
            routing_context = event_data.get("context", {})

            # Extract IDs
            project_id = event_data.get("project_id")
            if project_id:
                project_id = UUID(project_id) if isinstance(project_id, str) else project_id

            user_id = event_data.get("user_id")
            if user_id:
                user_id = UUID(user_id) if isinstance(user_id, str) else user_id

            message_id = routing_context.get("message_id")
            if message_id:
                message_id = UUID(message_id) if isinstance(message_id, str) else message_id
            else:
                message_id = uuid4()

            # Prepare execution context
            context = {
                "user_message": routing_context.get("user_message", ""),
                "task_description": routing_context.get("task_description", ""),
                "additional_context": routing_context.get("additional_context", ""),
                "priority": routing_context.get("priority", "medium"),
                "message_id": message_id,
            }

            # Execute Business Analyst crew
            result = await self.crew.execute(
                context=context,
                project_id=project_id,
                user_id=user_id,
            )

            if result.get("success"):
                logger.info(f"Business Analyst completed task successfully")
            else:
                logger.error(f"Business Analyst execution failed: {result.get('error')}")

            # Reset crew for next execution
            self.crew.reset()

        except Exception as e:
            logger.error(f"Error handling routing event: {e}", exc_info=True)

    def _create_consumer(self) -> EventHandlerConsumer:
        """Create and configure the Kafka consumer.

        Returns:
            Configured EventHandlerConsumer
        """
        consumer = EventHandlerConsumer(
            topics=[KafkaTopics.AGENT_ROUTING.value],
            group_id=self.group_id,
        )

        # Register handler for routing events
        consumer.register_handler(
            "agent.routing.delegated",
            lambda event_data: asyncio.create_task(self.handle_routing_event(event_data))
        )

        return consumer

    async def start(self) -> None:
        """Start consuming messages."""
        if self._running:
            logger.warning("Business Analyst consumer already running")
            return

        self.consumer = self._create_consumer()
        self._running = True

        logger.info(f"Starting Business Analyst consumer (group: {self.group_id})")

        # Run consumer in background
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.consumer.consume)

    async def stop(self) -> None:
        """Stop consuming messages."""
        if not self._running:
            return

        self._running = False
        if self.consumer:
            self.consumer.stop()
            self.consumer = None

        logger.info("Business Analyst consumer stopped")

    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running
