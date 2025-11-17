"""Kafka consumer base class and utilities.

This module provides a base consumer class with automatic message deserialization,
error handling, and offset management.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from confluent_kafka import Consumer, KafkaError, KafkaException
from pydantic import ValidationError

from app.core.config import settings
from app.kafka.event_schemas import BaseKafkaEvent, get_event_schema

logger = logging.getLogger(__name__)


class BaseKafkaConsumer(ABC):
    """Base class for Kafka consumers with automatic deserialization and error handling."""

    def __init__(
        self,
        topics: List[str],
        group_id: Optional[str] = None,
        auto_commit: bool = True,
    ):
        """Initialize Kafka consumer.

        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID (defaults to settings.KAFKA_GROUP_ID)
            auto_commit: Whether to auto-commit offsets
        """
        self.topics = topics
        self.group_id = group_id or settings.KAFKA_GROUP_ID
        self.auto_commit = auto_commit
        self.consumer: Optional[Consumer] = None
        self.running = False
        self._consume_task: Optional[asyncio.Task] = None

    def _build_config(self) -> Dict[str, Any]:
        """Build Kafka consumer configuration."""
        config = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": self.group_id,
            "auto.offset.reset": settings.KAFKA_AUTO_OFFSET_RESET,
            "enable.auto.commit": self.auto_commit,
            "session.timeout.ms": 30000,
            "max.poll.interval.ms": 300000,
            "enable.partition.eof": False,
        }

        # Add SASL authentication if configured
        if settings.KAFKA_SASL_MECHANISM:
            config.update({
                "security.protocol": settings.KAFKA_SECURITY_PROTOCOL,
                "sasl.mechanism": settings.KAFKA_SASL_MECHANISM,
                "sasl.username": settings.KAFKA_SASL_USERNAME,
                "sasl.password": settings.KAFKA_SASL_PASSWORD,
            })

        return config

    async def start(self):
        """Start consuming messages from Kafka."""
        try:
            config = self._build_config()
            self.consumer = Consumer(config)
            self.consumer.subscribe(self.topics)
            self.running = True

            logger.info(
                f"Kafka consumer started for topics {self.topics} with group {self.group_id}"
            )

            # Start consume loop in background
            self._consume_task = asyncio.create_task(self._consume_loop())

        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise

    async def _consume_loop(self):
        """Main consume loop running in background."""
        while self.running:
            try:
                # Poll with timeout (non-blocking)
                msg = await asyncio.to_thread(self.consumer.poll, timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition - not an error
                        continue
                    else:
                        logger.error(f"Kafka consumer error: {msg.error()}")
                        continue

                # Process message
                await self._process_message(msg)

            except Exception as e:
                logger.error(f"Error in consume loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Backoff on error

    async def _process_message(self, msg):
        """Process a single Kafka message.

        Args:
            msg: Kafka message object
        """
        try:
            # Deserialize message
            raw_value = msg.value().decode("utf-8")
            event_data = json.loads(raw_value)

            # Get event type
            event_type = event_data.get("event_type")
            if not event_type:
                logger.warning(f"Message missing event_type: {event_data}")
                return

            # Validate against schema
            try:
                schema_class = get_event_schema(event_type)
                validated_event = schema_class(**event_data)
            except (ValueError, ValidationError) as e:
                logger.warning(f"Event validation failed for {event_type}: {e}")
                # Continue processing with raw dict
                validated_event = event_data

            # Call handler
            await self.handle_message(
                topic=msg.topic(),
                event=validated_event,
                raw_data=event_data,
                key=msg.key().decode("utf-8") if msg.key() else None,
                partition=msg.partition(),
                offset=msg.offset(),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    @abstractmethod
    async def handle_message(
        self,
        topic: str,
        event: BaseKafkaEvent | Dict[str, Any],
        raw_data: Dict[str, Any],
        key: Optional[str],
        partition: int,
        offset: int,
    ):
        """Handle a consumed message.

        Must be implemented by subclasses.

        Args:
            topic: Kafka topic name
            event: Validated event object or raw dict
            raw_data: Raw event data dict
            key: Message key
            partition: Partition number
            offset: Message offset
        """
        pass

    async def stop(self):
        """Stop consuming messages and close consumer."""
        self.running = False

        if self._consume_task:
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass

        if self.consumer:
            self.consumer.close()
            logger.info(f"Kafka consumer stopped for topics {self.topics}")

    async def commit(self):
        """Manually commit current offsets."""
        if self.consumer and not self.auto_commit:
            await asyncio.to_thread(self.consumer.commit, asynchronous=False)


class EventHandlerConsumer(BaseKafkaConsumer):
    """Consumer that routes events to registered handlers by event type."""

    def __init__(self, topics: List[str], group_id: Optional[str] = None):
        super().__init__(topics, group_id)
        self.handlers: Dict[str, List[Callable]] = {}

    def register_handler(
        self, event_type: str, handler: Callable[[BaseKafkaEvent | Dict], Any]
    ):
        """Register a handler function for a specific event type.

        Args:
            event_type: Event type to handle
            handler: Async callable that accepts the event
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")

    async def handle_message(
        self,
        topic: str,
        event: BaseKafkaEvent | Dict[str, Any],
        raw_data: Dict[str, Any],
        key: Optional[str],
        partition: int,
        offset: int,
    ):
        """Route message to registered handlers based on event type."""
        event_type = raw_data.get("event_type")
        if not event_type:
            logger.warning("Message missing event_type field")
            return

        handlers = self.handlers.get(event_type, [])
        if not handlers:
            logger.debug(f"No handlers registered for event type: {event_type}")
            return

        # Call all registered handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    f"Error in handler for {event_type}: {e}",
                    exc_info=True,
                )
