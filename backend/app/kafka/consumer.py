"""Kafka Consumer service for VibeSDLC"""

import json
import logging
import asyncio
from typing import Callable, Optional, Dict, Any
from confluent_kafka import Consumer, KafkaException, KafkaError
from app.kafka.config import kafka_settings
from app.kafka.topics import KafkaTopics

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """Kafka Consumer Service for subscribing to topics"""

    def __init__(self, group_id: Optional[str] = None):
        self.group_id = group_id or kafka_settings.KAFKA_CONSUMER_GROUP_ID
        self.consumer: Optional[Consumer] = None
        self.running = False
        self.message_handlers: Dict[str, Callable] = {}

    def initialize(self, topics: list[KafkaTopics]):
        """Initialize Kafka consumer"""
        if not kafka_settings.KAFKA_ENABLED:
            logger.info("Kafka is disabled. Skipping consumer initialization.")
            return

        try:
            # Consumer configuration
            consumer_config = {
                'bootstrap.servers': kafka_settings.KAFKA_BOOTSTRAP_SERVERS,
                'group.id': self.group_id,
                'auto.offset.reset': kafka_settings.KAFKA_CONSUMER_AUTO_OFFSET_RESET,
                'enable.auto.commit': kafka_settings.KAFKA_CONSUMER_ENABLE_AUTO_COMMIT,
                'auto.commit.interval.ms': kafka_settings.KAFKA_CONSUMER_AUTO_COMMIT_INTERVAL_MS,
            }

            self.consumer = Consumer(consumer_config)

            # Subscribe to topics
            topic_names = [topic.value for topic in topics]
            self.consumer.subscribe(topic_names)

            logger.info(f"Kafka consumer initialized for topics: {topic_names}")

        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise

    def register_handler(self, topic: KafkaTopics, handler: Callable):
        """Register a message handler for a specific topic"""
        self.message_handlers[topic.value] = handler
        logger.info(f"Registered handler for topic: {topic.value}")

    async def start_consuming(self):
        """Start consuming messages (async)"""
        if not self.consumer:
            logger.warning("Consumer not initialized")
            return

        self.running = True
        logger.info("Starting Kafka consumer...")

        try:
            while self.running:
                # Poll for messages (non-blocking)
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    # No message, continue
                    await asyncio.sleep(0.1)
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, not an error
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue

                # Process message
                await self._process_message(msg)

        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        finally:
            self.stop()

    async def _process_message(self, msg):
        """Process a received message"""
        try:
            # Decode message
            topic = msg.topic()
            key = msg.key().decode('utf-8') if msg.key() else None
            value = json.loads(msg.value().decode('utf-8'))

            logger.debug(f"Received message from {topic}: key={key}")

            # Call registered handler
            handler = self.message_handlers.get(topic)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    await handler(value)
                else:
                    handler(value)
            else:
                logger.warning(f"No handler registered for topic: {topic}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def stop(self):
        """Stop consuming messages"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")


# Global consumer instances
agent_task_consumer = KafkaConsumerService(group_id="vibesdlc-agent-consumers")
story_event_consumer = KafkaConsumerService(group_id="vibesdlc-story-consumers")
