"""Project management endpoints."""

import logging
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.services import ProjectService
from app.services.agent_service import AgentService
from app.models import Project, Role, Agent, AgentStatus
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectPublic,
    ProjectsPublic,
)
from app.services.persona_service import PersonaService
from app.utils.seed_techstacks import copy_boilerplate_to_project, init_git_repo

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
async def create_project(
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

        # Copy boilerplate based on tech_stack
        tech_stack = project.tech_stack or "nodejs-react"
        backend_root = Path(__file__).resolve().parent.parent.parent.parent
        project_path = backend_root / "projects" / str(project.id)
        
        if copy_boilerplate_to_project(tech_stack, project_path):
            init_git_repo(project_path)
            logger.info(f"Copied boilerplate '{tech_stack}' to {project_path}")
        else:
            # Fallback: just create empty folder
            project_path.mkdir(parents=True, exist_ok=True)
            logger.warning(f"No boilerplate for '{tech_stack}', created empty folder")

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
        
        # Auto-spawn agents after project creation
        from app.api.routes.agent_management import get_available_pool, get_role_class_map
        
        role_class_map = get_role_class_map()
        spawned_count = 0
        
        for agent in created_agents:
            # Get pool for this agent's role (role-specific > universal > any)
            pool_manager = get_available_pool(role_type=agent.role_type)
            if not pool_manager:
                logger.warning(f"No pool available for {agent.role_type}, skipping spawn")
                continue
            
            role_class = role_class_map.get(agent.role_type)
            if not role_class:
                logger.warning(f"No role class found for {agent.role_type}, skipping spawn")
                continue
            
            try:
                success = await pool_manager.spawn_agent(
                    agent_id=agent.id,
                    role_class=role_class,
                    heartbeat_interval=30,
                    max_idle_time=300,
                )
                if success:
                    spawned_count += 1
                    logger.info(f"✓ Spawned agent {agent.human_name} ({agent.role_type}) in {pool_manager.pool_name}")
                else:
                    logger.warning(f"Failed to spawn agent {agent.human_name}")
            except Exception as e:
                logger.error(f"Error spawning agent {agent.human_name}: {e}")
        
        logger.info(f"Auto-spawned {spawned_count}/{len(created_agents)} agents for project {project.code}")
        
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
async def delete_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Delete a project and clean up all associated files (workspace + worktrees).

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
    
    # Stop any running agents for this project
    from app.api.routes.agent_management import get_available_pool
    agents = session.query(Agent).filter(Agent.project_id == project_id).all()
    for agent in agents:
        pool_manager = get_available_pool(role_type=agent.role_type)
        if pool_manager:
            try:
                await pool_manager.terminate_agent(agent.id)
                logger.info(f"Stopped agent {agent.human_name}")
            except Exception as e:
                logger.warning(f"Failed to stop agent {agent.human_name}: {e}")
    
    # Clean up project files (workspace + worktrees)
    project_service.delete_with_cleanup(project_id)


@router.post("/{project_id}/cleanup", status_code=status.HTTP_200_OK)
def cleanup_project_worktrees(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """
    Clean up all worktrees for a project (without deleting the project).

    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user

    Returns:
        dict: Cleanup result with count of deleted worktrees
    """
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    deleted_count = project_service.cleanup_worktrees(project_id)
    
    return {
        "message": f"Cleaned up {deleted_count} worktrees",
        "deleted_count": deleted_count,
        "project_id": str(project_id),
    }
