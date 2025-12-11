"""Story Handler - Handles Kanban story events."""

import logging
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class StoryHandler(BaseEventHandler):
    """Handles story-related WebSocket events."""

    async def handle_story_created(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Story created event missing project_id")
                return

            ws_message = {
                "type": "kanban_update",
                "action": "story_created",
                "story_id": str(event_data.get("story_id", "")),
                "title": event_data.get("title", ""),
                "status": event_data.get("status", ""),
                "story_type": event_data.get("story_type", ""),
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling story created: {e}", exc_info=True)

    async def handle_story_updated(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Story updated event missing project_id")
                return

            ws_message = {
                "type": "kanban_update",
                "action": "story_updated",
                "story_id": str(event_data.get("story_id", "")),
                "updated_fields": event_data.get("updated_fields", {}),
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling story updated: {e}", exc_info=True)

    async def handle_story_status_changed(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Story status change event missing project_id")
                return

            ws_message = {
                "type": "kanban_update",
                "action": "story_status_changed",
                "story_id": str(event_data.get("story_id", "")),
                "old_status": event_data.get("old_status", ""),
                "new_status": event_data.get("new_status", ""),
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling story status change: {e}", exc_info=True)

    async def handle_story_message_created(self, event):
        """Handle story channel message from agent/user."""
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Story message event missing project_id")
                return

            ws_message = {
                "type": "story_message",
                "story_id": str(event_data.get("story_id", "")),
                "message_id": str(event_data.get("message_id", "")),
                "author_type": event_data.get("author_type", ""),
                "author_name": event_data.get("author_name", ""),
                "content": event_data.get("content", ""),
                "message_type": event_data.get("message_type", "update"),
                "structured_data": event_data.get("structured_data"),
                "details": event_data.get("structured_data"),  # Alias for frontend
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)
            logger.debug(f"Broadcasted story message to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling story message: {e}", exc_info=True)

    async def handle_story_agent_state_changed(self, event):
        """Handle agent execution state change on a story."""
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Story agent state event missing project_id")
                return

            ws_message = {
                "type": "story_agent_state",
                "story_id": str(event_data.get("story_id", "")),
                "agent_state": event_data.get("agent_state", ""),
                "old_state": event_data.get("old_state"),
                "agent_id": str(event_data.get("agent_id", "")) if event_data.get("agent_id") else None,
                "agent_name": event_data.get("agent_name", ""),
                "progress_message": event_data.get("progress_message"),
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)
            logger.debug(f"Broadcasted story agent state to project {project_id}")

        except Exception as e:
            logger.error(f"Error handling story agent state: {e}", exc_info=True)
