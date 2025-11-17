"""
Kafka Consumer for CrewAI Event System

Implements pull-based task distribution system for agents
"""

import json
import logging
import asyncio
from typing import Callable, Any

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.core.config import settings
from app.crews.events.event_schemas import KafkaTopics

logger = logging.getLogger(__name__)


class KafkaEventConsumer:
    """
    Kafka consumer for receiving crew events

    Implements pull system where agents poll for tasks
    """

    def __init__(
        self,
        topics: list[str],
        group_id: str | None = None,
        auto_offset_reset: str = "latest"
    ):
        self.topics = topics
        self.group_id = group_id or settings.KAFKA_GROUP_ID
        self.auto_offset_reset = auto_offset_reset
        self.consumer: AIOKafkaConsumer | None = None
        self._running = False
        self._handlers: dict[str, list[Callable]] = {}

    async def start(self):
        """Initialize and start Kafka consumer"""
        try:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=settings.KAFKA_ENABLE_AUTO_COMMIT,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                security_protocol=settings.KAFKA_SECURITY_PROTOCOL,
                sasl_mechanism=settings.KAFKA_SASL_MECHANISM,
                sasl_plain_username=settings.KAFKA_SASL_USERNAME,
                sasl_plain_password=settings.KAFKA_SASL_PASSWORD,
            )

            await self.consumer.start()
            self._running = True
            logger.info(
                f"Kafka consumer started for topics {self.topics} "
                f"(group={self.group_id})"
            )

        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise

    async def stop(self):
        """Stop and cleanup Kafka consumer"""
        self._running = False
        if self.consumer:
            try:
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer: {e}")

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for specific event type

        Args:
            event_type: Event type to handle (e.g., "task.created")
            handler: Async function to handle the event
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")

    async def consume(self):
        """
        Start consuming events and dispatch to handlers

        Runs indefinitely until stopped
        """
        if not self._running or not self.consumer:
            logger.error("Consumer not started")
            return

        logger.info("Starting event consumption...")

        try:
            async for message in self.consumer:
                try:
                    # Parse event data
                    event_data = message.value
                    event_type = event_data.get("event_type")

                    logger.debug(
                        f"Received event: {event_type} "
                        f"(topic={message.topic}, partition={message.partition}, "
                        f"offset={message.offset})"
                    )

                    # Dispatch to registered handlers
                    if event_type and event_type in self._handlers:
                        for handler in self._handlers[event_type]:
                            try:
                                await handler(event_data)
                            except Exception as e:
                                logger.error(
                                    f"Error in handler for {event_type}: {e}",
                                    exc_info=True
                                )
                    else:
                        logger.debug(f"No handler registered for event type: {event_type}")

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except KafkaError as e:
            logger.error(f"Kafka error during consumption: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during event consumption: {e}")
            raise
        finally:
            logger.info("Event consumption stopped")


class AgentTaskPuller:
    """
    Pull-based task distribution system for agents

    Each agent polls for tasks assigned to it
    """

    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self._running = False
        self.consumer: KafkaEventConsumer | None = None

    async def start(self):
        """Start pulling tasks from Kafka"""
        # Subscribe to task queue topic
        self.consumer = KafkaEventConsumer(
            topics=[KafkaTopics.TASK_QUEUE],
            group_id=f"agent_{self.agent_type}"
        )

        # Register handler for task events
        self.consumer.register_handler("task.created", self._handle_task_created)
        self.consumer.register_handler("task.assigned", self._handle_task_assigned)

        await self.consumer.start()
        self._running = True

        # Start consuming
        await self.consumer.consume()

    async def stop(self):
        """Stop pulling tasks"""
        self._running = False
        if self.consumer:
            await self.consumer.stop()

    async def _handle_task_created(self, event_data: dict[str, Any]):
        """Handle new task creation"""
        task_id = event_data.get("task_id")
        task_type = event_data.get("task_type")
        assigned_to = event_data.get("assigned_to")

        # Check if task is for this agent
        if assigned_to and assigned_to != self.agent_id:
            return  # Not for this agent

        logger.info(f"Agent {self.agent_id} received task {task_id} ({task_type})")

        # TODO: Implement task execution logic
        # This will be integrated with CrewAI agents

    async def _handle_task_assigned(self, event_data: dict[str, Any]):
        """Handle task assignment"""
        task_id = event_data.get("task_id")
        assigned_to = event_data.get("assigned_to")

        if assigned_to == self.agent_id:
            logger.info(f"Task {task_id} assigned to agent {self.agent_id}")
            # TODO: Fetch task details and execute


# Global consumers
_consumers: dict[str, KafkaEventConsumer] = {}


async def create_consumer(
    consumer_id: str,
    topics: list[str],
    group_id: str | None = None,
    auto_offset_reset: str = "latest"
) -> KafkaEventConsumer:
    """
    Create and start a Kafka consumer

    Args:
        consumer_id: Unique identifier for this consumer
        topics: List of topics to subscribe to
        group_id: Optional consumer group ID
        auto_offset_reset: Where to start consuming from (earliest or latest)

    Returns:
        KafkaEventConsumer instance
    """
    if consumer_id in _consumers:
        return _consumers[consumer_id]

    consumer = KafkaEventConsumer(topics, group_id, auto_offset_reset)
    await consumer.start()

    _consumers[consumer_id] = consumer
    return consumer


async def shutdown_all_consumers():
    """Shutdown all consumers"""
    for consumer_id, consumer in _consumers.items():
        logger.info(f"Shutting down consumer: {consumer_id}")
        await consumer.stop()

    _consumers.clear()
