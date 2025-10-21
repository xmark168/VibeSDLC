from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, func

from app.api.deps import CurrentUser, SessionDep
from app.models import Project, Role, User
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectPublic,
    ProjectsPublic,
)

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/", response_model=ProjectsPublic)
def list_projects(
    session: SessionDep,
    current_user: CurrentUser,
    owner_id: Optional[UUID] = Query(None),
    code: Optional[str] = Query(None, description="Tìm theo code"),
    name: Optional[str] = Query(None, description="Tìm theo name"),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    stmt = select(Project)
    if owner_id:
        stmt = stmt.where(Project.owner_id == owner_id)
    if code:
        stmt = stmt.where(Project.code.ilike(f"%{code}%"))
    if name:
        stmt = stmt.where(Project.name.ilike(f"%{name}%"))

    count_stmt = select(func.count()).select_from(Project)
    if owner_id:
        count_stmt = count_stmt.where(Project.owner_id == owner_id)
    if code:
        count_stmt = count_stmt.where(Project.code.ilike(f"%{code}%"))
    if name:
        count_stmt = count_stmt.where(Project.name.ilike(f"%{name}%"))

    count = session.exec(count_stmt).one()
    rows = session.exec(stmt.offset(skip).limit(limit)).all()
    return ProjectsPublic(data=rows, count=count)

@router.get("/{project_id}", response_model=ProjectPublic)
def get_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    # Validate owner tồn tại
    owner = session.get(User, project_in.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    dup_stmt = select(Project).where(
        Project.owner_id == project_in.owner_id,
        Project.code == project_in.code,
    )
    if session.exec(dup_stmt).first():
        raise HTTPException(status_code=400, detail="Project code already exists for this owner")

    obj = Project(**project_in.model_dump())
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj

@router.patch("/{project_id}", response_model=ProjectPublic)
def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Chỉ admin hoặc owner được sửa
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    # Optional: nếu update code, kiểm tra trùng
    update_data = project_in.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"] != project.code:
        dup_stmt = select(Project).where(
            Project.owner_id == project.owner_id,
            Project.code == update_data["code"],
            Project.id != project.id,
        )
        if session.exec(dup_stmt).first():
            raise HTTPException(status_code=400, detail="Project code already exists")

    project.sqlmodel_update(update_data)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Chỉ admin hoặc owner được xóa
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    session.delete(project)
    session.commit()
    return None