import json
import logging
from typing import Dict, Any

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.agents.task_agent import TaskAgent

logger = logging.getLogger(__name__)


class EventConsumer:
    """Kafka event consumer for AI Agent Service."""

    def __init__(self):
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.group_id = settings.KAFKA_GROUP_ID
        self.consumer: AIOKafkaConsumer | None = None
        self.task_agent = TaskAgent()

    async def start(self):
        """Start the Kafka consumer."""
        self.consumer = AIOKafkaConsumer(
            "user-events",
            "item-events",
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )
        await self.consumer.start()
        logger.info("Kafka consumer started")

        # Start consuming messages
        try:
            async for message in self.consumer:
                await self.process_event(message.topic, message.value)
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")

    async def stop(self):
        """Stop the Kafka consumer."""
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def process_event(self, topic: str, event_data: Dict[str, Any]):
        """Process incoming events from Kafka."""
        try:
            event_type = event_data.get("event_type")
            data = event_data.get("data", {})

            logger.info(f"Processing event: {event_type} from topic: {topic}")

            if topic == "user-events":
                await self.handle_user_event(event_type, data)
            elif topic == "item-events":
                await self.handle_item_event(event_type, data)

        except Exception as e:
            logger.error(f"Error processing event: {e}")

    async def handle_user_event(self, event_type: str, data: Dict[str, Any]):
        """Handle user-related events."""
        if event_type == "user.created":
            await self.task_agent.on_user_created(data)
        elif event_type == "user.updated":
            await self.task_agent.on_user_updated(data)
        elif event_type == "user.deleted":
            await self.task_agent.on_user_deleted(data)

    async def handle_item_event(self, event_type: str, data: Dict[str, Any]):
        """Handle item-related events."""
        if event_type == "item.created":
            await self.task_agent.on_item_created(data)
        elif event_type == "item.updated":
            await self.task_agent.on_item_updated(data)
        elif event_type == "item.deleted":
            await self.task_agent.on_item_deleted(data)


# Global event consumer instance
event_consumer = EventConsumer()