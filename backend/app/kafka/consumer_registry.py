"""
Consumer Registry

Manages lifecycle of all Kafka consumers and WebSocket bridge
"""

import asyncio
import logging
from typing import List, Dict, Any

from app.websocket.kafka_bridge import websocket_kafka_bridge
from app.agents.router_agent import router_agent
from app.agents.story_assistant_consumer import story_assistant_consumer
from app.agents.insights_consumer import insights_agent_consumer

logger = logging.getLogger(__name__)


class ConsumerRegistry:
    """
    Centralized registry for all Kafka consumers

    Manages startup and shutdown of:
    - WebSocket-Kafka bridge
    - Router agent
    - Story assistant agent (BA)
    - Insights agent (Team Leader)
    - Developer agent (future)
    - Tester agent (future)
    """

    def __init__(self):
        self.consumers: List[Any] = []
        self.consumer_tasks: List[asyncio.Task] = []
        self.running = False

    async def start_all_consumers(self):
        """Start all consumers in background tasks"""
        try:
            logger.info("Starting all Kafka consumers...")

            # List of all consumers to start
            consumers_to_start = [
                ("WebSocket Bridge", websocket_kafka_bridge),
                ("Router Agent", router_agent),
                ("Story Assistant (BA)", story_assistant_consumer),
                ("Insights Agent (Leader)", insights_agent_consumer),
            ]

            # Start each consumer in a background task
            for name, consumer in consumers_to_start:
                try:
                    logger.info(f"Starting {name}...")
                    task = asyncio.create_task(
                        consumer.start(),
                        name=f"consumer_{name.lower().replace(' ', '_')}"
                    )
                    self.consumer_tasks.append(task)
                    self.consumers.append(consumer)
                    logger.info(f"✓ {name} started")
                except Exception as e:
                    logger.error(f"Failed to start {name}: {e}")
                    # Continue starting other consumers even if one fails

            self.running = True
            logger.info(f"✓ All consumers started ({len(self.consumers)} total)")

        except Exception as e:
            logger.error(f"Error starting consumers: {e}")
            # Try to clean up any started consumers
            await self.shutdown_all_consumers()
            raise

    async def shutdown_all_consumers(self):
        """Gracefully shutdown all consumers"""
        try:
            logger.info("Shutting down all consumers...")

            self.running = False

            # Stop all consumers
            for consumer in self.consumers:
                try:
                    if hasattr(consumer, 'stop'):
                        await consumer.stop()
                except Exception as e:
                    logger.error(f"Error stopping consumer: {e}")

            # Cancel all background tasks
            for task in self.consumer_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Error cancelling task: {e}")

            self.consumers.clear()
            self.consumer_tasks.clear()

            logger.info("✓ All consumers shut down")

        except Exception as e:
            logger.error(f"Error during consumer shutdown: {e}")

    def get_consumer_status(self) -> Dict[str, Any]:
        """Get status of all consumers"""
        return {
            "running": self.running,
            "consumer_count": len(self.consumers),
            "task_count": len(self.consumer_tasks),
            "tasks_status": [
                {
                    "name": task.get_name(),
                    "done": task.done(),
                    "cancelled": task.cancelled(),
                }
                for task in self.consumer_tasks
            ],
        }


# Global consumer registry instance
consumer_registry = ConsumerRegistry()


# Convenience functions for use in main.py
async def start_all_consumers():
    """Start all consumers (convenience function)"""
    await consumer_registry.start_all_consumers()


async def shutdown_all_consumers():
    """Shutdown all consumers (convenience function)"""
    await consumer_registry.shutdown_all_consumers()


def get_consumer_status():
    """Get consumer status (convenience function)"""
    return consumer_registry.get_consumer_status()
