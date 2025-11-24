"""
WebSocket-Kafka Bridge

Consumes events from Kafka topics and forwards them to WebSocket clients
"""

import logging
from typing import Optional

from sqlmodel import create_engine

from app.kafka import EventHandlerConsumer, KafkaTopics
from app.websocket.connection_manager import connection_manager
from app.websocket.handlers import (
    MessageHandler,
    StoryHandler,
    FlowHandler,
    ApprovalHandler,
    StatusHandler,
    TaskHandler,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSocketKafkaBridge:
    """
    Bridges Kafka events to WebSocket connections using modular handlers
    """

    def __init__(self):
        self.consumer: Optional[EventHandlerConsumer] = None
        self.running = False
        self.engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
        
        # Initialize handlers
        self.message_handler = MessageHandler(connection_manager, self.engine)
        self.story_handler = StoryHandler(connection_manager, self.engine)
        self.flow_handler = FlowHandler(connection_manager, self.engine)
        self.approval_handler = ApprovalHandler(connection_manager, self.engine)
        self.status_handler = StatusHandler(connection_manager, self.engine)
        self.task_handler = TaskHandler(connection_manager, self.engine)

    async def start(self):
        """Start the WebSocket-Kafka bridge consumer"""
        try:
            logger.info("Starting WebSocket-Kafka bridge...")

            # Create consumer subscribing to relevant topics
            self.consumer = EventHandlerConsumer(
                topics=[
                    KafkaTopics.AGENT_RESPONSES.value,
                    KafkaTopics.AGENT_ROUTING.value,
                    KafkaTopics.STORY_EVENTS.value,
                    KafkaTopics.FLOW_STATUS.value,
                    KafkaTopics.AGENT_STATUS.value,
                    KafkaTopics.AGENT_PROGRESS.value,
                    KafkaTopics.TOOL_CALLS.value,
                    KafkaTopics.APPROVAL_REQUESTS.value,
                    KafkaTopics.AGENT_TASKS.value,
                ],
                group_id="websocket_bridge_group",
            )

            # Register message handlers
            self.consumer.register_handler("agent.response.created", self.message_handler.handle_agent_response)
            self.consumer.register_handler("agent.routing.delegated", self.message_handler.handle_agent_routing)

            # Register story handlers
            self.consumer.register_handler("story.created", self.story_handler.handle_story_created)
            self.consumer.register_handler("story.updated", self.story_handler.handle_story_updated)
            self.consumer.register_handler("story.status.changed", self.story_handler.handle_story_status_changed)

            # Register flow handlers
            self.consumer.register_handler("flow.started", self.flow_handler.handle_flow_event)
            self.consumer.register_handler("flow.in_progress", self.flow_handler.handle_flow_event)
            self.consumer.register_handler("flow.completed", self.flow_handler.handle_flow_event)
            self.consumer.register_handler("flow.failed", self.flow_handler.handle_flow_event)

            # Register approval handler
            self.consumer.register_handler("approval.request.created", self.approval_handler.handle_approval_request)

            # Register status handlers
            self.consumer.register_handler("agent.idle", self.status_handler.handle_agent_status)
            self.consumer.register_handler("agent.thinking", self.status_handler.handle_agent_status)
            self.consumer.register_handler("agent.acting", self.status_handler.handle_agent_status)
            self.consumer.register_handler("agent.waiting", self.status_handler.handle_agent_status)
            self.consumer.register_handler("agent.error", self.status_handler.handle_agent_status)
            self.consumer.register_handler("agent.progress", self.status_handler.handle_agent_progress)
            self.consumer.register_handler("agent.tool_call", self.status_handler.handle_tool_call)

            # Register task handlers
            self.consumer.register_handler("agent.task.assigned", self.task_handler.handle_task_assigned)
            self.consumer.register_handler("agent.task.started", self.task_handler.handle_task_started)
            self.consumer.register_handler("agent.task.progress", self.task_handler.handle_task_progress)
            self.consumer.register_handler("agent.task.completed", self.task_handler.handle_task_completed)
            self.consumer.register_handler("agent.task.failed", self.task_handler.handle_task_failed)
            self.consumer.register_handler("agent.task.cancelled", self.task_handler.handle_task_cancelled)

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
            await self.consumer.stop()

        logger.info("WebSocket-Kafka bridge stopped")


# Global bridge instance
websocket_kafka_bridge = WebSocketKafkaBridge()
