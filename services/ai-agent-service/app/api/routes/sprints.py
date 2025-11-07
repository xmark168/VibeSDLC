from typing import Any, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, func

from app.api.deps import CurrentUser, SessionDep
from app.models import Sprint, Project, Role
from app.schemas import (
    SprintCreate,
    SprintUpdate,
    SprintPublic,
    SprintsPublic,
)

router = APIRouter(prefix="/sprints", tags=["sprints"])

@router.get("/", response_model=SprintsPublic)
def list_sprints(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    status: Optional[str] = Query(None, description="Filter by status"),
    name: Optional[str] = Query(None, description="Search by name"),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Lấy danh sách sprints với filter"""
    stmt = select(Sprint)

    if project_id:
        stmt = stmt.where(Sprint.project_id == project_id)
    if status:
        stmt = stmt.where(Sprint.status == status)
    if name:
        stmt = stmt.where(Sprint.name.like(f"%{name}%"))

    stmt = stmt.order_by(Sprint.project_id, Sprint.number)

    count_stmt = select(func.count()).select_from(Sprint)
    if project_id:
        count_stmt = count_stmt.where(Sprint.project_id == project_id)
    if status:
        count_stmt = count_stmt.where(Sprint.status == status)
    if name:
        count_stmt = count_stmt.where(Sprint.name.ilike(f"%{name}%"))

    count = session.exec(count_stmt).one()
    rows = session.exec(stmt.offset(skip).limit(limit)).all()

    return SprintsPublic(data=rows, count=count)

@router.get("/{sprint_id}", response_model=SprintPublic)
def get_sprint(
    sprint_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Lấy chi tiết một sprint"""
    sprint = session.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return sprint

@router.post("/", response_model=SprintPublic, status_code=status.HTTP_201_CREATED)
def create_sprint(
    sprint_in: SprintCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Tạo mới một sprint"""
    project = session.get(Project, sprint_in.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allow")

    dup_stmt = select(Sprint).where(
        Sprint.project_id == sprint_in.project_id,
        Sprint.number == sprint_in.number,
    )
    if session.exec(dup_stmt).first():
        raise HTTPException(
            status_code=400,
            detail=f"Sprint number {sprint_in.number} already exists in this project"
        )

    if sprint_in.start_date >= sprint_in.end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before end date"
        )
    
    obj = Sprint(**sprint_in.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj

@router.patch("/{sprint_id}", response_model=SprintPublic)
def update_sprint(
    sprint_id: UUID,
    sprint_in: SprintUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Cập nhật một sprint"""
    sprint = session.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    
    # Permission: chỉ admin hoặc project owner được sửa
    project = session.get(Project, sprint.project_id)
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    update_data = sprint_in.model_dump(exclude_unset=True)

    if "number" in update_data and update_data["number"] != sprint.number:
        dup_stmt = select(Sprint).where(
            Sprint.project_id == sprint.project_id,
            Sprint.number == update_data["number"],
            Sprint.id != sprint_id
        )
        if session.exec(dup_stmt).first():
            raise HTTPException(
                status_code=400,
                detail=f"Sprint number {update_data['number']} already exists in this project"
            )
    
    start_date = update_data.get("start_date", sprint.start_date)
    end_date = update_data.get("end_date", sprint.end_date)

    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    sprint.sqlmodel_update(update_data)
    session.add(sprint)
    session.commit()
    session.refresh(sprint)
    return sprint

@router.delete("/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sprint(
    sprint_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    """Xóa sprint"""
    sprint = session.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    
    # Permission: chỉ admin hoặc project owner được xóa
    project = session.get(Project, sprint.project_id)
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    session.delete(sprint)
    session.commit()
    return None

@router.get("/project/{project_id}/active", response_model=SprintPublic)
def get_active_sprint(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Lấy sprint đang active hoặc planned của project.

    Priority:
    1. Active sprint (nếu có)
    2. Planned sprint (nếu không có Active)
    3. Sprint mới nhất (nếu không có Active hoặc Planned)
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Try to get Active sprint first
    stmt = select(Sprint).where(
        Sprint.project_id == project_id,
        Sprint.status == "Active"
    ).order_by(Sprint.number.desc())

    sprint = session.exec(stmt).first()

    # If no Active sprint, try Planned
    if not sprint:
        stmt = select(Sprint).where(
            Sprint.project_id == project_id,
            Sprint.status == "Planned"
        ).order_by(Sprint.number.desc())
        sprint = session.exec(stmt).first()

    # If still no sprint, get the latest one regardless of status
    if not sprint:
        stmt = select(Sprint).where(
            Sprint.project_id == project_id
        ).order_by(Sprint.number.desc())
        sprint = session.exec(stmt).first()

    if not sprint:
        raise HTTPException(status_code=404, detail="No sprint found for this project")

    return sprint