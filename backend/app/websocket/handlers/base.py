"""
Base Event Handler

Common functionality for all WebSocket event handlers
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.engine import Engine

from app.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class BaseEventHandler:
    """Base class for WebSocket event handlers"""

    def __init__(self, connection_manager: ConnectionManager, engine: Engine):
        self.connection_manager = connection_manager
        self.engine = engine

    def _to_uuid(self, value) -> Optional[UUID]:
        """Convert value to UUID, handling both string and UUID object."""
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            return None

    def _normalize_event(self, event) -> Dict[str, Any]:
        """Convert event (Pydantic model or dict) to dict."""
        if hasattr(event, 'model_dump'):
            return event.model_dump()
        return event if isinstance(event, dict) else {}

    async def _broadcast(self, project_id: UUID, message: Dict[str, Any]) -> None:
        """Broadcast message to all connections in a project."""
        try:
            await self.connection_manager.broadcast_to_project(message, project_id)
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}", exc_info=True)

    def _has_active_connections(self, project_id: UUID) -> bool:
        """Check if project has active WebSocket connections."""
        return self.connection_manager.get_project_connection_count(project_id) > 0

    def _get_timestamp(self, event_data: Dict[str, Any]) -> str:
        """Get timestamp from event data or generate new one."""
        timestamp = event_data.get("timestamp")
        if timestamp:
            return str(timestamp)
        return datetime.now(timezone.utc).isoformat()
