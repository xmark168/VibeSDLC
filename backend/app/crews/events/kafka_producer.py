"""
Kafka Producer for CrewAI Event System

Publishes events to Kafka topics for event-driven agent coordination
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.core.config import settings
from app.crews.events.event_schemas import (
    BaseEvent,
    KafkaTopics,
    TaskCreatedEvent,
    TaskAssignedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    FlowStartedEvent,
    FlowStepCompletedEvent,
    FlowCompletedEvent,
    AgentStatusEvent,
)

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """
    Kafka producer for publishing crew events

    Handles connection management, serialization, and error handling
    """

    def __init__(self):
        self.producer: AIOKafkaProducer | None = None
        self._connected = False

    async def start(self):
        """Initialize and start Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                enable_idempotence=True,  # Ensure exactly-once delivery
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,
                max_in_flight_requests_per_connection=1,
                security_protocol=settings.KAFKA_SECURITY_PROTOCOL,
                sasl_mechanism=settings.KAFKA_SASL_MECHANISM,
                sasl_plain_username=settings.KAFKA_SASL_USERNAME,
                sasl_plain_password=settings.KAFKA_SASL_PASSWORD,
            )

            await self.producer.start()
            self._connected = True
            logger.info(f"Kafka producer connected to {settings.KAFKA_BOOTSTRAP_SERVERS}")

        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise

    async def stop(self):
        """Stop and cleanup Kafka producer"""
        if self.producer:
            try:
                await self.producer.stop()
                self._connected = False
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {e}")

    async def publish_event(
        self,
        topic: str,
        event: BaseEvent | dict[str, Any],
        key: str | None = None
    ) -> bool:
        """
        Publish an event to a Kafka topic

        Args:
            topic: Kafka topic name
            event: Event data (BaseEvent or dict)
            key: Optional partition key

        Returns:
            True if successful, False otherwise
        """
        if not self._connected or not self.producer:
            logger.error("Kafka producer not connected")
            return False

        try:
            # Convert Pydantic model to dict if needed
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            # Send to Kafka
            future = await self.producer.send(
                topic=topic,
                value=event_data,
                key=key
            )

            # Wait for confirmation
            metadata = await future

            logger.debug(
                f"Event published to {topic} "
                f"(partition={metadata.partition}, offset={metadata.offset})"
            )

            return True

        except KafkaError as e:
            logger.error(f"Kafka error publishing event to {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error publishing event to {topic}: {e}")
            return False

    # Convenience methods for specific event types

    async def publish_task_created(self, event: TaskCreatedEvent) -> bool:
        """Publish task created event"""
        return await self.publish_event(
            topic=KafkaTopics.TASK_QUEUE,
            event=event,
            key=event.task_id
        )

    async def publish_task_assigned(self, event: TaskAssignedEvent) -> bool:
        """Publish task assigned event"""
        return await self.publish_event(
            topic=KafkaTopics.CREW_EVENTS,
            event=event,
            key=event.task_id
        )

    async def publish_task_completed(self, event: TaskCompletedEvent) -> bool:
        """Publish task completed event"""
        return await self.publish_event(
            topic=KafkaTopics.TASK_RESULTS,
            event=event,
            key=event.task_id
        )

    async def publish_task_failed(self, event: TaskFailedEvent) -> bool:
        """Publish task failed event"""
        return await self.publish_event(
            topic=KafkaTopics.TASK_RESULTS,
            event=event,
            key=event.task_id
        )

    async def publish_flow_started(self, event: FlowStartedEvent) -> bool:
        """Publish flow started event"""
        return await self.publish_event(
            topic=KafkaTopics.FLOW_STATUS,
            event=event,
            key=event.flow_id
        )

    async def publish_flow_step_completed(self, event: FlowStepCompletedEvent) -> bool:
        """Publish flow step completed event"""
        return await self.publish_event(
            topic=KafkaTopics.FLOW_STATUS,
            event=event,
            key=event.flow_id
        )

    async def publish_flow_completed(self, event: FlowCompletedEvent) -> bool:
        """Publish flow completed event"""
        return await self.publish_event(
            topic=KafkaTopics.FLOW_STATUS,
            event=event,
            key=event.flow_id
        )

    async def publish_agent_status(self, event: AgentStatusEvent) -> bool:
        """Publish agent status event"""
        return await self.publish_event(
            topic=KafkaTopics.AGENT_STATUS,
            event=event,
            key=event.agent_id
        )


# Global producer instance
_producer: KafkaEventProducer | None = None


async def get_kafka_producer() -> KafkaEventProducer:
    """Get or create global Kafka producer instance"""
    global _producer

    if _producer is None:
        _producer = KafkaEventProducer()
        await _producer.start()

    return _producer


async def shutdown_kafka_producer():
    """Shutdown global Kafka producer"""
    global _producer

    if _producer is not None:
        await _producer.stop()
        _producer = None
