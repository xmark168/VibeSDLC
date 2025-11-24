"""
Story Handler

Handles story-related events (created, updated, status changed)
"""

import logging
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class StoryHandler(BaseEventHandler):
    """Handles story-related WebSocket events"""

    async def handle_story_created(self, event):
        """Handle story created events"""
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
        """Handle story updated events"""
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
        """Handle story status change events"""
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
