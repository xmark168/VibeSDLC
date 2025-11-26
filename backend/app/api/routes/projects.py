"""Project management endpoints."""

import logging
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.services import ProjectService
from app.models import Project, Role, Agent, AgentStatus
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectPublic,
    ProjectsPublic,
)
from app.services.persona_service import PersonaService

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
    project_service = ProjectService(session)
    if current_user.role == Role.ADMIN:
        projects, total_count = project_service.get_all(
            skip=skip,
            limit=limit,
        )
    else:
        projects, total_count = project_service.get_by_owner(
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
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

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
        project_service = ProjectService(session)
        project = project_service.create_no_commit(
            project_in=project_in,
            owner_id=current_user.id,
        )

        # Auto-generate project_path: projects/{project_id}
        project.project_path = f"projects/{project.id}"

        # Create the project folder if it doesn't exist
        project_folder = Path(project.project_path)
        project_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created project folder: {project_folder}")

        # Auto-create default agents for the project with diverse personas
        persona_service = PersonaService(session)
        agent_service = AgentService(session)
        created_agents = []
        used_persona_ids = []
        
        for role_type in DEFAULT_AGENT_ROLES:
            # Get random persona for this role (avoid duplicates in same project)
            persona = persona_service.get_random_persona_for_role(
                role_type=role_type,
                exclude_ids=used_persona_ids
            )
            
            if not persona:
                # No fallback - fail fast if personas not seeded
                session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"No persona templates found for role '{role_type}'. Please seed persona templates first by running: python app/db/seed_personas_script.py"
                )
            
            # Create agent from persona template
            agent = agent_service.create_from_template(
                project_id=project.id,
                persona_template=persona
            )
            used_persona_ids.append(persona.id)
            created_agents.append(agent)
            
            logger.info(
                f"✓ Created {agent.human_name} ({role_type}) "
                f"with persona: {persona.communication_style}, traits: {', '.join(persona.personality_traits[:2]) if persona.personality_traits else 'default'}"
            )

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
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

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

    project_service = ProjectService(session)
    updated_project = project_service.update(
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
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

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
    project_service = ProjectService(session)
    project_service.delete(project_id)
