from typing import Any, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, SessionDep
from app.models import Project, Message as MessageModel, AuthorType
from app.schemas import Message

router = APIRouter(prefix="/agent", tags=["agent-execution"])


class AgentExecutionRequest(BaseModel):
    project_id: UUID
    user_input: str
    agent_type: str = "po_agent"  # Default to PO Agent


class AgentExecutionResponse(BaseModel):
    execution_id: str
    status: str
    message: str


async def execute_agent_background(
    project_id: UUID,
    user_input: str,
    user_id: UUID,
    session: SessionDep,
    agent_type: str = "po_agent"
):
    """
    Execute agent in background and save responses to messages
    """
    from app.agents.product_owner.po_agent import POAgent
    import traceback
    
    try:
        # Create agent instance
        session_id = f"po_agent_{project_id}_{user_id}"
        agent = POAgent(session_id=session_id, user_id=str(user_id))
        
        # Run agent
        result = agent.run(user_input=user_input)
        
        # Extract response from result
        response_content = ""
        if isinstance(result, dict):
            # Try to get messages from result
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, dict):
                    response_content = last_message.get("content", "")
                else:
                    response_content = str(last_message)
            
            # If no messages, try to get other fields
            if not response_content:
                # Get brief, vision, backlog, or sprint_plan
                for key in ["sprint_plan", "backlog", "vision", "brief"]:
                    if key in result and result[key]:
                        response_content = f"Generated {key}:\n{result[key]}"
                        break
        
        if not response_content:
            response_content = "Agent execution completed successfully."
        
        # Save agent response to database
        agent_message = MessageModel(
            project_id=project_id,
            author_type=AuthorType.AGENT,
            user_id=None,
            agent_id=None,  # TODO: Link to specific agent
            content=response_content
        )
        session.add(agent_message)
        session.commit()
        
        # Broadcast via WebSocket if available
        from app.api.routes.chat_ws import manager
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
        }, str(project_id))
        
    except Exception as e:
        error_msg = f"Agent execution failed: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        # Save error message
        error_message = MessageModel(
            project_id=project_id,
            author_type=AuthorType.SYSTEM,
            user_id=None,
            agent_id=None,
            content=f"❌ Error: {str(e)}"
        )
        session.add(error_message)
        session.commit()
        
        # Broadcast error
        from app.api.routes.chat_ws import manager
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
        }, str(project_id))


@router.post("/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    request: AgentExecutionRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Execute an agent with user input.
    Agent will run in background and send responses via WebSocket.
    """
    # Validate project
    project = session.get(Project, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Generate execution ID
    execution_id = f"{request.agent_type}_{request.project_id}_{current_user.id}"
    
    # Add background task
    background_tasks.add_task(
        execute_agent_background,
        project_id=request.project_id,
        user_input=request.user_input,
        user_id=current_user.id,
        session=session,
        agent_type=request.agent_type
    )
    
    return AgentExecutionResponse(
        execution_id=execution_id,
        status="started",
        message="Agent execution started. You will receive responses via WebSocket."
    )


@router.post("/execute-sync", response_model=dict)
def execute_agent_sync(
    request: AgentExecutionRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Execute an agent synchronously (blocking).
    Use this for testing or when you need immediate response.
    """
    from app.agents.product_owner.po_agent import POAgent
    
    # Validate project
    project = session.get(Project, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        # Create agent instance
        session_id = f"po_agent_{request.project_id}_{current_user.id}"
        agent = POAgent(session_id=session_id, user_id=str(current_user.id))
        
        # Run agent
        result = agent.run(user_input=request.user_input)
        
        return {
            "status": "completed",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )