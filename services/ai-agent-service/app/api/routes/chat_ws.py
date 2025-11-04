from typing import Any
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlmodel import Session, select
import json
import asyncio
from datetime import datetime

from app.api.deps import get_current_user, get_db
from app.models import Message as MessageModel, Project, User, AuthorType
from app.core.config import settings
from app.core.response_queue import response_manager

router = APIRouter(prefix="/chat", tags=["chat"])


# Global cache for pending previews (key: preview_id, value: preview_data)
# This stores preview data temporarily until user approves/edits/regenerates
pending_previews: dict[str, dict[str, Any]] = {}


class ConnectionManager:
    def __init__(self):
        # Store connections by project_id
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)

    def disconnect(self, websocket: WebSocket, project_id: str):
        print(f"[ConnectionManager] Disconnecting websocket from project {project_id}", flush=True)
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
                print(f"[ConnectionManager] ✓ Removed connection. Remaining: {len(self.active_connections[project_id])}", flush=True)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
                print(f"[ConnectionManager] ✓ Removed project {project_id} (no more connections)", flush=True)
        else:
            print(f"[ConnectionManager] ⚠ Project {project_id} not found in active connections", flush=True)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_project(self, message: dict, project_id: str):
        """Broadcast message to all connections in a project"""
        print(f"[ConnectionManager] broadcast_to_project called: type={message.get('type')}, project_id={project_id}", flush=True)

        # Cache agent_preview messages for later retrieval when user approves
        if message.get("type") == "agent_preview" and "preview_id" in message:
            preview_id = message["preview_id"]
            pending_previews[preview_id] = message
            print(f"[Cache] Stored preview {preview_id} in cache", flush=True)

        if project_id in self.active_connections:
            num_connections = len(self.active_connections[project_id])
            print(f"[ConnectionManager] Found {num_connections} connections for project {project_id}", flush=True)
            disconnected = []
            for i, connection in enumerate(self.active_connections[project_id]):
                try:
                    print(f"[ConnectionManager] Sending to connection {i+1}/{num_connections}...", flush=True)
                    await connection.send_json(message)
                    print(f"[ConnectionManager] ✓ Sent to connection {i+1}", flush=True)
                except Exception as e:
                    print(f"[ConnectionManager] ✗ Failed to send to connection {i+1}: {e}", flush=True)
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn, project_id)
        else:
            print(f"[ConnectionManager] ⚠ No connections found for project {project_id}", flush=True)
            print(f"[ConnectionManager] Active projects: {list(self.active_connections.keys())}", flush=True)


manager = ConnectionManager()


# ===== Step-by-Step Workflow Helpers =====

def get_next_agent_from_message_type(message_type: str) -> str | None:
    """Determine next agent to run based on approved message type"""
    step_map = {
        "product_brief": "vision",      # Brief approved → Run Vision Agent
        "product_vision": "backlog",    # Vision approved → Run Backlog Agent
        "product_backlog": "priority",  # Backlog approved → Run Priority Agent
    }
    return step_map.get(message_type)


async def trigger_next_step_auto(
    project_id: str,
    user_id: str,
    approved_message_id: str,  # Pass ID instead of object
    websocket_broadcast_fn,
    response_manager,
    event_loop
):
    """Auto-trigger next agent after user approves a preview in step-by-step mode"""

    # Create new session for this task
    from app.core.db import engine
    step_session = Session(engine)

    try:
        # Query approved message to get type and data
        approved_message = step_session.exec(
            select(MessageModel).where(MessageModel.id == UUID(approved_message_id))
        ).first()

        if not approved_message:
            print(f"[Auto-Trigger] ⚠ Approved message not found: {approved_message_id}", flush=True)
            return

        next_agent = get_next_agent_from_message_type(approved_message.message_type)

        if not next_agent:
            # No next step (Priority is final step)
            print(f"[Auto-Trigger] Workflow complete for project {project_id}", flush=True)
            await websocket_broadcast_fn({
                "type": "agent_step",
                "step": "completed",
                "agent": "PO Agent",
                "message": "✅ Workflow hoàn thành! Tất cả 4 bước đã xong."
            }, project_id)
            return

        print(f"\n[Auto-Trigger] ===== TRIGGERING NEXT AGENT =====", flush=True)
        print(f"[Auto-Trigger] Current step: {approved_message.message_type}", flush=True)
        print(f"[Auto-Trigger] Next agent: {next_agent}", flush=True)
        print(f"[Auto-Trigger] Project: {project_id}", flush=True)

        # Wait a bit for user to see approved message
        await asyncio.sleep(1.5)

        if next_agent == "vision":
            # Get approved brief from DB
            brief_msg = step_session.exec(
                select(MessageModel)
                .where(MessageModel.project_id == UUID(project_id))
                .where(MessageModel.message_type == "product_brief")
                .order_by(MessageModel.created_at.desc())
            ).first()

            if brief_msg and brief_msg.structured_data:
                print(f"[Auto-Trigger] Found brief in DB: {brief_msg.structured_data.get('product_name')}", flush=True)

                # Send agent_step to show progress indicator
                await websocket_broadcast_fn({
                    "type": "agent_step",
                    "step": "started",
                    "agent": "Vision Agent",
                    "message": "🔄 Đang tạo Product Vision..."
                }, project_id)

                # Trigger Vision Agent
                from app.agents.product_owner.vision_agent import VisionAgent

                vision_agent = VisionAgent(
                    session_id=f"vision_auto_{project_id}",
                    user_id=user_id,
                    websocket_broadcast_fn=websocket_broadcast_fn,
                    project_id=project_id,
                    response_manager=response_manager,
                    event_loop=event_loop
                )

                print(f"[Auto-Trigger] Starting Vision Agent...", flush=True)
                await vision_agent.run_async(
                    product_brief=brief_msg.structured_data,
                    thread_id=f"vision_auto_{project_id}"
                )
                print(f"[Auto-Trigger] Vision Agent completed", flush=True)
            else:
                print(f"[Auto-Trigger] ⚠ Brief not found in DB", flush=True)

        elif next_agent == "backlog":
            # Get approved vision from DB
            vision_msg = step_session.exec(
                select(MessageModel)
                .where(MessageModel.project_id == UUID(project_id))
                .where(MessageModel.message_type == "product_vision")
                .order_by(MessageModel.created_at.desc())
            ).first()

            if vision_msg and vision_msg.structured_data:
                print(f"[Auto-Trigger] Found vision in DB", flush=True)

                # Send agent_step to show progress indicator
                await websocket_broadcast_fn({
                    "type": "agent_step",
                    "step": "started",
                    "agent": "Backlog Agent",
                    "message": "🔄 Đang tạo Product Backlog..."
                }, project_id)

                # Trigger Backlog Agent
                from app.agents.product_owner.backlog_agent import BacklogAgent

                backlog_agent = BacklogAgent(
                    session_id=f"backlog_auto_{project_id}",
                    user_id=user_id,
                    websocket_broadcast_fn=websocket_broadcast_fn,
                    project_id=project_id,
                    response_manager=response_manager,
                    event_loop=event_loop
                )

                print(f"[Auto-Trigger] Starting Backlog Agent...", flush=True)
                await backlog_agent.run_async(
                    product_vision=vision_msg.structured_data,
                    thread_id=f"backlog_auto_{project_id}"
                )
                print(f"[Auto-Trigger] Backlog Agent completed", flush=True)
            else:
                print(f"[Auto-Trigger] ⚠ Vision not found in DB", flush=True)

        elif next_agent == "priority":
            # Get approved backlog from DB
            backlog_msg = step_session.exec(
                select(MessageModel)
                .where(MessageModel.project_id == UUID(project_id))
                .where(MessageModel.message_type == "product_backlog")
                .order_by(MessageModel.created_at.desc())
            ).first()

            if backlog_msg and backlog_msg.structured_data:
                print(f"[Auto-Trigger] Found backlog in DB", flush=True)

                # Send agent_step to show progress indicator
                await websocket_broadcast_fn({
                    "type": "agent_step",
                    "step": "started",
                    "agent": "Priority Agent",
                    "message": "🔄 Đang sắp xếp ưu tiên và tạo Sprint Plan..."
                }, project_id)

                # Trigger Priority Agent
                from app.agents.product_owner.priority_agent import PriorityAgent

                priority_agent = PriorityAgent(
                    session_id=f"priority_auto_{project_id}",
                    user_id=user_id,
                    websocket_broadcast_fn=websocket_broadcast_fn,
                    project_id=project_id,
                    response_manager=response_manager,
                    event_loop=event_loop
                )

                print(f"[Auto-Trigger] Starting Priority Agent...", flush=True)
                await priority_agent.run_async(
                    product_backlog=backlog_msg.structured_data,
                    thread_id=f"priority_auto_{project_id}"
                )
                print(f"[Auto-Trigger] Priority Agent completed", flush=True)
            else:
                print(f"[Auto-Trigger] ⚠ Backlog not found in DB", flush=True)

    except Exception as e:
        print(f"[Auto-Trigger] ✗ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

        await websocket_broadcast_fn({
            "type": "agent_step",
            "step": "error",
            "agent": next_agent.capitalize() + " Agent" if 'next_agent' in locals() else "Agent",
            "message": f"❌ Lỗi khi chạy agent: {str(e)}"
        }, project_id)
    finally:
        step_session.close()
        print(f"[Auto-Trigger] Session closed", flush=True)



@router.get("/info")
def get_websocket_info():
    """
    Get WebSocket connection information.
    
    WebSocket endpoint is available at: ws://localhost:8000/api/v1/chat/ws
    
    Note: WebSocket endpoints don't appear in /docs because OpenAPI/Swagger 
    doesn't support WebSocket protocol well. This is normal behavior.
    
    To test WebSocket:
    1. Use browser console: new WebSocket('ws://localhost:8000/api/v1/chat/ws?project_id=UUID&token=JWT')
    2. Use wscat: wscat -c "ws://localhost:8000/api/v1/chat/ws?project_id=UUID&token=JWT"
    3. Use the frontend ChatPanelWS component
    
    See docs/WEBSOCKET_TESTING.md for detailed testing guide.
    """
    return {
        "websocket_url": "/api/v1/chat/ws",
        "protocol": "WebSocket",
        "parameters": {
            "project_id": "UUID (required, query parameter)",
            "token": "JWT token (required, query parameter)"
        },
        "message_format": {
            "client_to_server": {
                "type": "message | user_answer | ping",
                "content": "Your message here (for message type)",
                "author_type": "user (for message type)",
                "question_id": "UUID (for user_answer type)",
                "answer": "Your answer (for user_answer type)"
            },
            "server_to_client": {
                "type": "message | agent_message | typing | connected | pong | routing | agent_step | agent_thinking | tool_call | agent_question",
                "data": "Message object or other data"
            }
        },
        "example_connection": "ws://localhost:8000/api/v1/chat/ws?project_id=YOUR_PROJECT_ID&token=YOUR_TOKEN",
        "testing_guide": "/docs/WEBSOCKET_TESTING.md",
        "current_connections": {
            "total_projects": len(manager.active_connections),
            "total_connections": sum(len(conns) for conns in manager.active_connections.values()),
        }
    }


@router.get("/stats")
def get_connection_stats(current_user = Depends(get_current_user)):
    """
    Get current WebSocket connection statistics.
    Requires authentication.
    """
    return {
        "total_projects": len(manager.active_connections),
        "total_connections": sum(len(conns) for conns in manager.active_connections.values()),
        "projects": {
            project_id: len(conns) 
            for project_id, conns in manager.active_connections.items()
        }
    }


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str = Query(...),
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time chat communication.
    
    Protocol:
    - Client sends: {"type": "message", "content": "...", "author_type": "user"}
    - Server responds: {"type": "message", "data": {...message object...}}
    - Server sends agent responses: {"type": "agent_message", "data": {...}}
    - Server sends typing indicators: {"type": "typing", "agent_name": "..."}
    """
    # Validate token and get user
    from app.core.security import decode_access_token
    import jwt
    
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    except Exception as e:
        print(f"Token validation error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Get database session
    from app.core.db import engine
    session = Session(engine)
    
    try:
        # Validate project exists
        project = session.get(Project, UUID(project_id))
        if not project:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Connect to manager
        await manager.connect(websocket, project_id)
        
        # Send connection success
        await websocket.send_json({
            "type": "connected",
            "project_id": project_id,
            "message": "Connected to chat"
        })

        # Start background task to poll broadcast queue
        async def poll_broadcast_queue():
            """Poll ResponseManager's broadcast queue and send messages"""
            from app.core.response_queue import response_manager
            broadcast_queue = response_manager.get_broadcast_queue()

            while True:
                try:
                    # Wait for message from queue (with timeout to allow cancellation)
                    try:
                        message_data, proj_id = await asyncio.wait_for(
                            broadcast_queue.get(),
                            timeout=1.0
                        )

                        # Broadcast to project
                        print(f"[Broadcast Queue] Broadcasting {message_data.get('type')} to project {proj_id}", flush=True)
                        await manager.broadcast_to_project(message_data, proj_id)
                        print(f"[Broadcast Queue] ✓ Broadcast completed!", flush=True)

                    except asyncio.TimeoutError:
                        # No message in queue, continue
                        continue

                except asyncio.CancelledError:
                    print(f"[Broadcast Queue] Task cancelled, exiting", flush=True)
                    break
                except Exception as e:
                    print(f"[Broadcast Queue] Error: {e}", flush=True)
                    import traceback
                    traceback.print_exc()

        # Start polling task
        poll_task = asyncio.create_task(poll_broadcast_queue())

        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
            except Exception as e:
                print(f"[WebSocket] Error receiving message: {e}", flush=True)
                raise

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"[WebSocket] JSON decode error: {e}", flush=True)
                continue

            msg_type = message_data.get("type")

            # Skip logging for ping/pong messages (keep-alive)
            if msg_type != "ping":
                print(f"\n[WebSocket] Waiting for message...", flush=True)
                print(f"\n[WebSocket] ===== Raw message received =====", flush=True)
                print(f"[WebSocket] Raw data: {data[:200] if len(data) > 200 else data}", flush=True)
                print(f"[WebSocket] Parsed message_data: {message_data}", flush=True)
                print(f"[WebSocket] Message type: {msg_type}", flush=True)

            if msg_type == "message":
                # Save user message to database
                content = message_data.get("content", "")
                author_type = message_data.get("author_type", "user")

                new_message = MessageModel(
                    project_id=UUID(project_id),
                    author_type=AuthorType(author_type),
                    user_id=UUID(user_id) if author_type == "user" else None,
                    agent_id=None,
                    content=content
                )
                session.add(new_message)
                session.commit()
                session.refresh(new_message)

                # Broadcast to all clients in project
                await manager.broadcast_to_project({
                    "type": "message",
                    "data": {
                        "id": str(new_message.id),
                        "project_id": str(new_message.project_id),
                        "author_type": new_message.author_type,
                        "user_id": str(new_message.user_id) if new_message.user_id else None,
                        "agent_id": str(new_message.agent_id) if new_message.agent_id else None,
                        "content": new_message.content,
                        "created_at": new_message.created_at.isoformat(),
                        "updated_at": new_message.updated_at.isoformat(),
                    }
                }, project_id)

                # Trigger agent processing in background thread (NOT in event loop)
                # This frees main loop to handle WebSocket messages while agent runs
                # Agent will schedule broadcasts back to main loop via run_coroutine_threadsafe
                import concurrent.futures
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

                def run_agent_sync():
                    """Wrapper to run async agent in sync context"""
                    import asyncio
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(
                            trigger_agent_execution_bg(project_id, user_id, new_message.content)
                        )
                        return result
                    finally:
                        loop.close()

                executor.submit(run_agent_sync)

            elif msg_type == "user_answer":
                # User responding to agent question
                print(f"\n[WebSocket] ===== Received user_answer =====", flush=True)
                question_id = message_data.get("question_id")
                answer = message_data.get("answer")
                print(f"[WebSocket] question_id: {question_id}", flush=True)
                print(f"[WebSocket] answer: {answer}", flush=True)

                if question_id and answer is not None:
                    print(f"\n[WebSocket] ===== PROCESSING USER ANSWER =====", flush=True)
                    print(f"[WebSocket] question_id: {question_id}", flush=True)
                    print(f"[WebSocket] answer: {answer}", flush=True)
                    print(f"[WebSocket] answer type: {type(answer)}", flush=True)

                    # Check if this is an approved preview BEFORE submitting to ResponseManager
                    # This ensures approval message is broadcast BEFORE agent continues
                    is_approval = (
                        answer == "approve" or
                        (isinstance(answer, dict) and answer.get("choice") == "approve")
                    )
                    print(f"[WebSocket] is_approval: {is_approval}", flush=True)

                    # If approval, create and broadcast approval message FIRST
                    if is_approval:
                        preview_id = question_id
                        print(f"[WebSocket] Looking for preview_id: {preview_id} in cache...", flush=True)
                        print(f"[WebSocket] Cache keys: {list(pending_previews.keys())}", flush=True)

                        if preview_id in pending_previews:
                            preview_data = pending_previews[preview_id]
                            print(f"[WebSocket] User approved preview {preview_id}, saving to database...", flush=True)

                            # Extract structured data and metadata
                            preview_type = preview_data.get("preview_type", "text")
                            structured_data = None
                            message_summary = "✅ Approved preview"

                            # Map preview type to data field
                            type_field_map = {
                                "product_brief": "brief",
                                "product_vision": "vision",
                                "product_backlog": "backlog",
                                "sprint_plan": "sprint_plan"
                            }

                            if preview_type in type_field_map:
                                field_name = type_field_map[preview_type]
                                structured_data = preview_data.get(field_name)
                                if structured_data:
                                    # Create summary text
                                    if preview_type == "product_brief":
                                        message_summary = f"✅ Product Brief: {structured_data.get('product_name', 'N/A')}"
                                    elif preview_type == "product_vision":
                                        message_summary = f"✅ Product Vision: {structured_data.get('vision_statement', 'N/A')[:100]}..."
                                    elif preview_type == "product_backlog":
                                        total_items = structured_data.get('metadata', {}).get('total_items', 0)
                                        message_summary = f"✅ Product Backlog: {total_items} items"
                                    elif preview_type == "sprint_plan":
                                        total_sprints = structured_data.get('metadata', {}).get('total_sprints', 0)
                                        message_summary = f"✅ Sprint Plan: {total_sprints} sprints"

                            # Create message with structured data
                            approved_message = MessageModel(
                                project_id=UUID(project_id),
                                author_type=AuthorType.AGENT,
                                user_id=None,
                                agent_id=None,
                                content=message_summary,
                                message_type=preview_type,
                                structured_data=structured_data,
                                message_metadata={
                                    "preview_id": preview_id,
                                    "approved_by_user_id": user_id,
                                    "approved_at": datetime.utcnow().isoformat(),
                                    "quality_score": preview_data.get("quality_score"),
                                    "validation_result": preview_data.get("validation_result")
                                }
                            )

                            session.add(approved_message)
                            session.commit()
                            session.refresh(approved_message)

                            # Broadcast the approved message to chat BEFORE unblocking agent
                            await manager.broadcast_to_project({
                                "type": "agent_message",
                                "data": {
                                    "id": str(approved_message.id),
                                    "project_id": str(approved_message.project_id),
                                    "author_type": approved_message.author_type,
                                    "user_id": str(approved_message.user_id) if approved_message.user_id else None,
                                    "agent_id": str(approved_message.agent_id) if approved_message.agent_id else None,
                                    "content": approved_message.content,
                                    "message_type": approved_message.message_type,
                                    "structured_data": approved_message.structured_data,
                                    "metadata": approved_message.message_metadata,
                                    "created_at": approved_message.created_at.isoformat(),
                                    "updated_at": approved_message.updated_at.isoformat(),
                                }
                            }, project_id)

                            # Add small delay to ensure message is displayed before next step
                            await asyncio.sleep(0.5)

                            # Clean up cache
                            del pending_previews[preview_id]
                            print(f"[WebSocket] ✓ Approved preview saved and broadcasted", flush=True)

                            # Auto-trigger next step (run in background to not block WebSocket)
                            # This will trigger Vision → Backlog → Priority agents sequentially
                            print(f"[WebSocket] Checking if need to auto-trigger next agent...", flush=True)
                            asyncio.create_task(
                                trigger_next_step_auto(
                                    project_id=project_id,
                                    user_id=user_id,
                                    approved_message_id=str(approved_message.id),  # Pass ID, not object
                                    websocket_broadcast_fn=manager.broadcast_to_project,
                                    response_manager=response_manager,
                                    event_loop=asyncio.get_event_loop()
                                )
                            )
                            print(f"[WebSocket] ✓ Auto-trigger task created", flush=True)
                        else:
                            print(f"[WebSocket] ⚠ Preview {preview_id} not found in cache", flush=True)

                    # NOW submit response to ResponseManager to unblock agent
                    # This happens AFTER approval message is broadcast
                    print(f"[WebSocket] Submitting to ResponseManager...", flush=True)
                    success = await response_manager.submit_response(
                        project_id,
                        question_id,
                        answer
                    )

                    print(f"[WebSocket] ResponseManager.submit_response returned: {success}", flush=True)
                    if success:
                        print(f"[WebSocket] ✓ User answer submitted successfully: question_id={question_id}", flush=True)
                    else:
                        print(f"[WebSocket] ✗ Question not found in ResponseManager: question_id={question_id}", flush=True)
                else:
                    print(f"[WebSocket] ✗ Invalid user_answer data: question_id={question_id}, answer={answer}", flush=True)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        print(f"\n[WebSocket] ===== CONNECTION DISCONNECTED =====", flush=True)
        print(f"[WebSocket] Project: {project_id}", flush=True)
        print(f"[WebSocket] User: {user_id}", flush=True)
        manager.disconnect(websocket, project_id)
        poll_task.cancel()  # Cancel broadcast polling task
        print(f"[WebSocket] ✓ Cleanup completed", flush=True)
    except Exception as e:
        print(f"\n[WebSocket] ===== ERROR OCCURRED =====", flush=True)
        print(f"[WebSocket] Error: {e}", flush=True)
        print(f"[WebSocket] Project: {project_id}", flush=True)
        import traceback
        traceback.print_exc()
        manager.disconnect(websocket, project_id)
        poll_task.cancel()  # Cancel broadcast polling task
    finally:
        session.close()
        print(f"[WebSocket] Session closed for project {project_id}", flush=True)


async def trigger_agent_execution_bg(project_id: str, user_id: str, user_message: str):
    """
    Background task wrapper for trigger_agent_execution.
    Creates its own database session to avoid session lifecycle issues.
    """
    from app.core.db import engine
    session = Session(engine)

    try:
        await trigger_agent_execution(session, project_id, user_id, user_message)
    finally:
        session.close()


async def trigger_agent_execution(session: Session, project_id: str, user_id: str, user_message: str):
    """
    Trigger agent execution với auto-routing using Team Leader Agent.

    Flow:
    1. TL Agent classifies user intent
    2. Route to appropriate agent (PO/SM/Dev/Tester)
    3. Execute agent and return response

    Special: Detect [TEST_*] commands for direct agent testing with mock data
    """
    import asyncio
    import json
    import re
    from app.agents.team_leader.tl_agent import TeamLeaderAgent
    from app.agents.product_owner.po_agent import POAgent
    from app.agents.product_owner.vision_agent import VisionAgent
    from app.agents.product_owner.gatherer_agent import GathererAgent
    from app.agents.product_owner.backlog_agent import BacklogAgent
    from app.agents.product_owner.priority_agent import PriorityAgent
    import traceback

    # ===== STEP 0: Check for test commands =====
    test_match = re.match(r'\[TEST_(\w+)\]\s*(.*)', user_message, re.DOTALL)
    if test_match:
        test_agent = test_match.group(1).lower()
        test_data_str = test_match.group(2).strip()

        print(f"\n[TEST MODE] Detected test command for: {test_agent}", flush=True)

        # Send typing indicator
        await manager.broadcast_to_project({
            "type": "typing",
            "agent_name": f"{test_agent.capitalize()} Agent (Test Mode)",
            "is_typing": True
        }, project_id)

        try:
            if test_agent == "vision":
                # Parse mock product_brief from message
                product_brief = json.loads(test_data_str)

                print(f"[TEST MODE] Running Vision Agent with mock data", flush=True)

                # Create Vision Agent with WebSocket support
                session_id = f"vision_test_{project_id}_{user_id}"
                vision_agent = VisionAgent(
                    session_id=session_id,
                    user_id=user_id,
                    websocket_broadcast_fn=manager.broadcast_to_project,
                    project_id=project_id,
                    response_manager=response_manager,
                    event_loop=asyncio.get_event_loop()
                )

                # Run Vision Agent (async version for WebSocket support)
                result = await vision_agent.run_async(
                    product_brief=product_brief,
                    thread_id=f"{session_id}_thread"
                )

                # Send completion message
                await manager.broadcast_to_project({
                    "type": "agent_message",
                    "content": "✅ Vision Agent test completed! Check the preview above.",
                    "agent_name": "Vision Agent"
                }, project_id)

                # Save to database
                agent_message = MessageModel(
                    project_id=UUID(project_id),
                    author_type=AuthorType.AGENT,
                    user_id=None,
                    agent_id=None,
                    content="[Test Mode] Vision Agent executed with mock data. Product Vision generated."
                )
                session.add(agent_message)
                session.commit()

                return

            elif test_agent == "gatherer":
                print(f"[TEST MODE] Running Gatherer Agent", flush=True)

                # Create Gatherer Agent with WebSocket support
                session_id = f"gatherer_test_{project_id}_{user_id}"
                gatherer_agent = GathererAgent(
                    session_id=session_id,
                    user_id=user_id,
                    websocket_broadcast_fn=manager.broadcast_to_project,
                    project_id=project_id,
                    response_manager=response_manager,
                    event_loop=asyncio.get_event_loop()
                )

                # Run Gatherer Agent with test input
                result = gatherer_agent.run(
                    initial_context=test_data_str or "Create a task management application",
                    thread_id=f"{session_id}_thread"
                )

                await manager.broadcast_to_project({
                    "type": "agent_message",
                    "content": "✅ Gatherer Agent test completed!",
                    "agent_name": "Gatherer Agent"
                }, project_id)

                return

            elif test_agent == "backlog":
                # Parse mock product_vision from message
                product_vision = json.loads(test_data_str)

                print(f"[TEST MODE] Running Backlog Agent with mock data", flush=True)

                # Create Backlog Agent with WebSocket support
                session_id = f"backlog_test_{project_id}_{user_id}"
                backlog_agent = BacklogAgent(
                    session_id=session_id,
                    user_id=user_id,
                    websocket_broadcast_fn=manager.broadcast_to_project,
                    project_id=project_id,
                    response_manager=response_manager,
                    event_loop=asyncio.get_event_loop()
                )

                # Run Backlog Agent
                result = backlog_agent.run(
                    product_vision=product_vision,
                    thread_id=f"{session_id}_thread"
                )

                # Send completion message
                await manager.broadcast_to_project({
                    "type": "agent_message",
                    "content": "✅ Backlog Agent test completed! Check the preview above.",
                    "agent_name": "Backlog Agent"
                }, project_id)

                # Save to database
                agent_message = MessageModel(
                    project_id=UUID(project_id),
                    author_type=AuthorType.AGENT,
                    user_id=None,
                    agent_id=None,
                    content="[Test Mode] Backlog Agent executed with mock data. Product Backlog generated."
                )
                session.add(agent_message)
                session.commit()

                return

            elif test_agent == "priority":
                # Parse mock product_backlog from message
                product_backlog = json.loads(test_data_str)

                print(f"[TEST MODE] Running Priority Agent with mock data", flush=True)

                # Create Priority Agent with WebSocket support
                session_id = f"priority_test_{project_id}_{user_id}"
                priority_agent = PriorityAgent(
                    session_id=session_id,
                    user_id=user_id,
                    websocket_broadcast_fn=manager.broadcast_to_project,
                    project_id=project_id,
                    response_manager=response_manager,
                    event_loop=asyncio.get_event_loop()
                )

                # Run Priority Agent
                result = priority_agent.run(
                    product_backlog=product_backlog,
                    thread_id=f"{session_id}_thread"
                )

                # Send completion message
                await manager.broadcast_to_project({
                    "type": "agent_message",
                    "content": "✅ Priority Agent test completed! Check the preview above.",
                    "agent_name": "Priority Agent"
                }, project_id)

                # Save to database
                agent_message = MessageModel(
                    project_id=UUID(project_id),
                    author_type=AuthorType.AGENT,
                    user_id=None,
                    agent_id=None,
                    content="[Test Mode] Priority Agent executed with mock data. Sprint Plan generated."
                )
                session.add(agent_message)
                session.commit()

                return

            else:
                # Unknown test agent
                await manager.broadcast_to_project({
                    "type": "agent_message",
                    "content": f"❌ Unknown test agent: {test_agent}",
                    "agent_name": "System"
                }, project_id)
                return

        except Exception as e:
            print(f"[TEST MODE] Error: {e}", flush=True)
            traceback.print_exc()
            await manager.broadcast_to_project({
                "type": "agent_message",
                "content": f"❌ Test failed: {str(e)}",
                "agent_name": "System"
            }, project_id)
            return

    # ===== STEP 1: Classify với TL Agent (normal flow) =====
    try:
        tl_session_id = f"tl_agent_{project_id}"
        tl_agent = TeamLeaderAgent(session_id=tl_session_id, user_id=user_id)

        # Get project context
        project_context = {}
        try:
            project = session.get(Project, UUID(project_id))
            if project:
                # Có thể thêm project_phase nếu model có field này
                # project_context["project_phase"] = project.phase
                pass
        except:
            pass

        # Classify intent
        routing_result = tl_agent.classify(user_message, project_context)
        agent_type = routing_result.agent

        # Broadcast routing decision (optional, for transparency)
        await manager.broadcast_to_project({
            "type": "routing",
            "agent_selected": agent_type,
            "confidence": routing_result.confidence,
            "user_intent": routing_result.user_intent,
            "reasoning": routing_result.reasoning
        }, project_id)

    except Exception as e:
        print(f"[TL Agent] Routing error: {e}, defaulting to PO")
        agent_type = "po"  # Fallback to PO on error

    # STEP 2: Get agent name for typing indicator
    agent_names = {
        "po": "PO Agent",
        "scrum_master": "Scrum Master Agent",
        "developer": "Developer Agent",
        "tester": "Tester Agent"
    }
    agent_display_name = agent_names.get(agent_type, "PO Agent")

    # Send typing indicator
    await manager.broadcast_to_project({
        "type": "typing",
        "agent_name": agent_display_name,
        "is_typing": True
    }, project_id)

    try:
        # STEP 3: Create appropriate agent instance
        # For PO agent type, only run Gatherer Agent first (step-by-step workflow)
        # Auto-trigger will handle Vision → Backlog → Priority after approval
        if agent_type == "po":
            print(f"\n[Agent Execution] Using step-by-step workflow: Starting with Gatherer Agent only", flush=True)

            # Send agent_step to show progress indicator
            await manager.broadcast_to_project({
                "type": "agent_step",
                "step": "started",
                "agent": "Gatherer Agent",
                "message": "🔄 Đang thu thập thông tin sản phẩm..."
            }, project_id)

            # Create Gatherer Agent with WebSocket support
            gatherer_agent = GathererAgent(
                session_id=f"gatherer_{project_id}_{user_id}",
                user_id=user_id,
                websocket_broadcast_fn=manager.broadcast_to_project,
                project_id=project_id,
                response_manager=response_manager,
                event_loop=asyncio.get_event_loop()
            )

            # Run only Gatherer Agent (will show preview and wait for approval)
            result = await gatherer_agent.run_async(
                initial_context=user_message,
                thread_id=f"gatherer_{project_id}_thread"
            )

            print(f"[Agent Execution] Gatherer Agent completed. Waiting for approval before next step.", flush=True)
        else:
            # TODO: Implement other agents (Scrum Master, Developer, Tester)
            print(f"[WARNING] Agent type '{agent_type}' not implemented yet")
            agent_display_name = "System"

            await manager.broadcast_to_project({
                "type": "agent_message",
                "content": f"⚠️ Agent type '{agent_type}' is not implemented yet. Please contact support.",
                "agent_name": "System"
            }, project_id)
            return

        # Gatherer Agent completed successfully
        # Wait for user to approve preview, then auto-trigger will run next agent
        # Keep progress indicator and typing indicator active (don't send typing stopped)
        print(f"[Agent Execution] ✓ Gatherer Agent workflow initiated successfully", flush=True)

    except Exception as e:
        error_msg = f"❌ Agent execution failed: {str(e)}"
        print(f"Error: {error_msg}\n{traceback.format_exc()}")
        
        # Send typing stopped
        await manager.broadcast_to_project({
            "type": "typing",
            "agent_name": "PO Agent",
            "is_typing": False
        }, project_id)
        
        # Save error message
        error_message = MessageModel(
            project_id=UUID(project_id),
            author_type=AuthorType.SYSTEM,
            user_id=None,
            agent_id=None,
            content=error_msg
        )
        session.add(error_message)
        session.commit()
        session.refresh(error_message)
        
        # Broadcast error
        await manager.broadcast_to_project({
            "type": "agent_message",
            "data": {
                "id": str(error_message.id),
                "project_id": str(error_message.project_id),
                "author_type": error_message.author_type,
                "user_id": None,
                "agent_id": None,
                "content": error_message.content,
                "created_at": error_message.created_at.isoformat(),
                "updated_at": error_message.updated_at.isoformat(),
            }
        }, project_id)
