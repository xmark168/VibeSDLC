"""
Kafka consumer registry for managing multiple consumers.
"""

import asyncio
import logging
from typing import Dict, Optional

from app.kafka.consumer import BaseKafkaConsumer

logger = logging.getLogger(__name__)


class ConsumerRegistry:
    """Registry for managing multiple Kafka consumers."""

    def __init__(self):
        """Initialize consumer registry."""
        self.consumers: Dict[str, BaseKafkaConsumer] = {}
        self._started = False

    def register(self, name: str, consumer: BaseKafkaConsumer):
        """
        Register a consumer.
        """
        if name in self.consumers:
            logger.warning(f"Consumer {name} already registered, replacing...")
        self.consumers[name] = consumer
        logger.info(f"Registered consumer: {name}")

    async def start_all(self):
        """Start all registered consumers."""
        if self._started:
            logger.warning("Consumers already started")
            return

        logger.info(f"Starting {len(self.consumers)} Kafka consumers...")

        tasks = []
        for name, consumer in self.consumers.items():
            try:
                task = asyncio.create_task(consumer.start())
                tasks.append(task)
                logger.info(f"Starting consumer: {name}")
            except Exception as e:
                logger.error(f"Failed to start consumer {name}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._started = True
        logger.info("All Kafka consumers started")

    async def stop_all(self):
        """Stop all registered consumers."""
        if not self._started:
            return

        logger.info(f"Stopping {len(self.consumers)} Kafka consumers...")

        tasks = []
        for name, consumer in self.consumers.items():
            try:
                task = asyncio.create_task(consumer.stop())
                tasks.append(task)
                logger.info(f"Stopping consumer: {name}")
            except Exception as e:
                logger.error(f"Failed to stop consumer {name}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._started = False
        logger.info("All Kafka consumers stopped")

    def get_consumer(self, name: str) -> Optional[BaseKafkaConsumer]:
        """Get a consumer by name.

        Args:
            name: Consumer name

        Returns:
            Consumer instance or None if not found
        """
        return self.consumers.get(name)


# GLOBAL REGISTRY INSTANCE
_registry: Optional[ConsumerRegistry] = None


def get_consumer_registry() -> ConsumerRegistry:
    """Get the global consumer registry instance.

    Returns:
        ConsumerRegistry singleton
    """
    global _registry
    if _registry is None:
        _registry = ConsumerRegistry()
    return _registry


def setup_consumers(registry: ConsumerRegistry):
    """Setup all application consumers.

    """
    # Story events are handled by StoryEventRouter in router.py
    # No additional consumers needed here

    logger.info("Consumer setup completed")


async def start_all_consumers():
    """Start all registered consumers.

    """
    registry = get_consumer_registry()
    setup_consumers(registry)
    await registry.start_all()


async def shutdown_all_consumers():
    """Shutdown all registered consumers.

    """
    registry = get_consumer_registry()
    await registry.stop_all()
