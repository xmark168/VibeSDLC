"""
WebSocket-Kafka Bridge

Consumes events from Kafka topics and forwards them to WebSocket clients
"""

import asyncio
import logging
from typing import Optional

from sqlmodel import create_engine

from app.kafka import EventHandlerConsumer, KafkaTopics
from app.websocket.connection_manager import connection_manager
from app.websocket.handlers import (
    StoryHandler,
    FlowHandler,
    TaskHandler,
    AgentEventsHandler,
)
from app.core.config import settings, database_settings

logger = logging.getLogger(__name__)


class WebSocketKafkaBridge:
    """
    Bridges Kafka events to WebSocket connections using modular handlers
    """

    def __init__(self):
        self.consumer: Optional[EventHandlerConsumer] = None
        self.running = False
        self.engine = create_engine(str(database_settings.SQLALCHEMY_DATABASE_URI))
        
        # Initialize handlers
        # Agent events handler for all agent events
        self.agent_events_handler = AgentEventsHandler(connection_manager, self.engine)
        
        # Domain event handlers
        self.story_handler = StoryHandler(connection_manager, self.engine)
        self.flow_handler = FlowHandler(connection_manager, self.engine)
        self.task_handler = TaskHandler(connection_manager, self.engine)

    async def start(self):
        """Start the WebSocket-Kafka bridge consumer"""
        try:
            logger.info("Starting WebSocket-Kafka bridge...")

            # Create consumer subscribing to relevant topics
            # IMPORTANT: Use auto_offset_reset="latest" to skip backlog on restart
            # WebSocket is real-time only - old messages already in DB
            self.consumer = EventHandlerConsumer(
                topics=[
                    # Agent events (unified stream)
                    KafkaTopics.AGENT_EVENTS.value,
                    
                    # Domain events
                    KafkaTopics.DOMAIN_EVENTS.value,
                    KafkaTopics.STORY_EVENTS.value,
                    KafkaTopics.FLOW_STATUS.value,
                    
                    # Task management
                    KafkaTopics.AGENT_TASKS.value,
                ],
                group_id="websocket_bridge_group",
                auto_offset_reset="latest",  # Skip backlog, only consume new messages
            )

            # Register agent events handler for all agent events
            self.consumer.register_handler("agent.thinking", self.agent_events_handler.handle_agent_event)
            self.consumer.register_handler("agent.idle", self.agent_events_handler.handle_agent_event)
            self.consumer.register_handler("agent.waiting", self.agent_events_handler.handle_agent_event)
            self.consumer.register_handler("agent.error", self.agent_events_handler.handle_agent_event)
            self.consumer.register_handler("agent.tool_call", self.agent_events_handler.handle_agent_event)
            self.consumer.register_handler("agent.progress", self.agent_events_handler.handle_agent_event)
            self.consumer.register_handler("agent.response", self.agent_events_handler.handle_agent_event)
            self.consumer.register_handler("agent.completed", self.agent_events_handler.handle_agent_event)  # Finish signal
            self.consumer.register_handler("agent.delegation", self.agent_events_handler.handle_agent_event)
            self.consumer.register_handler("agent.question", self.agent_events_handler.handle_agent_event)

            # Register story handlers
            self.consumer.register_handler("story.created", self.story_handler.handle_story_created)
            self.consumer.register_handler("story.updated", self.story_handler.handle_story_updated)
            self.consumer.register_handler("story.status.changed", self.story_handler.handle_story_status_changed)
            self.consumer.register_handler("story.agent_state.changed", self.story_handler.handle_story_agent_state_changed)

            # Start consumer
            await self.consumer.start()

            self.running = True

            logger.info("WebSocket-Kafka bridge started successfully")

        except Exception as e:
            logger.error(f"Error starting WebSocket-Kafka bridge: {e}")
            raise

    async def stop(self):
        """Stop the WebSocket-Kafka bridge consumer"""
        self.running = False

        # Stop consumer
        if self.consumer:
            try:
                await self.consumer.stop()
            except (Exception, asyncio.CancelledError) as e:
                logger.error(f"Error stopping consumer: {e}")

        logger.info("WebSocket-Kafka bridge stopped")


# Global bridge instance
websocket_kafka_bridge = WebSocketKafkaBridge()
