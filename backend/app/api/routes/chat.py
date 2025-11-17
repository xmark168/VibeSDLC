"""
WebSocket Chat API

Real-time chat endpoint for project communication
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends
from uuid import UUID
import logging
import json
from datetime import datetime

from app.websocket.connection_manager import connection_manager
from app.core.security import decode_access_token
from app.models import User
from sqlmodel import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: UUID = Query(...),
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time chat

    Query Parameters:
    - project_id: UUID of the project
    - token: JWT access token for authentication
    """
    try:
        # Authenticate user
        from app.core.db import engine
        from sqlmodel import Session

        with Session(engine) as session:
            try:
                payload = decode_access_token(token)
                user_id = payload.get("sub")
                if not user_id:
                    await websocket.close(code=1008, reason="Invalid token")
                    return

                user = session.get(User, UUID(user_id))
                if not user:
                    await websocket.close(code=1008, reason="User not found")
                    return
            except Exception as e:
                logger.error(f"WebSocket authentication error: {e}")
                await websocket.close(code=1008, reason="Authentication failed")
                return

        # Connect to project room
        await connection_manager.connect(websocket, project_id)

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "project_id": str(project_id),
            "user_id": str(user.id),
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.info(f"User {user.id} connected to project {project_id} via WebSocket")

        try:
            # Keep connection alive and handle ping/pong
            while True:
                # Receive messages from client
                data = await websocket.receive_text()

                try:
                    message = json.loads(data)
                    message_type = message.get("type")

                    # Handle ping
                    if message_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        continue

                    # Handle other message types
                    # Note: Actual message handling will be done via Kafka
                    # This WebSocket primarily receives events from Kafka bridge

                    logger.debug(f"Received WebSocket message: {message_type}")

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {data}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON format"
                    })

        except WebSocketDisconnect:
            connection_manager.disconnect(websocket)
            logger.info(f"User {user.id} disconnected from project {project_id}")
        except Exception as e:
            logger.error(f"WebSocket error for user {user.id}: {e}")
            connection_manager.disconnect(websocket)
            await websocket.close(code=1011, reason="Internal server error")

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


@router.get("/health")
async def chat_health():
    """Health check endpoint for chat service"""
    return {
        "status": "healthy",
        "total_connections": connection_manager.get_total_connections(),
        "active_projects": len(connection_manager.get_active_projects())
    }
