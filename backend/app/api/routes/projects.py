"""Project management endpoints."""

import logging
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import Project, Role, Agent, AgentStatus
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectPublic,
    ProjectsPublic,
)
from app.agents.core.name_generator import generate_agent_name, get_display_name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

# Default role types for new projects
DEFAULT_AGENT_ROLES = ["team_leader", "business_analyst", "developer", "tester"]


@router.get("/", response_model=ProjectsPublic)
def list_projects(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> ProjectsPublic:
    """
    Get all projects owned by the current user, or all projects if admin.

    Args:
        session: Database session
        current_user: Current authenticated user
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return

    Returns:
        ProjectsPublic: List of projects with total count
    """
    if current_user.role == Role.ADMIN:
        projects, total_count = crud.project.get_projects(
            session=session,
            skip=skip,
            limit=limit,
        )
    else:
        projects, total_count = crud.project.get_projects_by_owner(
            session=session,
            owner_id=current_user.id,
            skip=skip,
            limit=limit,
        )

    return ProjectsPublic(
        data=[ProjectPublic.model_validate(p) for p in projects],
        count=total_count,
    )


@router.get("/{project_id}", response_model=ProjectPublic)
def get_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> ProjectPublic:
    """
    Get a specific project by ID.

    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user

    Returns:
        ProjectPublic: Project details

    Raises:
        HTTPException: If project not found or user lacks access
    """
    project = crud.project.get_project(session=session, project_id=project_id)

    if not project:
        logger.warning(f"Project {project_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if user owns the project or is admin
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to access project {project_id} "
            f"owned by {project.owner_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    return ProjectPublic.model_validate(project)


@router.post("/", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ProjectPublic:
    """
    Create a new project.

    The project code is automatically generated in format PRJ-001, PRJ-002, etc.
    Default agents (1 per role type) are automatically created for the project.

    Uses a single transaction - if agent creation fails, the project is rolled back.

    Args:
        project_in: Project creation schema
        session: Database session
        current_user: Current authenticated user

    Returns:
        ProjectPublic: Created project details

    Raises:
        HTTPException: If project or agent creation fails
    """
    logger.info(f"Creating new project '{project_in.name}' for user {current_user.id}")

    try:
        # Create project without committing (uses flush to get ID)
        project = crud.project.create_project_no_commit(
            session=session,
            project_in=project_in,
            owner_id=current_user.id,
        )

        # Auto-generate project_path: projects/{project_id}
        project.project_path = f"projects/{project.id}"

        # Create the project folder if it doesn't exist
        project_folder = Path(project.project_path)
        project_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created project folder: {project_folder}")

        # Auto-create default agents for the project (1 per role type)
        created_agents = []
        for role_type in DEFAULT_AGENT_ROLES:
            human_name = generate_agent_name(role_type, existing_names=[])
            display_name = get_display_name(human_name, role_type)

            agent = Agent(
                project_id=project.id,
                name=display_name,
                human_name=human_name,
                role_type=role_type,
                agent_type=role_type,
                status=AgentStatus.idle,
            )
            session.add(agent)
            created_agents.append(agent)

        # Commit both project and agents in a single transaction
        session.commit()
        session.refresh(project)

        logger.info(
            f"Project created successfully: {project.code} (ID: {project.id}) "
            f"with {len(created_agents)} agents"
        )
        return ProjectPublic.model_validate(project)

    except Exception as e:
        # Rollback the entire transaction (project + agents)
        session.rollback()
        logger.error(f"Failed to create project '{project_in.name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@router.put("/{project_id}", response_model=ProjectPublic)
def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ProjectPublic:
    """
    Update a project.

    Args:
        project_id: UUID of the project to update
        project_in: Project update schema
        session: Database session
        current_user: Current authenticated user

    Returns:
        ProjectPublic: Updated project details

    Raises:
        HTTPException: If project not found or user lacks access
    """
    project = crud.project.get_project(session=session, project_id=project_id)

    if not project:
        logger.warning(f"Project {project_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if user owns the project or is admin
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to update project {project_id} "
            f"owned by {project.owner_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    logger.info(f"Updating project {project.code} (ID: {project_id})")

    updated_project = crud.project.update_project(
        session=session,
        db_project=project,
        project_in=project_in,
    )

    return ProjectPublic.model_validate(updated_project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Delete a project.

    Args:
        project_id: UUID of the project to delete
        session: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If project not found or user lacks access
    """
    project = crud.project.get_project(session=session, project_id=project_id)

    if not project:
        logger.warning(f"Project {project_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if user owns the project or is admin
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        logger.warning(
            f"User {current_user.id} attempted to delete project {project_id} "
            f"owned by {project.owner_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    logger.info(f"Deleting project {project.code} (ID: {project_id})")
    crud.project.delete_project(session=session, project_id=project_id)
