"""
WebSocket Connection Manager
"""

from typing import Dict, List, Set
from uuid import UUID
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for projects"""

    def __init__(self):
        # project_id -> set of WebSocket connections
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
        # websocket -> project_id mapping for cleanup
        self.websocket_to_project: Dict[WebSocket, UUID] = {}

    async def connect(self, websocket: WebSocket, project_id: UUID):
        """
        Connect a WebSocket to a project room.
        """
        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()

        self.active_connections[project_id].add(websocket)
        self.websocket_to_project[websocket] = project_id

        logger.info(f"WebSocket connected to project {project_id}.")

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket"""
        if websocket not in self.websocket_to_project:
            return

        project_id = self.websocket_to_project[websocket]

        if project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)

            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
                logger.info(f"Project {project_id} room closed (no active connections)")

        # Remove from mapping
        del self.websocket_to_project[websocket]

        logger.info(f"WebSocket disconnected from project {project_id}.")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast_to_project(self, message: dict, project_id: UUID):
        """Broadcast a message to all connections in a project"""
        if project_id not in self.active_connections:
            logger.warning(f"No active connections for project {project_id}")
            return

        disconnected = []
        for connection in self.active_connections[project_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)

    def get_project_connection_count(self, project_id: UUID) -> int:
        """Get the number of active connections for a project"""
        return len(self.active_connections.get(project_id, set()))

    def get_total_connections(self) -> int:
        """Get the total number of active connections across all projects"""
        return sum(len(conns) for conns in self.active_connections.values())

    def get_active_projects(self) -> List[UUID]:
        """Get list of projects with active connections"""
        return list(self.active_connections.keys())

connection_manager = ConnectionManager()
