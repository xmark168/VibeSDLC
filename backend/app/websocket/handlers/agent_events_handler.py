"""
Agent Events Handler

Simplified handler with 5 event types only:
- agent.messaging.start
- agent.messaging.analyzing
- agent.messaging.tool_call
- agent.messaging.response
- agent.messaging.finish
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Session

from app.models import Message as MessageModel, AuthorType, MessageVisibility
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class AgentEventsHandler(BaseEventHandler):
    """
    Simplified handler for agent events using agent.messaging.* pattern.
    
    Only 5 event types:
    1. start - Agent begins execution
    2. analyzing - Progress/steps
    3. tool_call - Tool execution
    4. response - Agent message (saved to DB)
    5. finish - Execution complete
    """
    
    async def handle_agent_event(self, event):
        """Route agent event to one of 5 handlers"""
        try:
            event_data = self._normalize_event(event)
            event_type = event_data.get("event_type", "")
            
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning(f"Agent event missing project_id: {event_type}")
                return
            
            # Check for active connections (skip if no one is listening)
            has_connections = self._has_active_connections(project_id)
            logger.info(
                f"[AGENT_EVENT] Received {event_type} for project {project_id} - "
                f"Active connections: {has_connections}"
            )
            
            # Skip if no active connections (real-time only)
            if not has_connections:
                logger.info(f"Skipping event {event_type} - no active connections for project {project_id}")
                return
            
            # Map old event types to new handlers
            type_map = {
                "agent.thinking": "start",
                "agent.progress": "analyzing",
                "agent.tool_call": "tool_call",
                "agent.response": "response",
                "agent.completed": "finish",
                "agent.idle": "finish",
            }
            
            handler_type = type_map.get(event_type)
            if not handler_type:
                logger.warning(f"Unknown event type: {event_type}, skipping")
                return
            
            # Route to handler
            handler_method = getattr(self, f"_handle_{handler_type}", None)
            if handler_method:
                await handler_method(event_data, project_id)
            else:
                logger.error(f"Handler not found: _handle_{handler_type}")
        
        except Exception as e:
            logger.error(f"Error handling agent event: {e}", exc_info=True)
    
    # ========================================================================
    # 5 Handler Methods
    # ========================================================================
    
    async def _handle_start(self, data, project_id):
        """agent.messaging.start - Agent begins execution"""
        try:
            ws_message = {
                "type": "agent.messaging.start",
                "id": str(data.get("execution_id") or uuid4()),
                "agent_name": data.get("agent_name", "Agent"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._broadcast(project_id, ws_message)
            logger.info(f"[START] {data.get('agent_name')} execution {ws_message['id']}")
        except Exception as e:
            logger.error(f"Error in _handle_start: {e}", exc_info=True)
    
    async def _handle_analyzing(self, data, project_id):
        """agent.messaging.analyzing - Progress step"""
        try:
            ws_message = {
                "type": "agent.messaging.analyzing",
                "id": str(data.get("execution_id") or uuid4()),
                "agent_name": data.get("agent_name", "Agent"),
                "step": data.get("content", "Processing..."),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._broadcast(project_id, ws_message)
            logger.info(f"[ANALYZING] {data.get('agent_name')}: {ws_message['step']}")
        except Exception as e:
            logger.error(f"Error in _handle_analyzing: {e}", exc_info=True)
    
    async def _handle_tool_call(self, data, project_id):
        """agent.messaging.tool_call - Tool execution"""
        try:
            details = data.get("details", {})
            ws_message = {
                "type": "agent.messaging.tool_call",
                "id": str(uuid4()),
                "execution_id": str(data.get("execution_id", "")),
                "agent_name": data.get("agent_name", "Agent"),
                "tool": details.get("tool", "unknown"),
                "action": data.get("content", "Executing tool"),
                "state": details.get("state", "started"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._broadcast(project_id, ws_message)
            logger.info(f"[TOOL] {data.get('agent_name')}: {ws_message['action']} ({ws_message['state']})")
        except Exception as e:
            logger.error(f"Error in _handle_tool_call: {e}", exc_info=True)
    
    async def _handle_response(self, data, project_id):
        """agent.messaging.response - Save agent message to DB and broadcast"""
        try:
            logger.info(f"_handle_response called: project_id={project_id}")
            content = data.get("content", "")
            details = data.get("details", {})
            agent_name = data.get("agent_name", "Agent")
            execution_id = data.get("execution_id")
            
            # Extract structured data from details
            message_type = details.get("message_type", "text")
            structured_data_payload = details.get("data")
            
            # Save message to database using MessageService
            with Session(self.engine) as db_session:
                from app.services import MessageService
                message_service = MessageService(db_session)
                db_message = message_service.create_agent_message(
                    project_id=project_id,
                    agent_name=agent_name,
                    content=content,
                    execution_id=execution_id,
                    message_type=message_type,
                    structured_data=structured_data_payload,
                )
                message_id = db_message.id
            
            logger.info(f"[RESPONSE] Saved message {message_id} from {agent_name}")
            
            # Broadcast to WebSocket with NEW format
            ws_message = {
                "type": "agent.messaging.response",
                "id": str(message_id),
                "execution_id": str(execution_id) if execution_id else "",
                "agent_name": agent_name,
                "content": content,
                "message_type": message_type,
                "structured_data": structured_data_payload,
                "timestamp": db_message.created_at.isoformat(),  # Use DB timestamp
            }
            
            logger.info(f"Broadcasting agent response to WebSocket: message_id={message_id}, project={project_id}")
            await self._broadcast(project_id, ws_message)
        
        except Exception as e:
            logger.error(f"Error in _handle_response: {e}", exc_info=True)
    
    async def _handle_finish(self, data, project_id):
        """agent.messaging.finish - Execution complete"""
        try:
            logger.info(f"🏁 [_handle_finish] Called with data: {data}")
            ws_message = {
                "type": "agent.messaging.finish",
                "id": str(data.get("execution_id") or uuid4()),
                "agent_name": data.get("agent_name", "Agent"),
                "summary": data.get("content", "Completed"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(f"🏁 [_handle_finish] Broadcasting message: {ws_message}")
            await self._broadcast(project_id, ws_message)
            logger.info(f"🏁 [FINISH] {data.get('agent_name')} execution {ws_message['id']}")
        except Exception as e:
            logger.error(f"❌ Error in _handle_finish: {e}", exc_info=True)
    

