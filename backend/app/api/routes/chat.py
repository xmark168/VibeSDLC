"""WebSocket Chat API."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState
from uuid import UUID
import asyncio
import logging
import json
from datetime import datetime, timezone
from app.websocket.connection_manager import connection_manager
from app.core.security import decode_access_token
from app.models import User, Message as MessageModel, Project, AuthorType, MessageVisibility
from app.kafka import get_kafka_producer, KafkaTopics, UserMessageEvent
from sqlmodel import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


async def update_websocket_activity(project_id: UUID):
    """Update WebSocket last_seen timestamp on user activity."""
    try:
        from app.core.db import engine
        from sqlmodel import Session as DBSession
        
        with DBSession(engine) as session:
            project = session.get(Project, project_id)
            if project:
                project.websocket_last_seen = datetime.now(timezone.utc)
                session.add(project)
                session.commit()
    except Exception as e:
        logger.debug(f"Failed to update WebSocket activity: {e}")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: UUID = Query(...),
    token: str = Query(...),
):
    """WebSocket endpoint for real-time chat"""
    logger.info(f"🔵 WebSocket connection attempt - project: {project_id}, token: {token[:20]}...")
    
    try:
        # IMPORTANT: Accept WebSocket connection FIRST
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for project {project_id}")

        # Then authenticate user
        from app.core.db import engine
        from sqlmodel import Session

        with Session(engine) as session:
            try:
                payload = decode_access_token(token)
                user_id = payload.get("sub")
                if not user_id:
                    logger.warning(f"Invalid token - no user_id in payload")
                    await websocket.close(code=1008, reason="Invalid token")
                    return

                user = session.get(User, UUID(user_id))
                if not user:
                    logger.warning(f"User not found: {user_id}")
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
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        logger.info(f"User {user.id} connected to project {project_id} via WebSocket")

        # Add connection limits to prevent resource leaks
        from datetime import timedelta
        MAX_CONNECTION_DURATION = timedelta(hours=24)
        HEARTBEAT_TIMEOUT = 120  # 2 minutes without message = dead connection
        connection_start = datetime.now()

        try:
            # Keep connection alive and handle ping/pong
            while True:
                # Check max connection duration (prevent infinite connections)
                if datetime.now() - connection_start > MAX_CONNECTION_DURATION:
                    logger.info(f"User {user.id} connection reached 24h limit, closing")
                    await websocket.send_json({
                        "type": "info",
                        "message": "Connection time limit reached, please reconnect"
                    })
                    break
                
                # Receive messages with timeout (detect dead connections)
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=HEARTBEAT_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"User {user.id} heartbeat timeout, closing connection")
                    break

                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    # Update WebSocket activity timestamp
                    await update_websocket_activity(project_id)

                    # Handle user message
                    if message_type == "message":
                        content = message.get("content", "").strip()
                        if not content:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Message content cannot be empty"
                            })
                            continue

                        # Parse agent routing info from @ mention
                        agent_id_str = message.get("agent_id")
                        agent_name = message.get("agent_name")
                        agent_id = UUID(agent_id_str) if agent_id_str else None

                        # Save message to database
                        from app.core.db import engine
                        from sqlmodel import Session as DBSession

                        message_id = None
                        db_message = None
                        
                        try:
                            with DBSession(engine) as db_session:
                                # Verify project exists
                                project = db_session.get(Project, project_id)
                                if not project:
                                    logger.warning(f"Project {project_id} not found")
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": "Project not found"
                                    })
                                    continue

                                # Deduct credit for user message
                                from app.services.credit_service import CreditService
                                credit_service = CreditService(db_session)
                                if not credit_service.deduct_credit(user.id):
                                    logger.warning(f"Insufficient credits for user {user.id}")
                                    await websocket.send_json({
                                        "type": "error",
                                        "code": 402,
                                        "message": "Insufficient credits"
                                    })
                                    continue

                                # Create message with agent routing info
                                db_message = MessageModel(
                                    project_id=project_id,
                                    user_id=user.id,
                                    agent_id=agent_id,  # Save mentioned agent ID for routing
                                    content=content,
                                    author_type=AuthorType.USER,
                                    visibility=MessageVisibility.USER_MESSAGE,  # User messages are always user-facing
                                    message_type=message.get("message_type", "text"),
                                )
                                
                                logger.debug(f"Creating message (user={user.id}, content_len={len(content)})")
                                db_session.add(db_message)
                                
                                try:
                                    db_session.commit()
                                    logger.info(f"Message committed to DB")
                                except Exception as commit_error:
                                    logger.error(f"DB commit failed: {commit_error}", exc_info=True)
                                    db_session.rollback()
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": f"Failed to save message: {str(commit_error)}"
                                    })
                                    continue
                                
                                db_session.refresh(db_message)
                                message_id = db_message.id
                                
                                # Verify message was actually saved
                                verify_message = db_session.get(MessageModel, message_id)
                                if not verify_message:
                                    logger.error(f"Message {message_id} not found after commit!")
                                    raise Exception("Message verification failed")
                                
                                logger.info(f"Message saved & verified: {message_id} (user={user.id}, content_len={len(content)})" +
                                          (f" targeting agent {agent_name} ({agent_id})" if agent_id else ""))

                        except Exception as db_error:
                            logger.error(f"Database error while saving message: {db_error}", exc_info=True)
                            await websocket.send_json({
                                "type": "error",
                                "message": "Database error occurred"
                            })
                            continue

                        # Only proceed if message was saved successfully
                        if not message_id or not db_message:
                            logger.error("Message ID is None after DB operation")
                            continue

                        # Publish to Kafka for agent processing
                        try:
                            producer = await get_kafka_producer()
                            user_message_event = UserMessageEvent(
                                message_id=message_id,
                                project_id=str(project_id),
                                user_id=str(user.id),
                                content=content,
                                message_type=message.get("message_type", "text"),
                                agent_id=agent_id,  # Include agent ID for routing
                                agent_name=agent_name,  # Include agent name for display
                            )

                            # Publish to global USER_MESSAGES topic (partitioned by project_id)
                            await producer.publish(
                                topic=KafkaTopics.USER_MESSAGES,
                                event=user_message_event,
                            )
                            logger.info(
                                f"Message {message_id} published to USER_MESSAGES topic for project {project_id}" +
                                (f" with routing to {agent_name}" if agent_name else "")
                            )
                        except Exception as e:
                            logger.error(f"Failed to publish message to Kafka: {e}")

                        # Broadcast user message back to all clients (including sender)
                        # for consistency and real-time sync
                        await connection_manager.broadcast_to_project(
                            {
                                "type": "user_message",
                                "message_id": str(message_id),
                                "project_id": str(project_id),
                                "content": content,
                                "author_type": "user",
                                "created_at": db_message.created_at.isoformat(),
                                "updated_at": db_message.updated_at.isoformat(),
                                "user_id": str(user.id),
                                "message_type": message.get("message_type", "text"),
                                "timestamp": db_message.created_at.isoformat(),
                            },
                            project_id
                        )
                        logger.info(f"Broadcasted user message {message_id} to all clients in project {project_id}")

                    # Handle clarification question answer
                    elif message_type == "question_answer":
                        question_id_str = message.get("question_id")
                        answer = message.get("answer")
                        selected_options = message.get("selected_options")
                        approved = message.get("approved")
                        modified_data = message.get("modified_data")
                        
                        if not question_id_str:
                            await websocket.send_json({
                                "type": "error",
                                "message": "question_id is required"
                            })
                            continue
                        
                        logger.info(f"[WS] User {user.id} answered question {question_id_str}")
                        
                        # Load question to get agent info
                        from app.core.db import engine
                        from sqlmodel import Session as DBSession
                        from app.models import AgentQuestion, QuestionStatus
                        
                        with DBSession(engine) as db_session:
                            question = db_session.get(AgentQuestion, UUID(question_id_str))
                            
                            if not question:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Question not found"
                                })
                                continue
                            
                            if question.status != QuestionStatus.WAITING_ANSWER:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Question already answered or expired"
                                })
                                continue
                            
                            # Publish answer event to Kafka
                            try:
                                from app.kafka.event_schemas import QuestionAnswerEvent
                                
                                producer = await get_kafka_producer()
                                answer_event = QuestionAnswerEvent(
                                    question_id=UUID(question_id_str),
                                    answer=answer or "",
                                    selected_options=selected_options,
                                    approved=approved,
                                    modified_data=modified_data,
                                    agent_id=question.agent_id,
                                    task_id=question.task_id,
                                    project_id=str(project_id),
                                    user_id=str(user.id),
                                )
                                
                                await producer.publish(
                                    topic=KafkaTopics.QUESTION_ANSWERS,
                                    event=answer_event
                                )
                                
                                logger.info(f"Question answer published for {question_id_str}")
                                
                                # Ack to user
                                await websocket.send_json({
                                    "type": "question_answer_received",
                                    "question_id": question_id_str,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                })
                            except Exception as e:
                                logger.error(f"Failed to publish question answer: {e}")
                                await websocket.send_json({
                                    "type": "error",
                                    "message": f"Failed to process answer: {str(e)}"
                                })
                    
                    # Handle batch clarification question answers
                    elif message_type == "question_batch_answer":
                        batch_id = message.get("batch_id")
                        answers = message.get("answers", [])
                        
                        if not batch_id or not answers:
                            await websocket.send_json({
                                "type": "error",
                                "message": "batch_id and answers are required"
                            })
                            continue
                        
                        logger.info(f"[WS] User {user.id} answered batch {batch_id} with {len(answers)} answers")
                        
                        # Get first question to extract agent_id and task_id
                        from app.core.db import engine
                        from sqlmodel import Session as DBSession
                        from app.models import AgentQuestion
                        
                        try:
                            with DBSession(engine) as db_session:
                                first_question = db_session.get(AgentQuestion, UUID(answers[0]["question_id"]))
                                
                                if not first_question:
                                    await websocket.send_json({
                                        "type": "error",
                                        "message": "First question not found"
                                    })
                                    continue
                                
                                # Update Message in DB to mark as answered
                                from app.models import Message as DbMessage
                                from sqlmodel import select
                                from sqlalchemy.orm.attributes import flag_modified
                                
                                # Find the batch message
                                stmt = select(DbMessage).where(
                                    DbMessage.project_id == project_id,
                                    DbMessage.message_type == "agent_question_batch",
                                ).limit(10)  # Get recent batch messages
                                
                                batch_messages = db_session.exec(stmt).all()
                                for batch_msg in batch_messages:
                                    if batch_msg.structured_data and batch_msg.structured_data.get("batch_id") == batch_id:
                                        # Update structured_data to mark as answered and store answers
                                        new_structured_data = {
                                            **batch_msg.structured_data, 
                                            "answered": True,
                                            "answers": answers  # Store user's answers for display
                                        }
                                        batch_msg.structured_data = new_structured_data
                                        flag_modified(batch_msg, "structured_data")  # Force SQLAlchemy to detect change
                                        db_session.add(batch_msg)
                                        db_session.commit()
                                        logger.info(f"Marked batch message {batch_id} as answered in DB")
                                        break
                                
                                # Publish batch answer event to Kafka
                                from app.kafka.event_schemas import BatchAnswersEvent
                                
                                producer = await get_kafka_producer()
                                batch_answer_event = BatchAnswersEvent(
                                    batch_id=batch_id,
                                    answers=answers,
                                    agent_id=first_question.agent_id,
                                    task_id=first_question.task_id,
                                    project_id=str(project_id),
                                    user_id=str(user.id),
                                )
                                
                                await producer.publish(
                                    topic=KafkaTopics.QUESTION_ANSWERS,
                                    event=batch_answer_event
                                )
                                
                                logger.info(f"Batch answers published for {batch_id} ({len(answers)} questions)")
                                
                                # Ack to user
                                await websocket.send_json({
                                    "type": "batch_answers_received",
                                    "batch_id": batch_id,
                                    "answer_count": len(answers),
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                })
                        except Exception as e:
                            logger.error(f"Failed to publish batch answers: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Failed to process batch answers: {str(e)}"
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
            # Only close if still connected
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.close(code=1011, reason="Internal server error")
            except:
                pass  # Already closed or closing

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        # Don't try to close again - cleanup only
        connection_manager.disconnect(websocket)


@router.get("/health")
async def chat_health():
    """Health check endpoint for chat service"""
    return {
        "status": "healthy",
        "total_connections": connection_manager.get_total_connections(),
        "active_projects": len(connection_manager.get_active_projects())
    }
