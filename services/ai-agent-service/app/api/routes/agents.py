from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select, func

from app.api.deps import CurrentUser, SessionDep
from app.models import Agent as AgentModel, Role
from app.schemas import (
    AgentCreate,
    AgentUpdate,
    AgentPublic,
    AgentsPublic,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=AgentsPublic)
def list_agents(
    session: SessionDep,
    current_user: CurrentUser,
    name: Optional[str] = Query(None),
    agent_type: Optional[str] = Query(None),
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
    current_user: CurrentUser,
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

