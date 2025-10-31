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
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_project(self, message: dict, project_id: str):
        """Broadcast message to all connections in a project"""
        if project_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn, project_id)


manager = ConnectionManager()


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
                print(f"\n[WebSocket] Waiting for message...", flush=True)
                data = await websocket.receive_text()
                print(f"\n[WebSocket] ===== Raw message received =====", flush=True)
                print(f"[WebSocket] Raw data: {data[:200] if len(data) > 200 else data}", flush=True)
            except Exception as e:
                print(f"[WebSocket] Error receiving message: {e}", flush=True)
                raise

            try:
                message_data = json.loads(data)
                print(f"[WebSocket] Parsed message_data: {message_data}", flush=True)
            except json.JSONDecodeError as e:
                print(f"[WebSocket] JSON decode error: {e}", flush=True)
                continue

            msg_type = message_data.get("type")
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
                    print(f"[WebSocket] Submitting to ResponseManager...", flush=True)
                    # Submit response to ResponseManager
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
        manager.disconnect(websocket, project_id)
        poll_task.cancel()  # Cancel broadcast polling task
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, project_id)
        poll_task.cancel()  # Cancel broadcast polling task
    finally:
        session.close()


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
    """
    import asyncio
    from app.agents.team_leader.tl_agent import TeamLeaderAgent
    from app.agents.product_owner.po_agent import POAgent
    import traceback

    # STEP 1: Classify với TL Agent
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
        # Agent factory pattern
        agent_factory = {
            "po": lambda: POAgent(
                session_id=f"po_agent_{project_id}_{user_id}",
                user_id=user_id
            ),
            # TODO: Implement other agents
            # "scrum_master": lambda: ScrumMasterAgent(...),
            # "developer": lambda: DeveloperAgent(...),
            # "tester": lambda: TesterAgent(...),
        }

        # Get agent or fallback to PO
        if agent_type in agent_factory:
            agent = agent_factory[agent_type]()
        else:
            print(f"[WARNING] Agent type '{agent_type}' not implemented yet, using PO Agent")
            agent = agent_factory["po"]()
            agent_display_name = "PO Agent"

        # Run agent with WebSocket streaming
        result = await agent.run_with_streaming(
            user_input=user_message,
            websocket_broadcast_fn=manager.broadcast_to_project,
            project_id=project_id,
            response_manager=response_manager
        )

        # Extract response from result
        response_content = ""
        if isinstance(result, dict):
            # Try to get messages from result
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, dict):
                    response_content = last_message.get("content", "")
                elif hasattr(last_message, 'content'):
                    # LangChain message object
                    response_content = last_message.content
                else:
                    # Convert to string and try to extract content
                    msg_str = str(last_message)
                    if "content=" in msg_str:
                        # Extract content from string representation
                        import re
                        match = re.search(r"content='([^']*)'", msg_str)
                        if match:
                            response_content = match.group(1)
                        else:
                            response_content = msg_str
                    else:
                        response_content = msg_str
            
            # If no messages, try to get other fields
            if not response_content:
                for key in ["sprint_plan", "backlog", "vision", "brief"]:
                    if key in result and result[key]:
                        response_content = f"✅ Generated {key}:\n\n{result[key]}"
                        break
        
        if not response_content:
            response_content = "✅ Agent execution completed successfully."

        # Clean up escaped newlines
        response_content = response_content.replace('\\n', '\n')

        # Save agent response to database
        agent_message = MessageModel(
            project_id=UUID(project_id),
            author_type=AuthorType.AGENT,
            user_id=None,
            agent_id=None,
            content=response_content
        )
        session.add(agent_message)
        session.commit()
        session.refresh(agent_message)

        # Send typing stopped
        await manager.broadcast_to_project({
            "type": "typing",
            "agent_name": "PO Agent",
            "is_typing": False
        }, project_id)

        # Broadcast agent message
        await manager.broadcast_to_project({
            "type": "agent_message",
            "data": {
                "id": str(agent_message.id),
                "project_id": str(agent_message.project_id),
                "author_type": agent_message.author_type,
                "user_id": str(agent_message.user_id) if agent_message.user_id else None,
                "agent_id": str(agent_message.agent_id) if agent_message.agent_id else None,
                "content": agent_message.content,
                "created_at": agent_message.created_at.isoformat(),
                "updated_at": agent_message.updated_at.isoformat(),
            }
        }, project_id)

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
