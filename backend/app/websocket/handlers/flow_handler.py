"""Flow Handler - Handles development flow execution events."""

import logging
from .base import BaseEventHandler

logger = logging.getLogger(__name__)


class FlowHandler(BaseEventHandler):
    """Handles flow-related WebSocket events."""

    async def handle_flow_event(self, event):
        try:
            event_data = self._normalize_event(event)
            project_id = self._to_uuid(event_data.get("project_id"))
            
            if not project_id:
                logger.warning("Flow event missing project_id")
                return

            ws_message = {
                "type": "scrum_master_step",
                "event_type": event_data.get("event_type", ""),
                "flow_id": str(event_data.get("flow_id", "")),
                "flow_type": event_data.get("flow_type", ""),
                "status": event_data.get("status", ""),
                "current_step": event_data.get("current_step"),
                "total_steps": event_data.get("total_steps"),
                "completed_steps": event_data.get("completed_steps"),
                "timestamp": self._get_timestamp(event_data),
            }

            if event_data.get("error_message"):
                ws_message["error_message"] = event_data["error_message"]

            if event_data.get("result"):
                ws_message["result"] = event_data["result"]

            await self._broadcast(project_id, ws_message)

        except Exception as e:
            logger.error(f"Error handling flow event: {e}", exc_info=True)
