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
        
        # Activity tracking now handled by activity_buffer
        # Removed: execution_activities, _activity_locks, _cleanup_task
        # ActivityBuffer handles all buffering and database writes

    def _has_active_connections(self, project_id: UUID) -> bool:
        """Check if project has active WebSocket connections.

        Used to skip processing non-critical events when no one is listening.

        Args:
            project_id: Project UUID to check

        Returns:
            True if project has at least one active connection
        """
        return connection_manager.get_project_connection_count(project_id) > 0

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

            # Register agent task handlers
            self.consumer.register_handler("agent.task.assigned", self.handle_task_assigned)
            self.consumer.register_handler("agent.task.started", self.handle_task_started)
            self.consumer.register_handler("agent.task.progress", self.handle_task_progress)
            self.consumer.register_handler("agent.task.completed", self.handle_task_completed)
            self.consumer.register_handler("agent.task.failed", self.handle_task_failed)
            self.consumer.register_handler("agent.task.cancelled", self.handle_task_cancelled)

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
                logger.warning(
                    f"Agent routing event missing project_id - cannot broadcast. "
                    f"From: {event_data.get('from_agent')}, "
                    f"To: {event_data.get('to_agent')}, "
                    f"Event ID: {event_data.get('event_id')}"
                )
                return

            # EARLY RETURN: Skip if no active connections (real-time delegation info)
            if not self._has_active_connections(project_id):
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
                logger.warning(
                    f"Story created event missing project_id - cannot broadcast. "
                    f"Story ID: {event_data.get('story_id')}, "
                    f"Event ID: {event_data.get('event_id')}"
                )
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
                logger.warning(
                    f"Story updated event missing project_id - cannot broadcast. "
                    f"Story ID: {event_data.get('story_id')}, "
                    f"Event ID: {event_data.get('event_id')}"
                )
                return

            ws_message = {
                "type": "kanban_update",
                "action": "story_updated",
                "story_id": str(event_data.get("story_id", "")),
                "updated_fields": event_data.get("updated_fields", {}),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

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
                logger.warning(
                    f"Story status change event missing project_id - cannot broadcast. "
                    f"Story ID: {event_data.get('story_id')}, "
                    f"Event ID: {event_data.get('event_id')}"
                )
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
                logger.warning(
                    f"Flow event missing project_id - cannot broadcast. "
                    f"Flow ID: {event_data.get('flow_id')}, "
                    f"Event Type: {event_data.get('event_type')}, "
                    f"Event ID: {event_data.get('event_id')}"
                )
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
                logger.warning(
                    f"Approval request event missing project_id - cannot broadcast. "
                    f"Request ID: {event_data.get('approval_request_id')}, "
                    f"Agent: {event_data.get('agent_name')}, "
                    f"Event ID: {event_data.get('event_id')}"
                )
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
                logger.warning(
                    f"Agent status event missing project_id - cannot broadcast. "
                    f"Agent: {event_data.get('agent_name')}, "
                    f"Status: {event_data.get('status')}, "
                    f"Event ID: {event_data.get('event_id')}"
                )
                return

            # EARLY RETURN: Skip if no active connections (real-time only event)
            if not self._has_active_connections(project_id):
                return

            # Extract status - handle both enum and string
            status = event_data.get("status", "")
            if hasattr(status, 'value'):
                # If it's an enum, get the value
                status = status.value
            elif not isinstance(status, str):
                # If it's not a string, convert to string
                status = str(status)

            ws_message = {
                "type": "agent_status",
                "agent_name": event_data.get("agent_name", ""),
                "status": status,
                "current_action": event_data.get("current_action"),
                "execution_id": str(event_data.get("execution_id", "")) if event_data.get("execution_id") else None,
                "timestamp": str(event_data.get("timestamp", "")),
            }

            if event_data.get("error_message"):
                ws_message["error_message"] = event_data["error_message"]

            await connection_manager.broadcast_to_project(ws_message, project_id)

            logger.debug(
                f"Broadcasted agent status to project {project_id}: "
                f"agent={ws_message['agent_name']}, status={ws_message['status']}"
            )

        except Exception as e:
            logger.error(f"Error handling agent status event: {e}", exc_info=True)

    async def handle_agent_progress(self, event):
        """Handle agent progress events using activity buffer.
        
        Now simplified with activity_buffer handling database writes.
        """
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                logger.warning(
                    f"Agent progress event missing project_id. "
                    f"Agent: {event_data.get('agent_name')}"
                )
                return

            # EARLY RETURN: Skip if no active connections (real-time only)
            if not self._has_active_connections(project_id):
                return

            execution_id = event_data.get("execution_id")
            if not execution_id:
                logger.warning(f"Agent progress event missing execution_id")
                return

            execution_id_str = str(execution_id)
            agent_name = event_data.get("agent_name", "Agent")
            step_number = event_data.get("step_number", 0)
            total_steps = event_data.get("total_steps", 0)
            step_description = event_data.get("step_description", "")
            step_status = event_data.get("status", "in_progress")

            # Update activity buffer (handles DB writes asynchronously)
            message_id = activity_buffer.update_activity(
                execution_id=execution_id_str,
                project_id=project_id,
                agent_name=agent_name,
                step_number=step_number,
                total_steps=total_steps,
                step_description=step_description,
                step_status=step_status
            )
            
            # Get activity data from buffer for WebSocket broadcast
            activity_data_obj = activity_buffer.get_activity(execution_id_str)
            
            if not activity_data_obj:
                logger.warning(f"Activity not found in buffer: {execution_id_str}")
                return
            
            # Build WebSocket message from buffered data
            is_new = len(activity_data_obj.steps) == 1
            
            activity_data = {
                "message_type": "activity",
                "data": {
                    "execution_id": execution_id_str,
                    "agent_name": agent_name,
                    "total_steps": total_steps,
                    "current_step": step_number,
                    "steps": activity_data_obj.steps,
                    "status": activity_data_obj.status,
                    "started_at": activity_data_obj.started_at.isoformat() if activity_data_obj.started_at else None,
                    "completed_at": activity_data_obj.completed_at.isoformat() if activity_data_obj.completed_at else None
                }
            }
            
            ws_message = {
                "type": "activity_update",
                "message_id": str(activity_data_obj.message_id) if activity_data_obj.message_id else "pending",
                "is_new": is_new,
                "structured_data": activity_data,
                "content": f"{agent_name} {'đã hoàn thành' if activity_data_obj.is_completed else 'đang thực thi...'}",
                "updated_at": activity_data_obj.last_update.isoformat(),
                "agent_name": agent_name,
            }
            
            if is_new:
                ws_message["created_at"] = activity_data_obj.started_at.isoformat() if activity_data_obj.started_at else None

            # Broadcast to WebSocket immediately (real-time feedback)
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
                logger.warning(
                    f"Tool call event missing project_id - cannot broadcast. "
                    f"Agent: {event_data.get('agent_name')}, "
                    f"Tool: {event_data.get('tool_name')}, "
                    f"Event ID: {event_data.get('event_id')}"
                )
                return

            # EARLY RETURN: Skip if no active connections (real-time debugging info)
            if not self._has_active_connections(project_id):
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

    async def handle_task_assigned(self, event):
        """Handle agent task assigned events"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                logger.warning(
                    f"Task assigned event missing project_id - cannot broadcast. "
                    f"Task ID: {event_data.get('task_id')}, "
                    f"Agent: {event_data.get('agent_name')}"
                )
                return

            ws_message = {
                "type": "task_assigned",
                "task_id": str(event_data.get("task_id", "")),
                "task_type": event_data.get("task_type", ""),
                "agent_id": str(event_data.get("agent_id", "")),
                "agent_name": event_data.get("agent_name", ""),
                "assigned_by": event_data.get("assigned_by", ""),
                "title": event_data.get("title", ""),
                "description": event_data.get("description"),
                "priority": event_data.get("priority", "medium"),
                "story_id": str(event_data.get("story_id")) if event_data.get("story_id") else None,
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

        except Exception as e:
            logger.error(f"Error handling task assigned event: {e}", exc_info=True)

    async def handle_task_started(self, event):
        """Handle agent task started events"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                logger.warning(f"Task started event missing project_id")
                return

            # EARLY RETURN: Skip if no active connections (real-time notification only)
            if not self._has_active_connections(project_id):
                return

            ws_message = {
                "type": "task_started",
                "task_id": str(event_data.get("task_id", "")),
                "agent_id": str(event_data.get("agent_id", "")),
                "agent_name": event_data.get("agent_name", ""),
                "execution_id": str(event_data.get("execution_id", "")),
                "started_at": str(event_data.get("started_at", "")),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

        except Exception as e:
            logger.error(f"Error handling task started event: {e}", exc_info=True)

    async def handle_task_progress(self, event):
        """Handle agent task progress events"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                logger.warning(f"Task progress event missing project_id")
                return

            # EARLY RETURN: Skip if no active connections (real-time progress only)
            if not self._has_active_connections(project_id):
                return

            ws_message = {
                "type": "task_progress",
                "task_id": str(event_data.get("task_id", "")),
                "agent_id": str(event_data.get("agent_id", "")),
                "agent_name": event_data.get("agent_name", ""),
                "execution_id": str(event_data.get("execution_id", "")),
                "progress_percentage": event_data.get("progress_percentage", 0),
                "current_step": event_data.get("current_step", ""),
                "steps_completed": event_data.get("steps_completed", 0),
                "total_steps": event_data.get("total_steps", 0),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            if event_data.get("estimated_completion"):
                ws_message["estimated_completion"] = str(event_data["estimated_completion"])

            await connection_manager.broadcast_to_project(ws_message, project_id)

        except Exception as e:
            logger.error(f"Error handling task progress event: {e}", exc_info=True)

    async def handle_task_completed(self, event):
        """Handle agent task completed events"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                logger.warning(f"Task completed event missing project_id")
                return

            ws_message = {
                "type": "task_completed",
                "task_id": str(event_data.get("task_id", "")),
                "agent_id": str(event_data.get("agent_id", "")),
                "agent_name": event_data.get("agent_name", ""),
                "execution_id": str(event_data.get("execution_id", "")),
                "completed_at": str(event_data.get("completed_at", "")),
                "duration_seconds": event_data.get("duration_seconds", 0),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            if event_data.get("result"):
                ws_message["result"] = event_data["result"]

            if event_data.get("artifacts"):
                ws_message["artifacts"] = event_data["artifacts"]

            await connection_manager.broadcast_to_project(ws_message, project_id)

        except Exception as e:
            logger.error(f"Error handling task completed event: {e}", exc_info=True)

    async def handle_task_failed(self, event):
        """Handle agent task failed events"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                logger.warning(f"Task failed event missing project_id")
                return

            ws_message = {
                "type": "task_failed",
                "task_id": str(event_data.get("task_id", "")),
                "agent_id": str(event_data.get("agent_id", "")),
                "agent_name": event_data.get("agent_name", ""),
                "execution_id": str(event_data.get("execution_id", "")),
                "failed_at": str(event_data.get("failed_at", "")),
                "error_message": event_data.get("error_message", ""),
                "error_type": event_data.get("error_type"),
                "retry_count": event_data.get("retry_count", 0),
                "can_retry": event_data.get("can_retry", True),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)
            logger.error(f"Forwarded task failed event to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling task failed event: {e}", exc_info=True)

    async def handle_task_cancelled(self, event):
        """Handle agent task cancelled events"""
        try:
            if hasattr(event, 'model_dump'):
                event_data = event.model_dump()
            else:
                event_data = event

            project_id = _to_uuid(event_data.get("project_id"))
            if not project_id:
                logger.warning(f"Task cancelled event missing project_id")
                return

            ws_message = {
                "type": "task_cancelled",
                "task_id": str(event_data.get("task_id", "")),
                "agent_id": str(event_data.get("agent_id", "")),
                "agent_name": event_data.get("agent_name", ""),
                "cancelled_by": event_data.get("cancelled_by", ""),
                "cancelled_at": str(event_data.get("cancelled_at", "")),
                "reason": event_data.get("reason"),
                "timestamp": str(event_data.get("timestamp", "")),
            }

            await connection_manager.broadcast_to_project(ws_message, project_id)

        except Exception as e:
            logger.error(f"Error handling task cancelled event: {e}", exc_info=True)


# Global bridge instance
websocket_kafka_bridge = WebSocketKafkaBridge()
