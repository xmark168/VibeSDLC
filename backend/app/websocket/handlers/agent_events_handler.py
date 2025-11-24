"""
Agent Events Handler

Handles all agent events from the AGENT_EVENTS topic.
Routes events based on event_type field.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Session

from app.models import Message as MessageModel, AuthorType, MessageVisibility
from .base import BaseEventHandler
from app.websocket.activity_buffer import activity_buffer

logger = logging.getLogger(__name__)


class AgentEventsHandler(BaseEventHandler):
    """
    Single handler for all agent events from AGENT_EVENTS topic.
    
    Routes events based on event_type:
    - agent.response → Save to DB + broadcast
    - agent.thinking/idle/waiting/error → Broadcast status
    - agent.progress → Update activity buffer + broadcast
    - agent.tool_call → Broadcast tool usage
    - agent.delegation → Create delegation message
    - agent.approval_request → Broadcast approval request
    """
    
    async def handle_agent_event(self, event):
        """Route agent event based on type"""
        try:
            event_data = self._normalize_event(event)
            event_type = event_data.get("event_type", "")
            
            # Remove "agent." prefix to get event category
            event_category = event_type.replace("agent.", "")
            
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning(f"Agent event missing project_id: {event_type}")
                return
            
            # Check for active connections
            has_connections = self._has_active_connections(project_id)
            logger.info(
                f"[AGENT_EVENT] Received {event_type} for project {project_id} - "
                f"Active connections: {has_connections}"
            )
            
            # Skip if no active connections (real-time only)
            if not has_connections:
                logger.info(f"Skipping event {event_type} - no active connections for project {project_id}")
                return
            
            # Route to appropriate handler
            if event_category == "response":
                await self._handle_response(event_data, project_id)
            
            elif event_category in ["thinking", "idle", "waiting", "error"]:
                await self._handle_status(event_data, project_id)
            
            elif event_category == "progress":
                await self._handle_progress(event_data, project_id)
            
            elif event_category == "tool_call":
                await self._handle_tool_call(event_data, project_id)
            
            elif event_category == "delegation":
                await self._handle_delegation(event_data, project_id)
            
            elif event_category == "approval_request":
                await self._handle_approval_request(event_data, project_id)
            
            else:
                # Unknown event type - still broadcast (extensible!)
                logger.info(f"Unknown agent event type: {event_type}, broadcasting as generic")
                await self._broadcast_generic(event_data, project_id)
        
        except Exception as e:
            logger.error(f"Error handling agent event: {e}", exc_info=True)
    
    async def _handle_response(self, data, project_id):
        """Handle response events - save to DB and broadcast"""
        try:
            content = data.get("content", "")
            details = data.get("details", {})
            agent_name = data.get("agent_name", "")
            execution_id = data.get("execution_id")
            task_id = data.get("task_id")
            
            # Extract structured data from details
            message_type = details.get("message_type", "text")
            structured_data_payload = details.get("data")
            requires_approval = details.get("requires_approval", False)
            
            # Build metadata
            metadata = {"agent_name": agent_name}
            if task_id:
                metadata["task_id"] = str(task_id)
            if execution_id:
                metadata["execution_id"] = str(execution_id)
            
            # Save message to database
            with Session(self.engine) as db_session:
                db_message = MessageModel(
                    project_id=project_id,
                    user_id=None,
                    agent_id=None,
                    content=content,
                    author_type=AuthorType.AGENT,
                    visibility=MessageVisibility.USER_MESSAGE,  # Agent responses are user-facing messages
                    message_type=message_type,
                    structured_data=structured_data_payload,
                    message_metadata=metadata,
                )
                db_session.add(db_message)
                db_session.commit()
                db_session.refresh(db_message)
                message_id = db_message.id
            
            logger.info(
                f"Saved agent response: {message_id}, "
                f"type={message_type}, execution_id={execution_id}"
            )
            
            # Broadcast to WebSocket
            ws_message = {
                "type": "agent_message",
                "message_id": str(message_id),
                "agent_name": agent_name,
                "content": content,
                "structured_data": details,
                "requires_approval": requires_approval,
                "timestamp": self._get_timestamp(data),
            }
            
            await self._broadcast(project_id, ws_message)
        
        except Exception as e:
            logger.error(f"Error handling response event: {e}", exc_info=True)
    
    async def _handle_status(self, data, project_id):
        """Handle status events (thinking, idle, waiting, error)"""
        try:
            event_type = data.get("event_type", "").replace("agent.", "")
            
            ws_message = {
                "type": "agent_status",
                "agent_name": data.get("agent_name", ""),
                "status": event_type,
                "current_action": data.get("content"),
                "execution_id": str(data.get("execution_id", "")) if data.get("execution_id") else None,
                "timestamp": self._get_timestamp(data),
            }
            
            # Add error details if present
            details = data.get("details", {})
            if details.get("error_type"):
                ws_message["error_message"] = data.get("content")
                ws_message["error_type"] = details.get("error_type")
            
            await self._broadcast(project_id, ws_message)
        
        except Exception as e:
            logger.error(f"Error handling status event: {e}", exc_info=True)
    
    async def _handle_progress(self, data, project_id):
        """Handle progress events - use activity buffer"""
        try:
            execution_id = data.get("execution_id")
            
            if not execution_id:
                logger.warning("Progress event missing execution_id")
                return
            
            execution_id_str = str(execution_id)
            agent_name = data.get("agent_name", "Agent")
            content = data.get("content", "")
            details = data.get("details", {})
            
            # Extract agent_execution_id from metadata if available
            metadata = data.get("metadata", {})
            agent_execution_id = metadata.get("agent_execution_id")
            
            # Convert to UUID if present
            if agent_execution_id and isinstance(agent_execution_id, str):
                try:
                    from uuid import UUID
                    agent_execution_id = UUID(agent_execution_id)
                except:
                    agent_execution_id = None
            
            # Add event to activity buffer (no step numbers!)
            activity_buffer.add_event(
                execution_id=execution_id_str,
                project_id=project_id,
                agent_name=agent_name,
                event_description=content,
                event_details=details,
                agent_execution_id=agent_execution_id,
            )
            
            # Get activity data for broadcast
            activity_data_obj = activity_buffer.get_activity(execution_id_str)
            
            if not activity_data_obj:
                logger.warning(f"Activity not found in buffer: {execution_id_str}")
                return
            
            # Check if this is first event (new activity)
            is_new = len(activity_data_obj.events) == 1
            
            # Determine status
            milestone = details.get("milestone", "")
            if milestone == "completed" or "complete" in content.lower():
                status = "completed"
                activity_data_obj.status = "completed"
                activity_data_obj.completed_at = datetime.now(timezone.utc)
            elif milestone == "failed" or "error" in content.lower():
                status = "failed"
                activity_data_obj.status = "failed"
            else:
                status = "in_progress"
            
            # Build WebSocket message
            ws_message = {
                "type": "activity_update" if not is_new else "agent_progress",
                "message_id": str(activity_data_obj.message_id) if activity_data_obj.message_id else None,
                "execution_id": execution_id_str,
                "agent_name": agent_name,
                "content": content,
                "structured_data": {
                    "execution_id": execution_id_str,
                    "agent_name": agent_name,
                    "events": [
                        {
                            "description": evt["description"],
                            "details": evt.get("details", {}),
                            "timestamp": evt["timestamp"],
                        }
                        for evt in activity_data_obj.events
                    ],
                    "status": status,
                    "started_at": activity_data_obj.started_at.isoformat() if activity_data_obj.started_at else None,
                    "completed_at": activity_data_obj.completed_at.isoformat() if activity_data_obj.completed_at else None,
                },
                "timestamp": self._get_timestamp(data),
            }
            
            await self._broadcast(project_id, ws_message)
        
        except Exception as e:
            logger.error(f"Error handling progress event: {e}", exc_info=True)
    
    async def _handle_tool_call(self, data, project_id):
        """Handle tool call events"""
        try:
            details = data.get("details", {})
            
            ws_message = {
                "type": "tool_call",
                "agent_name": data.get("agent_name", ""),
                "tool_name": details.get("tool", ""),
                "display_name": data.get("content"),
                "status": details.get("status", "started"),
                "parameters": details.get("parameters"),
                "result": details.get("result"),
                "error_message": details.get("error"),
                "timestamp": self._get_timestamp(data),
            }
            
            await self._broadcast(project_id, ws_message)
        
        except Exception as e:
            logger.error(f"Error handling tool call event: {e}", exc_info=True)
    
    async def _handle_delegation(self, data, project_id):
        """Handle delegation events"""
        try:
            details = data.get("details", {})
            
            ws_message = {
                "type": "routing",
                "from_agent": data.get("agent_name", ""),
                "to_agent": details.get("to_agent", ""),
                "reason": details.get("reason", ""),
                "context": details.get("context", {}),
                "timestamp": self._get_timestamp(data),
            }
            
            await self._broadcast(project_id, ws_message)
        
        except Exception as e:
            logger.error(f"Error handling delegation event: {e}", exc_info=True)
    
    async def _handle_approval_request(self, data, project_id):
        """Handle approval request events"""
        try:
            details = data.get("details", {})
            
            ws_message = {
                "type": "approval_request",
                "approval_request_id": details.get("approval_request_id") or str(uuid4()),
                "agent_name": data.get("agent_name", ""),
                "request_type": details.get("request_type", ""),
                "proposed_data": details.get("proposed_data", {}),
                "preview_data": details.get("preview_data"),
                "explanation": data.get("content"),
                "timestamp": self._get_timestamp(data),
            }
            
            await self._broadcast(project_id, ws_message)
        
        except Exception as e:
            logger.error(f"Error handling approval request event: {e}", exc_info=True)
    
    async def _broadcast_generic(self, data, project_id):
        """Broadcast unknown event types as-is"""
        try:
            ws_message = {
                "type": data.get("event_type", "unknown"),
                "agent_name": data.get("agent_name", ""),
                "content": data.get("content", ""),
                "details": data.get("details", {}),
                "timestamp": self._get_timestamp(data),
            }
            
            await self._broadcast(project_id, ws_message)
        
        except Exception as e:
            logger.error(f"Error broadcasting generic event: {e}", exc_info=True)
