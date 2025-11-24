"""
Approval Handler

Handles approval request events (human-in-the-loop)
"""

import logging
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class ApprovalHandler(BaseEventHandler):
    """Handles approval-related WebSocket events"""

    async def handle_approval_request(self, event):
        """Handle approval request events"""
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Approval request event missing project_id")
                return

            ws_message = {
                "type": "approval_request",
                "approval_request_id": str(event_data.get("approval_request_id", "")),
                "request_type": event_data.get("request_type", ""),
                "agent_name": event_data.get("agent_name", ""),
                "proposed_data": event_data.get("proposed_data", {}),
                "preview_data": event_data.get("preview_data", {}),
                "explanation": event_data.get("explanation", ""),
                "timestamp": self._get_timestamp(event_data),
            }

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling approval request: {e}", exc_info=True)
