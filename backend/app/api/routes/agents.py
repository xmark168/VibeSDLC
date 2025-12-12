from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Agent as AgentModel
from app.models import (
    AgentExecution,
    AgentExecutionStatus,
    AuthorType,
    Message,
    Role,
)
from app.schemas import (
    AgentActivityResponse,
    AgentCreate,
    AgentPublic,
    AgentsPublic,
    AgentUpdate,
    CurrentTaskInfo,
    RecentActivity,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=AgentsPublic)
def list_agents(
    session: SessionDep,
    current_user: CurrentUser,
    name: str | None = Query(None),
    agent_type: str | None = Query(None),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    stmt = select(AgentModel)
    if name:
        stmt = stmt.where(AgentModel.name.ilike(f"%{name}%"))
    if agent_type:
        stmt = stmt.where(AgentModel.agent_type == agent_type)

    count_stmt = select(func.count()).select_from(AgentModel)
    if name:
        count_stmt = count_stmt.where(AgentModel.name.ilike(f"%{name}%"))
    if agent_type:
        count_stmt = count_stmt.where(AgentModel.agent_type == agent_type)

    count = session.exec(count_stmt).one()
    rows = session.exec(stmt.offset(skip).limit(limit)).all()
    return AgentsPublic(data=rows, count=count)

@router.get("/{agent_id}", response_model=AgentPublic)
def get_agent(
    agent_id: UUID,
    session: SessionDep,
    _ : CurrentUser,
) -> Any:
    obj = session.get(AgentModel, agent_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent not found")
    return obj


@router.post("/", response_model=AgentPublic, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_in: AgentCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    # Only admin can create agents (optional policy)
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not allowed")

    obj = AgentModel(**agent_in.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


@router.patch("/{agent_id}", response_model=AgentPublic)
def update_agent(
    agent_id: UUID,
    agent_in: AgentUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not allowed")

    obj = session.get(AgentModel, agent_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = agent_in.model_dump(exclude_unset=True)
    obj.sqlmodel_update(update_data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Not allowed")

    obj = session.get(AgentModel, agent_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Agent not found")

    session.delete(obj)
    session.commit()
    return None


@router.get("/{agent_id}/activity", response_model=AgentActivityResponse)
def get_agent_activity(
    agent_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = Query(default=5, le=20),
) -> Any:
    """
    Get agent activity for popup display.
    
    Returns:
    - Agent basic info (name, role, status)
    - Status message and skills from persona_metadata
    - Current running task (if any)
    - Recent activities (messages sent by this agent)
    """
    agent = session.get(AgentModel, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Extract data from persona_metadata
    # Structure: {"description": "...", "strengths": ["...", "..."]}
    persona_metadata = agent.persona_metadata or {}

    # Get skills from "strengths" field
    skills = persona_metadata.get("strengths", [])

    # Default skills based on role if not set
    if not skills:
        default_skills = {
            "team_leader": ["Kanban", "Agile", "Planning", "Coordination"],
            "business_analyst": ["PRD", "User Stories", "Requirements", "BPMN"],
            "developer": ["Code", "Architecture", "Testing", "Debug"],
            "tester": ["Test Plans", "QA", "Automation", "Bug Reports"],
        }
        skills = default_skills.get(agent.role_type, [])

    # Get status_message from "description" field
    status_message = persona_metadata.get("description")

    # Get current running task
    current_task = None
    running_execution = session.exec(
        select(AgentExecution)
        .where(AgentExecution.agent_name == agent.human_name)
        .where(AgentExecution.project_id == agent.project_id)
        .where(AgentExecution.status == AgentExecutionStatus.RUNNING)
        .order_by(col(AgentExecution.started_at).desc())
        .limit(1)
    ).first()

    if running_execution:
        # Extract task name from result or metadata
        task_name = "Đang xử lý..."
        if running_execution.result:
            task_name = running_execution.result.get("task_name", task_name)
        elif running_execution.extra_metadata:
            task_name = running_execution.extra_metadata.get("task_name", task_name)

        current_task = CurrentTaskInfo(
            id=running_execution.id,
            name=task_name,
            status=running_execution.status.value,
            progress=running_execution.extra_metadata.get("progress") if running_execution.extra_metadata else None,
            started_at=running_execution.started_at or running_execution.created_at,
        )

    # Get recent activities (messages from this agent)
    recent_messages = session.exec(
        select(Message)
        .where(Message.agent_id == agent_id)
        .where(Message.author_type == AuthorType.AGENT)
        .where(Message.message_type != "activity")  # Exclude activity logs
        .order_by(col(Message.created_at).desc())
        .limit(limit)
    ).all()

    recent_activities = []
    for msg in recent_messages:
        # Determine activity type and content
        activity_type = "message"
        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content

        if msg.message_type == "agent_question":
            activity_type = "question"
            content = "Đặt câu hỏi: " + content
        elif msg.message_type == "artifact_created":
            activity_type = "artifact"
            artifact_title = msg.structured_data.get("title", "Artifact") if msg.structured_data else "Artifact"
            content = f"Tạo {artifact_title}"
        elif msg.structured_data:
            msg_type = msg.structured_data.get("message_type", "")
            if msg_type == "prd_created":
                activity_type = "prd"
                content = "Tạo PRD document"
            elif msg_type == "stories_created":
                activity_type = "stories"
                content = "Tạo User Stories"

        recent_activities.append(RecentActivity(
            id=msg.id,
            activity_type=activity_type,
            content=content,
            created_at=msg.created_at,
        ))

    return AgentActivityResponse(
        agent_id=agent.id,
        human_name=agent.human_name,
        role_type=agent.role_type,
        status=agent.status.value,
        status_message=status_message,
        skills=skills,
        current_task=current_task,
        recent_activities=recent_activities,
    )

