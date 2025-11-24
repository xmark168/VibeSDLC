"""
Status Handler

Handles agent status, progress, and tool call events
"""

import logging
from .base import BaseEventHandler
from app.websocket.activity_buffer import activity_buffer

logger = logging.getLogger(__name__)


class StatusHandler(BaseEventHandler):
    """Handles status-related WebSocket events"""

    async def handle_agent_status(self, event):
        """Handle agent status events (thinking, acting, idle, etc.)"""
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Agent status event missing project_id")
                return

            # Skip if no active connections (real-time only)
            if not self._has_active_connections(project_id):
                return

            # Extract status
            status = event_data.get("status", "")
            if hasattr(status, 'value'):
                status = status.value
            elif not isinstance(status, str):
                status = str(status)

            ws_message = {
                "type": "agent_status",
                "agent_name": event_data.get("agent_name", ""),
                "status": status,
                "current_action": event_data.get("current_action"),
                "execution_id": str(event_data.get("execution_id", "")) if event_data.get("execution_id") else None,
                "timestamp": self._get_timestamp(event_data),
            }

            if event_data.get("error_message"):
                ws_message["error_message"] = event_data["error_message"]

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling agent status: {e}", exc_info=True)

    async def handle_agent_progress(self, event):
        """Handle agent progress events using activity buffer"""
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Agent progress event missing project_id")
                return

            # Skip if no active connections
            if not self._has_active_connections(project_id):
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

            # Update activity buffer
            activity_buffer.update_activity(
                execution_id=execution_id_str,
                project_id=project_id,
                agent_name=agent_name,
                step_number=step_number,
                total_steps=total_steps,
                step_description=step_description,
                step_status=step_status
            )

            # Get activity data for broadcast
            activity_data_obj = activity_buffer.get_activity(execution_id_str)
            
            if not activity_data_obj:
                logger.warning(f"Activity not found in buffer: {execution_id_str}")
                return

            # Build WebSocket message
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

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling agent progress: {e}", exc_info=True)

    async def handle_tool_call(self, event):
        """Handle tool call events"""
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Tool call event missing project_id")
                return

            # Skip if no active connections (real-time debugging info)
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
                "timestamp": self._get_timestamp(event_data),
            }

            if event_data.get("parameters"):
                ws_message["parameters"] = event_data["parameters"]
            if event_data.get("result"):
                ws_message["result"] = event_data["result"]
            if event_data.get("error_message"):
                ws_message["error_message"] = event_data["error_message"]

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling tool call: {e}", exc_info=True)
