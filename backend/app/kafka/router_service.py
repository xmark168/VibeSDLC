"""Central Message Router Service.

This service subscribes to various Kafka topics and dispatches events
to appropriate routers for handling.

Architecture:
    Router Service (consumer)
        ↓ subscribes to topics
    USER_MESSAGES, AGENT_RESPONSES, APPROVAL_RESPONSES, AGENT_STATUS
        ↓ dispatches to routers
    UserMessageRouter, AgentResponseRouter, etc.
        ↓ publishes tasks
    AGENT_TASKS topic
"""

import asyncio
import logging
from typing import Any, Dict, List

from app.kafka.consumer import BaseKafkaConsumer
from app.kafka.event_schemas import KafkaTopics
from app.kafka.message_router import (
    AgentResponseRouter,
    AgentStatusRouter,
    ApprovalResponseRouter,
    BaseEventRouter,
    UserMessageRouter,
)
from app.kafka.producer import get_kafka_producer


logger = logging.getLogger(__name__)


class MessageRouterService(BaseKafkaConsumer):
    """Central routing service that subscribes to events and dispatches to routers.

    This service:
    1. Subscribes to multiple Kafka topics
    2. Receives events
    3. Dispatches to appropriate router based on event type
    4. Routers publish RouterTaskEvent to AGENT_TASKS topic
    """

    def __init__(self):
        """Initialize the router service."""
        # Subscribe to all source topics that need routing
        topics = [
            KafkaTopics.USER_MESSAGES,
            KafkaTopics.AGENT_RESPONSES,
            KafkaTopics.APPROVAL_RESPONSES,
            KafkaTopics.AGENT_STATUS,
        ]

        # Use a dedicated consumer group for the router
        super().__init__(
            topics=topics,
            group_id="message_router_service",
            auto_commit=True,
        )

        self.routers: List[BaseEventRouter] = []
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the router service.

        Initializes routers and starts consuming events.
        """
        self.logger.info("Starting Message Router Service...")

        # Initialize routers with Kafka producer
        producer = await get_kafka_producer()

        self.routers = [
            UserMessageRouter(producer),
            AgentResponseRouter(producer),
            ApprovalResponseRouter(producer),
            AgentStatusRouter(producer),
        ]

        self.logger.info(f"Initialized {len(self.routers)} routers")

        # Start consuming
        await super().start()

        self.logger.info("Message Router Service started successfully")

    async def stop(self):
        """Stop the router service."""
        self.logger.info("Stopping Message Router Service...")
        await super().stop()
        self.logger.info("Message Router Service stopped")

    async def handle_message(self, event: Dict[str, Any]) -> None:
        """Handle incoming event by dispatching to appropriate router.

        This method is called by BaseKafkaConsumer for each message.

        Args:
            event: Deserialized event dictionary
        """
        event_type = event.get("event_type", "unknown")

        self.logger.debug(f"Received event: {event_type}")

        # Dispatch to routers
        routed = False
        for router in self.routers:
            try:
                if router.should_handle(event):
                    await router.route(event)
                    routed = True
                    break  # Only first matching router handles the event
            except Exception as e:
                self.logger.error(
                    f"Error routing event {event_type} with {router.__class__.__name__}: {e}",
                    exc_info=True
                )

        if not routed:
            self.logger.warning(f"No router handled event type: {event_type}")


# Singleton instance
_router_service: MessageRouterService | None = None


async def get_router_service() -> MessageRouterService:
    """Get the global router service instance.

    Returns:
        MessageRouterService instance
    """
    global _router_service

    if _router_service is None:
        _router_service = MessageRouterService()

    return _router_service


async def start_router_service() -> MessageRouterService:
    """Start the global router service.

    Returns:
        Started MessageRouterService instance
    """
    service = await get_router_service()
    if not service.running:
        await service.start()
    return service


async def stop_router_service() -> None:
    """Stop the global router service."""
    global _router_service

    if _router_service is not None:
        await _router_service.stop()
        _router_service = None
