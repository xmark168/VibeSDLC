"""Kafka consumer pattern for agents.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
from uuid import UUID

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentConsumer:
    """
    Kafka consumer for agent message processing.
    """

    def __init__(
        self,
        agent_id: UUID,
        agent_name: str,
        topics: list[str],
        group_id: str,
        message_handler: Callable,
    ):
        """Initialize agent consumer
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.topics = topics
        self.group_id = group_id
        self.message_handler = message_handler

        self.consumer: Optional[AIOKafkaConsumer] = None
        self._consumer_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Statistics
        self.total_messages = 0
        self.processed_messages = 0
        self.failed_messages = 0

        logger.info(f"AgentConsumer created for {agent_name} (ID: {agent_id})")

    async def start(self) -> bool:
        """Start consuming messages.

        Returns:
            True if started successfully
        """
        try:
            # Create consumer
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self.group_id,
                auto_offset_reset="latest",
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )

            # Start consumer
            await self.consumer.start()

            # Start consumption loop
            self._consumer_task = asyncio.create_task(self._consume_loop())

            logger.info(f"Consumer for {self.agent_name} started on topics: {self.topics}")
            return True

        except Exception as e:
            logger.error(f"Failed to start consumer for {self.agent_name}: {e}", exc_info=True)
            return False

    async def stop(self) -> bool:
        """Stop consuming messages.

        Returns:
            True if stopped successfully
        """
        try:
            self._shutdown_event.set()

            # Stop consumer task
            if self._consumer_task:
                self._consumer_task.cancel()
                try:
                    await self._consumer_task
                except asyncio.CancelledError:
                    pass

            # Stop consumer
            if self.consumer:
                await self.consumer.stop()

            logger.info(f"Consumer for {self.agent_name} stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop consumer for {self.agent_name}: {e}", exc_info=True)
            return False

    async def _consume_loop(self) -> None:
        """Main consumption loop."""
        while not self._shutdown_event.is_set():
            try:
                if not self.consumer:
                    logger.error(f"Consumer not initialized for {self.agent_name}")
                    break
                async for message in self.consumer:
                    if self._shutdown_event.is_set():
                        break

                    self.total_messages += 1
                    await self._process_message(message)

            except asyncio.CancelledError:
                break
            except KafkaError as e:
                logger.error(f"Kafka error in consumer for {self.agent_name}: {e}")
                await asyncio.sleep(5)  
            except Exception as e:
                logger.error(f"Error in consumer loop for {self.agent_name}: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_message(self, message) -> None:
        """Process a single message.

        Args:
            message: Kafka message
        """
        try:
            logger.debug(f"Processing message for {self.agent_name}: {message.topic}/{message.partition}/{message.offset}")

            # Extract payload
            payload = message.value

            # Call handler
            await self.message_handler(payload)

            self.processed_messages += 1

        except Exception as e:
            logger.error(f"Error processing message for {self.agent_name}: {e}", exc_info=True)
            self.failed_messages += 1

            # Could publish to DLQ here
            await self._handle_failed_message(message, e)

    async def _handle_failed_message(self, message, error: Exception) -> None:
        """Handle failed message processing.

        Args:
            message: Failed message
            error: Exception that occurred
        """
        # Log error
        logger.error(f"Failed to process message: {error}")

        # Could implement:
        # - Dead letter queue
        # - Retry logic
        # - Alert generation
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "agent_id": str(self.agent_id),
            "agent_name": self.agent_name,
            "topics": self.topics,
            "group_id": self.group_id,
            "total_messages": self.total_messages,
            "processed_messages": self.processed_messages,
            "failed_messages": self.failed_messages,
            "success_rate": self.processed_messages / self.total_messages if self.total_messages > 0 else 0,
        }
