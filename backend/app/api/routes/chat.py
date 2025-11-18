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
from app.models import User, Message as MessageModel, Project, AuthorType
from app.kafka import get_kafka_producer, KafkaTopics, UserMessageEvent
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
        # IMPORTANT: Accept WebSocket connection FIRST
        await websocket.accept()

        # Then authenticate user
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

                    # Handle user message
                    elif message_type == "message":
                        content = message.get("content", "").strip()
                        if not content:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Message content cannot be empty"
                            })
                            continue

                        # Save message to database
                        from app.core.db import engine
                        from sqlmodel import Session as DBSession

                        with DBSession(engine) as db_session:
                            # Verify project exists
                            project = db_session.get(Project, project_id)
                            if not project:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Project not found"
                                })
                                continue

                            # Create message
                            db_message = MessageModel(
                                project_id=project_id,
                                user_id=user.id,
                                agent_id=None,
                                content=content,
                                author_type=AuthorType.USER,
                                message_type=message.get("message_type", "text"),
                            )
                            db_session.add(db_message)
                            db_session.commit()
                            db_session.refresh(db_message)

                            message_id = db_message.id

                        logger.info(f"Message saved: {message_id} from user {user.id}")

                        # Publish to Kafka for agent processing
                        try:
                            producer = await get_kafka_producer()
                            user_message_event = UserMessageEvent(
                                message_id=message_id,
                                project_id=project_id,
                                user_id=user.id,
                                content=content,
                                message_type=message.get("message_type", "text"),
                            )
                            await producer.publish(
                                topic=KafkaTopics.USER_MESSAGES,
                                event=user_message_event,
                            )
                            logger.info(f"Message {message_id} published to Kafka")
                        except Exception as e:
                            logger.error(f"Failed to publish message to Kafka: {e}")

                        # Send acknowledgment to client
                        await websocket.send_json({
                            "type": "message_ack",
                            "message_id": str(message_id),
                            "status": "received",
                            "timestamp": datetime.utcnow().isoformat()
                        })

                        # Broadcast user message to all clients in project
                        await connection_manager.broadcast_to_project({
                            "type": "user_message",
                            "message_id": str(message_id),
                            "user_id": str(user.id),
                            "content": content,
                            "timestamp": datetime.utcnow().isoformat()
                        }, project_id)

                    # Handle user answer (for agent questions/approvals)
                    elif message_type == "user_answer":
                        approval_request_id = message.get("approval_request_id")
                        answer = message.get("answer")

                        if not approval_request_id or answer is None:
                            await websocket.send_json({
                                "type": "error",
                                "message": "approval_request_id and answer are required"
                            })
                            continue

                        # Publish approval response to Kafka
                        try:
                            from app.kafka.event_schemas import ApprovalResponseEvent

                            producer = await get_kafka_producer()
                            approval_event = ApprovalResponseEvent(
                                approval_request_id=UUID(approval_request_id),
                                project_id=project_id,
                                user_id=user.id,
                                approved=answer.get("approved", False) if isinstance(answer, dict) else bool(answer),
                                feedback=answer.get("feedback", "") if isinstance(answer, dict) else "",
                                modified_data=answer.get("modified_data") if isinstance(answer, dict) else None,
                            )
                            await producer.publish(
                                topic=KafkaTopics.APPROVAL_RESPONSES,
                                event=approval_event,
                            )
                            logger.info(f"Approval response published for {approval_request_id}")
                        except Exception as e:
                            logger.error(f"Failed to publish approval response: {e}")

                        await websocket.send_json({
                            "type": "answer_ack",
                            "approval_request_id": approval_request_id,
                            "status": "received",
                            "timestamp": datetime.utcnow().isoformat()
                        })

                    else:
                        logger.debug(f"Received unhandled WebSocket message type: {message_type}")

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
