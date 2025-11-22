"""
WebSocket-Kafka Bridge

Consumes events from Kafka topics and forwards them to WebSocket clients
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
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
    """

    def __init__(self):
        self.consumer: Optional[EventHandlerConsumer] = None
        self.running = False
        self.engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
        # Track execution_id -> message_id mapping for activity updates
        self.execution_activities: Dict[str, UUID] = {}  # execution_id (str) -> message_id (UUID)

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

            # Register agent status handlers
            self.consumer.register_handler("agent.idle", self.handle_agent_status)
            self.consumer.register_handler("agent.thinking", self.handle_agent_status)
            self.consumer.register_handler("agent.acting", self.handle_agent_status)
            self.consumer.register_handler("agent.waiting", self.handle_agent_status)
            self.consumer.register_handler("agent.error", self.handle_agent_status)

            # Register agent progress and tool call handlers
            self.consumer.register_handler("agent.progress", self.handle_agent_progress)
            self.consumer.register_handler("agent.tool_call", self.handle_tool_call)

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
            agent_name = event_data.get("agent_name", "")

            # Build metadata with agent_name so it persists in database
            metadata = {"agent_name": agent_name} if agent_name else {}
            if structured_data:
                metadata.update(structured_data)

            with Session(self.engine) as db_session:
                db_message = MessageModel(
                    project_id=project_id,
                    user_id=None,
                    agent_id=None,
                    content=content,
                    author_type=AuthorType.AGENT,
                    message_type=structured_data.get("message_type", "text") if structured_data else "text",
                    structured_data=structured_data.get("data") if structured_data and "data" in structured_data else None,
                    message_metadata=metadata if metadata else None,
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
                "context": event_data.get("context", {}),  # Include full context for delegation details
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

    async def handle_agent_status(self, event):
        """Handle agent status events (thinking, acting, idle, etc.)"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                return

            ws_message = {
                "type": "agent_status",
                "agent_name": event_data.get("agent_name", ""),
                "status": event_data.get("status", ""),
                "current_action": event_data.get("current_action"),
                "execution_id": str(event_data.get("execution_id", "")) if event_data.get("execution_id") else None,
                "timestamp": str(event_data.get("timestamp", "")),
            }

            if event_data.get("error_message"):
                ws_message["error_message"] = event_data["error_message"]

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(f"Forwarded agent status to project {project_id}: {ws_message['status']}")

        except Exception as e:
            logger.error(f"Error handling agent status event: {e}", exc_info=True)

    async def handle_agent_progress(self, event):
        """Handle agent progress events (step-by-step execution tracking)

        Creates/updates activity messages in the database to persist progress.
        """
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                return

            execution_id = event_data.get("execution_id")
            if not execution_id:
                logger.warning("Agent progress event missing execution_id")
                return

            execution_id_str = str(execution_id)
            agent_name = event_data.get("agent_name", "Agent")
            step_number = event_data.get("step_number", 0)
            total_steps = event_data.get("total_steps", 0)
            step_description = event_data.get("step_description", "")
            step_status = event_data.get("status", "in_progress")

            # Check if activity message exists for this execution
            message_id = self.execution_activities.get(execution_id_str)

            with Session(self.engine) as db_session:
                if not message_id:
                    # FIRST progress event - CREATE new activity message
                    message_id = uuid4()

                    activity_data = {
                        "message_type": "activity",
                        "data": {
                            "execution_id": execution_id_str,
                            "agent_name": agent_name,
                            "total_steps": total_steps,
                            "current_step": step_number,
                            "steps": [
                                {
                                    "step": step_number,
                                    "description": step_description,
                                    "status": step_status,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                            ],
                            "status": "in_progress",
                            "started_at": datetime.now(timezone.utc).isoformat(),
                            "completed_at": None
                        }
                    }

                    db_message = MessageModel(
                        id=message_id,
                        project_id=project_id,
                        user_id=None,
                        agent_id=None,
                        content=f"{agent_name} đang thực thi...",
                        author_type=AuthorType.AGENT,
                        message_type="activity",
                        structured_data=activity_data,
                        message_metadata={"agent_name": agent_name}
                    )
                    db_session.add(db_message)
                    db_session.commit()
                    db_session.refresh(db_message)

                    # Track mapping
                    self.execution_activities[execution_id_str] = message_id

                    logger.info(f"Created activity message {message_id} for execution {execution_id_str}")

                    # Send as NEW message to WebSocket
                    ws_message = {
                        "type": "agent_message",
                        "data": {
                            "id": str(message_id),
                            "project_id": str(project_id),
                            "author_type": "agent",
                            "content": db_message.content,
                            "created_at": db_message.created_at.isoformat(),
                            "updated_at": db_message.updated_at.isoformat(),
                            "agent_name": agent_name,
                            "message_type": "activity",
                            "structured_data": activity_data,
                            "message_metadata": {"agent_name": agent_name}
                        }
                    }

                else:
                    # UPDATE existing activity message
                    db_message = db_session.get(MessageModel, message_id)

                    if not db_message:
                        logger.warning(f"Activity message {message_id} not found in database")
                        # Clean up stale mapping
                        del self.execution_activities[execution_id_str]
                        return

                    # Get existing activity data
                    activity_data = db_message.structured_data or {}
                    if "data" not in activity_data:
                        activity_data["data"] = {}

                    data = activity_data["data"]

                    # Append new step to steps array
                    if "steps" not in data:
                        data["steps"] = []

                    data["steps"].append({
                        "step": step_number,
                        "description": step_description,
                        "status": step_status,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                    # Update current step
                    data["current_step"] = step_number

                    # If completed, mark as done and cleanup mapping
                    if step_status == "completed":
                        data["status"] = "completed"
                        data["completed_at"] = datetime.now(timezone.utc).isoformat()
                        db_message.content = f"{agent_name} đã hoàn thành"

                        # Clean up mapping
                        if execution_id_str in self.execution_activities:
                            del self.execution_activities[execution_id_str]

                        logger.info(f"Completed activity {message_id} for execution {execution_id_str}")

                    # Update message in database
                    db_message.structured_data = activity_data
                    db_message.updated_at = datetime.now(timezone.utc)
                    db_session.add(db_message)
                    db_session.commit()
                    db_session.refresh(db_message)

                    logger.debug(f"Updated activity message {message_id}: step {step_number}/{total_steps}")

                    # Send as UPDATE to WebSocket
                    ws_message = {
                        "type": "activity_update",
                        "message_id": str(message_id),
                        "structured_data": activity_data,
                        "updated_at": db_message.updated_at.isoformat(),
                        "content": db_message.content,
                    }

                # Broadcast to project
                await connection_manager.broadcast_to_project(ws_message, project_id)

        except Exception as e:
            logger.error(f"Error handling agent progress event: {e}", exc_info=True)

    async def handle_tool_call(self, event):
        """Handle tool call events (agent using tools/functions)"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                return

            ws_message = {
                "type": "tool_call",
                "agent_name": event_data.get("agent_name", ""),
                "agent_id": event_data.get("agent_id"),
                "execution_id": str(event_data.get("execution_id", "")) if event_data.get("execution_id") else None,
                "tool_name": event_data.get("tool_name", ""),
                "display_name": event_data.get("display_name", ""),
                "status": event_data.get("status", "started"),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            if event_data.get("parameters"):
                ws_message["parameters"] = event_data["parameters"]

            if event_data.get("result"):
                ws_message["result"] = event_data["result"]

            if event_data.get("error_message"):
                ws_message["error_message"] = event_data["error_message"]

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(
                f"Forwarded tool call to project {project_id}: "
                f"{event_data.get('agent_name')} using {event_data.get('tool_name')}"
            )

        except Exception as e:
            logger.error(f"Error handling tool call event: {e}", exc_info=True)


# Global bridge instance
websocket_kafka_bridge = WebSocketKafkaBridge()
