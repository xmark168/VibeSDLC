"""
Agent Events Handler - Handles agent messaging events broadcast
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class AgentEventsHandler(BaseEventHandler):
    """Simplified handler for agent events using agent.messaging.* pattern."""
    
    async def handle_agent_event(self, event):
        try:
            event_data = self._normalize_event(event)
            event_type = event_data.get("event_type", "")
            
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning(f"Agent event missing project_id: {event_type}")
                return
            
            has_connections = self._has_active_connections(project_id)
            logger.info(f"[AGENT_EVENT] Received {event_type} for project {project_id} - Active connections: {has_connections}")
            
            if not has_connections:
                logger.info(f"Skipping event {event_type} - no active connections for project {project_id}")
                return
            
            type_map = {
                "agent.thinking": "start",
                "agent.tool_call": "tool_call",
                "agent.response": "response",
                "agent.completed": "finish",
                "agent.idle": "finish",
            }
            
            handler_type = type_map.get(event_type)
            if not handler_type:
                logger.warning(f"Unknown event type: {event_type}, skipping")
                return
            
            handler_method = getattr(self, f"_handle_{handler_type}", None)
            if handler_method:
                await handler_method(event_data, project_id)
            else:
                logger.error(f"Handler not found: _handle_{handler_type}")
        
        except Exception as e:
            logger.error(f"Error handling agent event: {e}", exc_info=True)
    
    async def _handle_start(self, data, project_id):
        try:
            ws_message = {
                "type": "agent.messaging.start",
                "id": str(data.get("execution_id") or uuid4()),
                "agent_name": data.get("agent_name", "Agent"),
                "content": data.get("content", "Processing..."),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._broadcast(project_id, ws_message)
        except Exception as e:
            logger.error(f"Error in _handle_start: {e}")
    
    async def _handle_tool_call(self, data, project_id):
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
        except Exception as e:
            logger.error(f"Error in _handle_tool_call: {e}")
    
    async def _handle_response(self, data, project_id):
        """Broadcast agent response to WebSocket clients.
        
        NOTE: DB save is handled by base_agent._handle_simple_message()
        This handler only broadcasts to WebSocket using the message_id from the event.
        """
        try:
            content = data.get("content", "")
            details = data.get("details", {})
            agent_name = data.get("agent_name", "Agent")
            execution_id = data.get("execution_id")
            message_type = details.get("message_type", "text")
            # Pass full details as structured_data (excluding message_id which is used separately)
            structured_data_payload = {k: v for k, v in details.items() if k != "message_id"}
            
            # Use message_id from base_agent (already saved to DB)
            message_id = details.get("message_id")
            if not message_id:
                message_id = str(uuid4())
                logger.warning(f"[_handle_response] No message_id in event, generated fallback: {message_id}")
            
            ws_message = {
                "type": "agent.messaging.response",
                "id": message_id,
                "execution_id": str(execution_id) if execution_id else "",
                "agent_name": agent_name,
                "content": content,
                "message_type": message_type,
                "structured_data": structured_data_payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._broadcast(project_id, ws_message)
        
        except Exception as e:
            logger.error(f"Error in _handle_response: {e}")
    
    async def _handle_finish(self, data, project_id):
        try:
            ws_message = {
                "type": "agent.messaging.finish",
                "id": str(data.get("execution_id") or uuid4()),
                "agent_name": data.get("agent_name", "Agent"),
                "summary": data.get("content", "Completed"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._broadcast(project_id, ws_message)
        except Exception as e:
            logger.error(f"Error in _handle_finish: {e}")
    

