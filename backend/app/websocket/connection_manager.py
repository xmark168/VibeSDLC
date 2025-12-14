"""WebSocket Connection Manager for real-time project communication.

Manages WebSocket connections per project room, handling:
- Connection lifecycle (connect/disconnect)
- Message broadcasting to project rooms
- Database status synchronization
- Graceful cleanup of stale connections
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe WebSocket connection manager for project rooms.
    
    Each project has its own "room" where multiple clients can connect.
    Messages are broadcast to all clients in the same project room.
    """

    __slots__ = ('_connections', '_socket_to_project')

    def __init__(self):
        self._connections: dict[UUID, set[WebSocket]] = {}
        self._socket_to_project: dict[WebSocket, UUID] = {}

    # =========================================================================
    # Connection Lifecycle
    # =========================================================================

    async def connect(self, websocket: WebSocket, project_id: UUID) -> None:
        """Register a WebSocket connection to a project room."""
        if project_id not in self._connections:
            self._connections[project_id] = set()

        self._connections[project_id].add(websocket)
        self._socket_to_project[websocket] = project_id

        asyncio.create_task(self._update_project_status(project_id, connected=True))
        
        logger.info(
            f"WebSocket connected to project {project_id} "
            f"(total: {len(self._connections[project_id])})"
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection and cleanup if room is empty."""
        project_id = self._socket_to_project.pop(websocket, None)
        if project_id is None:
            return

        connections = self._connections.get(project_id)
        if connections:
            connections.discard(websocket)
            
            if not connections:
                del self._connections[project_id]
                logger.info(f"Project {project_id} room closed (no connections)")
                self._schedule_disconnect_tasks(project_id)
            else:
                logger.debug(
                    f"WebSocket disconnected from project {project_id} "
                    f"(remaining: {len(connections)})"
                )

    def _schedule_disconnect_tasks(self, project_id: UUID) -> None:
        """Schedule background tasks for disconnect cleanup."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._update_project_status(project_id, connected=False))
            loop.create_task(self._clear_active_agent(project_id))
        except RuntimeError:
            logger.debug("No event loop for disconnect cleanup")

    # =========================================================================
    # Message Sending
    # =========================================================================

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket) -> bool:
        """Send a message to a specific WebSocket."""
        if not self._is_connected(websocket):
            self.disconnect(websocket)
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")
            self.disconnect(websocket)
            return False

    async def broadcast_to_project(
        self,
        message: dict[str, Any],
        project_id: UUID
    ) -> int:
        """
        Broadcast a message to all connections in a project room.
        """
        connections = self._connections.get(project_id)
        if not connections:
            logger.debug(f"No connections for project {project_id}, skipping broadcast")
            return 0

        snapshot = list(connections)
        success_count = 0
        failed: list[WebSocket] = []
        
        for ws in snapshot:
            if await self._send_safe(ws, message):
                success_count += 1
            else:
                failed.append(ws)

        for ws in failed:
            self.disconnect(ws)
        
        if failed:
            logger.debug(
                f"Broadcast to {project_id}: {success_count} success, "
                f"{len(failed)} failed/cleaned"
            )
        
        return success_count

    async def _send_safe(self, websocket: WebSocket, message: dict[str, Any]) -> bool:
        """Safely send a message, handling connection errors."""
        if not self._is_connected(websocket):
            return False

        try:
            await websocket.send_json(message)
            return True
        except RuntimeError as e:
            if "close message" in str(e).lower():
                logger.debug("WebSocket already closing")
            else:
                logger.warning(f"Runtime error sending: {e}")
            return False
        except Exception as e:
            logger.warning(f"Error sending to WebSocket: {e}")
            return False

    @staticmethod
    def _is_connected(websocket: WebSocket) -> bool:
        """Check if a WebSocket is still connected."""
        try:
            return websocket.client_state == WebSocketState.CONNECTED
        except Exception:
            return False

    # =========================================================================
    # Stats & Queries
    # =========================================================================

    def get_project_connection_count(self, project_id: UUID) -> int:
        """Get number of active connections for a project."""
        return len(self._connections.get(project_id, set()))

    def get_total_connections(self) -> int:
        """Get total number of connections across all projects."""
        return sum(len(conns) for conns in self._connections.values())

    def get_active_projects(self) -> list[UUID]:
        """Get list of projects with active connections."""
        return list(self._connections.keys())

    def has_connections(self, project_id: UUID) -> bool:
        """Check if a project has any active connections."""
        return bool(self._connections.get(project_id))

    # =========================================================================
    # Database Operations (run in thread pool)
    # =========================================================================

    async def _update_project_status(self, project_id: UUID, connected: bool) -> None:
        """Update project's WebSocket status in database."""
        def _update(session):
            from app.models import Project
            project = session.get(Project, project_id)
            if project:
                project.websocket_connected = connected
                project.websocket_last_seen = datetime.now(timezone.utc)
                session.add(project)
                session.commit()

        try:
            from app.core.async_db import AsyncDB
            await AsyncDB.execute(_update)
            logger.debug(f"Updated WebSocket status: project={project_id}, connected={connected}")
        except Exception as e:
            logger.error(f"Failed to update WebSocket status: {e}")

    async def _clear_active_agent(self, project_id: UUID) -> None:
        """Clear active agent context when project disconnects."""
        def _clear(session):
            from app.models import Project
            project = session.get(Project, project_id)
            if project and project.active_agent_id:
                old_agent = project.active_agent_id
                project.active_agent_id = None
                project.active_agent_updated_at = None
                session.add(project)
                session.commit()
                return old_agent
            return None

        try:
            from app.core.async_db import AsyncDB
            old_agent = await AsyncDB.execute(_clear)
            if old_agent:
                logger.info(f"Cleared active agent for project {project_id} (was: {old_agent})")
        except Exception as e:
            logger.error(f"Failed to clear active agent: {e}")


connection_manager = ConnectionManager()
