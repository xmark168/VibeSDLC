"""Task Handler - Handles agent task events."""

import logging
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class TaskHandler(BaseEventHandler):
    """Handles task-related WebSocket events."""

    async def handle_task_assigned(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Task assigned event missing project_id")
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
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling task assigned: {e}", exc_info=True)

    async def handle_task_started(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Task started event missing project_id")
                return

            if not self._has_active_connections(project_id):
                return

            ws_message = {
                "type": "task_started",
                "task_id": str(event_data.get("task_id", "")),
                "agent_id": str(event_data.get("agent_id", "")),
                "agent_name": event_data.get("agent_name", ""),
                "execution_id": str(event_data.get("execution_id", "")),
                "started_at": str(event_data.get("started_at", "")),
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling task started: {e}", exc_info=True)

    async def handle_task_progress(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Task progress event missing project_id")
                return

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
                "timestamp": self._get_timestamp(event_data),
            }

            if event_data.get("estimated_completion"):
                ws_message["estimated_completion"] = str(event_data["estimated_completion"])

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling task progress: {e}", exc_info=True)

    async def handle_task_completed(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Task completed event missing project_id")
                return

            ws_message = {
                "type": "task_completed",
                "task_id": str(event_data.get("task_id", "")),
                "agent_id": str(event_data.get("agent_id", "")),
                "agent_name": event_data.get("agent_name", ""),
                "execution_id": str(event_data.get("execution_id", "")),
                "completed_at": str(event_data.get("completed_at", "")),
                "duration_seconds": event_data.get("duration_seconds", 0),
                "timestamp": self._get_timestamp(event_data),
            }

            if event_data.get("result"):
                ws_message["result"] = event_data["result"]
            if event_data.get("artifacts"):
                ws_message["artifacts"] = event_data["artifacts"]

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling task completed: {e}", exc_info=True)

    async def handle_task_failed(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Task failed event missing project_id")
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
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling task failed: {e}", exc_info=True)

    async def handle_task_cancelled(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Task cancelled event missing project_id")
                return

            ws_message = {
                "type": "task_cancelled",
                "task_id": str(event_data.get("task_id", "")),
                "agent_id": str(event_data.get("agent_id", "")),
                "agent_name": event_data.get("agent_name", ""),
                "cancelled_by": event_data.get("cancelled_by", ""),
                "cancelled_at": str(event_data.get("cancelled_at", "")),
                "reason": event_data.get("reason"),
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling task cancelled: {e}", exc_info=True)
