"""
WebSocket-Kafka Bridge

Consumes events from Kafka topics and forwards them to WebSocket clients
"""

import asyncio
import logging
from typing import Dict, Any
from uuid import UUID

from app.crews.events.kafka_consumer import create_consumer
from app.crews.events.event_schemas import KafkaTopics
from app.websocket.connection_manager import connection_manager

logger = logging.getLogger(__name__)


class WebSocketKafkaBridge:
    """
    Bridges Kafka events to WebSocket connections

    Subscribes to multiple Kafka topics and forwards relevant events
    to connected WebSocket clients based on project_id
    """

    def __init__(self):
        self.consumer = None
        self.running = False

    async def start(self):
        """Start the WebSocket-Kafka bridge consumer"""
        try:
            logger.info("Starting WebSocket-Kafka bridge...")

            # Create consumer subscribing to relevant topics
            self.consumer = await create_consumer(
                consumer_id="websocket_bridge",
                topics=[
                    KafkaTopics.AGENT_RESPONSES,
                    KafkaTopics.AGENT_ROUTING,
                    KafkaTopics.STORY_EVENTS,
                    KafkaTopics.FLOW_STATUS,
                    KafkaTopics.AGENT_STATUS,
                ],
                group_id="websocket_bridge_group",
                auto_offset_reset="latest"
            )

            # Register event handlers
            self.consumer.register_handler("agent.response", self.handle_agent_response)
            self.consumer.register_handler("agent.routing", self.handle_agent_routing)
            self.consumer.register_handler("story.created", self.handle_story_created)
            self.consumer.register_handler("story.updated", self.handle_story_updated)
            self.consumer.register_handler("story.status.changed", self.handle_story_status_changed)
            self.consumer.register_handler("flow.started", self.handle_flow_event)
            self.consumer.register_handler("flow.step.completed", self.handle_flow_event)
            self.consumer.register_handler("flow.completed", self.handle_flow_event)

            self.running = True
            logger.info("WebSocket-Kafka bridge started successfully")

            # Start consuming in background
            await self.consumer.consume()

        except Exception as e:
            logger.error(f"Error starting WebSocket-Kafka bridge: {e}")
            raise

    async def stop(self):
        """Stop the WebSocket-Kafka bridge consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("WebSocket-Kafka bridge stopped")

    async def handle_agent_response(self, event_data: Dict[str, Any]):
        """
        Handle agent response events and forward to WebSocket clients

        Event structure:
        {
            "response_id": UUID,
            "task_id": UUID,
            "agent_type": str,
            "project_id": UUID,
            "content": str,
            "structured_data": dict (optional),
            "metadata": dict (optional)
        }
        """
        try:
            project_id = UUID(event_data["project_id"])

            # Format message for WebSocket
            ws_message = {
                "type": "agent_message",
                "agent_type": event_data["agent_type"],
                "content": event_data["content"],
                "response_id": str(event_data["response_id"]),
                "task_id": str(event_data["task_id"]),
                "timestamp": event_data.get("timestamp", ""),
            }

            # Include structured data if present (for previews, etc.)
            if "structured_data" in event_data and event_data["structured_data"]:
                ws_message["structured_data"] = event_data["structured_data"]

            if "metadata" in event_data and event_data["metadata"]:
                ws_message["metadata"] = event_data["metadata"]

            # Broadcast to all clients in the project
            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded agent response to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling agent response event: {e}")

    async def handle_agent_routing(self, event_data: Dict[str, Any]):
        """
        Handle agent routing events (when router decides which agent to use)

        Event structure:
        {
            "message_id": UUID,
            "project_id": UUID,
            "routed_to": str,
            "routing_reason": str,
            "confidence": float
        }
        """
        try:
            project_id = UUID(event_data["project_id"])

            ws_message = {
                "type": "routing",
                "routed_to": event_data["routed_to"],
                "reason": event_data.get("routing_reason", ""),
                "confidence": event_data.get("confidence", 1.0),
                "timestamp": event_data.get("timestamp", ""),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded routing decision to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling routing event: {e}")

    async def handle_story_created(self, event_data: Dict[str, Any]):
        """Handle story created events"""
        try:
            project_id = UUID(event_data["project_id"])

            ws_message = {
                "type": "kanban_update",
                "action": "story_created",
                "story_id": str(event_data["story_id"]),
                "title": event_data.get("title", ""),
                "status": event_data.get("status", ""),
                "timestamp": event_data.get("timestamp", ""),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded story created event to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling story created event: {e}")

    async def handle_story_updated(self, event_data: Dict[str, Any]):
        """Handle story updated events"""
        try:
            project_id = UUID(event_data["project_id"])

            ws_message = {
                "type": "kanban_update",
                "action": "story_updated",
                "story_id": str(event_data["story_id"]),
                "changes": event_data.get("changes", {}),
                "timestamp": event_data.get("timestamp", ""),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded story updated event to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling story updated event: {e}")

    async def handle_story_status_changed(self, event_data: Dict[str, Any]):
        """Handle story status change events"""
        try:
            project_id = UUID(event_data["project_id"])

            ws_message = {
                "type": "kanban_update",
                "action": "story_status_changed",
                "story_id": str(event_data["story_id"]),
                "old_status": event_data.get("old_status", ""),
                "new_status": event_data.get("new_status", ""),
                "timestamp": event_data.get("timestamp", ""),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded story status change to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling story status change event: {e}")

    async def handle_flow_event(self, event_data: Dict[str, Any]):
        """Handle flow execution events (development flow progress)"""
        try:
            project_id = UUID(event_data["project_id"])
            event_type = event_data.get("event_type", "")

            ws_message = {
                "type": "scrum_master_step",
                "event_type": event_type,
                "flow_id": event_data.get("flow_id", ""),
                "timestamp": event_data.get("timestamp", ""),
            }

            # Add specific fields based on event type
            if event_type == "flow.started":
                ws_message["flow_type"] = event_data.get("flow_type", "")
            elif event_type == "flow.step.completed":
                ws_message["step_name"] = event_data.get("step_name", "")
                ws_message["next_step"] = event_data.get("next_step", "")
            elif event_type == "flow.completed":
                ws_message["execution_time_ms"] = event_data.get("total_execution_time_ms", 0)

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded flow event to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling flow event: {e}")


# Global bridge instance
websocket_kafka_bridge = WebSocketKafkaBridge()
