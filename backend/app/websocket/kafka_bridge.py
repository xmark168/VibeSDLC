"""
WebSocket-Kafka Bridge

Consumes events from Kafka topics and forwards them to WebSocket clients
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlmodel import Session, create_engine

from app.kafka import EventHandlerConsumer, KafkaTopics
from app.websocket.connection_manager import connection_manager
from app.core.config import settings
from app.models import Message as MessageModel, AuthorType

logger = logging.getLogger(__name__)


def _to_uuid(value) -> UUID | None:
    """Convert value to UUID, handling both string and UUID object."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(value)


class WebSocketKafkaBridge:
    """
    Bridges Kafka events to WebSocket connections

    Subscribes to multiple Kafka topics and forwards relevant events
    to connected WebSocket clients based on project_id
    """

    def __init__(self):
        self.consumer: Optional[EventHandlerConsumer] = None
        self.running = False
        self.engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

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
                    KafkaTopics.APPROVAL_REQUESTS.value,
                ],
                group_id="websocket_bridge_group",
            )

            # Register event handlers
            self.consumer.register_handler("agent.response.created", self.handle_agent_response)
            self.consumer.register_handler("agent.routing.delegated", self.handle_agent_routing)
            self.consumer.register_handler("story.created", self.handle_story_created)
            self.consumer.register_handler("story.updated", self.handle_story_updated)
            self.consumer.register_handler("story.status.changed", self.handle_story_status_changed)
            self.consumer.register_handler("flow.started", self.handle_flow_event)
            self.consumer.register_handler("flow.in_progress", self.handle_flow_event)
            self.consumer.register_handler("flow.completed", self.handle_flow_event)
            self.consumer.register_handler("flow.failed", self.handle_flow_event)
            self.consumer.register_handler("approval.request.created", self.handle_approval_request)

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
        if self.consumer:
            await self.consumer.stop()
        logger.info("WebSocket-Kafka bridge stopped")

    async def handle_agent_response(self, event):
        """
        Handle agent response events and forward to WebSocket clients

        Args:
            event: AgentResponseEvent instance or dict
        """
        try:
            # Handle both dict and Pydantic model
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                logger.warning("Agent response event missing project_id")
                return

            # Save message to database
            message_id = None
            content = event_data.get("content", "")
            structured_data = event_data.get("structured_data")

            with Session(self.engine) as db_session:
                db_message = MessageModel(
                    project_id=project_id,
                    user_id=None,
                    agent_id=None,
                    content=content,
                    author_type=AuthorType.AGENT,
                    message_type=structured_data.get("message_type", "text") if structured_data else "text",
                    structured_data=structured_data.get("data") if structured_data and "data" in structured_data else None,
                    metadata=structured_data if structured_data else None,
                )
                db_session.add(db_message)
                db_session.commit()
                db_session.refresh(db_message)
                message_id = db_message.id

            logger.info(f"Saved agent response to database: {message_id}")

            # Format message for WebSocket
            # Use timezone-aware datetime so JavaScript parses it correctly
            ws_message = {
                "type": "agent_message",
                "agent_name": event_data.get("agent_name", ""),
                "agent_type": event_data.get("agent_type", ""),
                "content": content,
                "message_id": str(message_id),
                "project_id": str(project_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "requires_approval": event_data.get("requires_approval", False),
            }

            # Only include structured_data if it's actual preview data (has message_type)
            # This prevents plain text messages from being displayed as preview cards
            if structured_data and structured_data.get("message_type"):
                ws_message["structured_data"] = structured_data

            if event_data.get("approval_request_id"):
                ws_message["approval_request_id"] = str(event_data["approval_request_id"])

            # Broadcast to all clients in the project
            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.info(f"Forwarded agent response to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling agent response event: {e}", exc_info=True)

    async def handle_agent_routing(self, event):
        """Handle agent routing events (when TeamLeader delegates to specialist)"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                return

            ws_message = {
                "type": "routing",
                "from_agent": event_data.get("from_agent", ""),
                "to_agent": event_data.get("to_agent", ""),
                "reason": event_data.get("delegation_reason", ""),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded routing decision to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling routing event: {e}", exc_info=True)

    async def handle_story_created(self, event):
        """Handle story created events"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                return

            ws_message = {
                "type": "kanban_update",
                "action": "story_created",
                "story_id": str(event_data.get("story_id", "")),
                "title": event_data.get("title", ""),
                "status": event_data.get("status", ""),
                "story_type": event_data.get("story_type", ""),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded story created event to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling story created event: {e}", exc_info=True)

    async def handle_story_updated(self, event):
        """Handle story updated events"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                return

            ws_message = {
                "type": "kanban_update",
                "action": "story_updated",
                "story_id": str(event_data.get("story_id", "")),
                "updated_fields": event_data.get("updated_fields", {}),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded story updated event to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling story updated event: {e}", exc_info=True)

    async def handle_story_status_changed(self, event):
        """Handle story status change events"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                return

            ws_message = {
                "type": "kanban_update",
                "action": "story_status_changed",
                "story_id": str(event_data.get("story_id", "")),
                "old_status": event_data.get("old_status", ""),
                "new_status": event_data.get("new_status", ""),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded story status change to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling story status change event: {e}", exc_info=True)

    async def handle_flow_event(self, event):
        """Handle flow execution events (development flow progress)"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                return

            event_type = event_data.get("event_type", "")

            ws_message = {
                "type": "scrum_master_step",
                "event_type": event_type,
                "flow_id": str(event_data.get("flow_id", "")),
                "flow_type": event_data.get("flow_type", ""),
                "status": event_data.get("status", ""),
                "current_step": event_data.get("current_step"),
                "total_steps": event_data.get("total_steps"),
                "completed_steps": event_data.get("completed_steps"),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            # Add error message if failed
            if event_data.get("error_message"):
                ws_message["error_message"] = event_data["error_message"]

            # Add result if completed
            if event_data.get("result"):
                ws_message["result"] = event_data["result"]

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded flow event to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling flow event: {e}", exc_info=True)

    async def handle_approval_request(self, event):
        """Handle approval request events (human-in-the-loop)"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                return

            ws_message = {
                "type": "approval_request",
                "approval_request_id": str(event_data.get("approval_request_id", "")),
                "request_type": event_data.get("request_type", ""),
                "agent_name": event_data.get("agent_name", ""),
                "proposed_data": event_data.get("proposed_data", {}),
                "preview_data": event_data.get("preview_data", {}),
                "explanation": event_data.get("explanation", ""),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.info(f"Forwarded approval request to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling approval request event: {e}", exc_info=True)


# Global bridge instance
websocket_kafka_bridge = WebSocketKafkaBridge()
