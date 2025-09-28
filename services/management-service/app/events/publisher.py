import json
import logging
from typing import Any, Dict

from aiokafka import AIOKafkaProducer
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer: AIOKafkaProducer | None = None

    async def start(self):
        """Start the Kafka producer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda x: json.dumps(x).encode("utf-8"),
        )
        await self.producer.start()
        logger.info("Kafka producer started")

    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def publish_event(self, topic: str, event_data: Dict[str, Any]):
        """Publish an event to Kafka topic."""
        if not self.producer:
            logger.error("Producer not started. Call start() first.")
            return

        try:
            await self.producer.send_and_wait(topic, event_data)
            logger.info(f"Event published to topic '{topic}': {event_data}")
        except Exception as e:
            logger.error(f"Failed to publish event to topic '{topic}': {e}")

    async def publish_user_event(self, event_type: str, user_data: Dict[str, Any]):
        """Publish user-related events."""
        event = {
            "event_type": event_type,
            "timestamp": None,  # Add timestamp in service
            "data": user_data,
        }
        await self.publish_event("user-events", event)

    async def publish_item_event(self, event_type: str, item_data: Dict[str, Any]):
        """Publish item-related events."""
        event = {
            "event_type": event_type,
            "timestamp": None,  # Add timestamp in service
            "data": item_data,
        }
        await self.publish_event("item-events", event)


# Global event publisher instance
event_publisher = EventPublisher()