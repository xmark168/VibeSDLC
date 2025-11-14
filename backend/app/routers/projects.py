"""
Project Router - API endpoints for project and Kanban board management
"""
from typing import List
from fastapi import APIRouter, Depends, status, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models import User
from app.services.project_service import ProjectService
from app.kanban_schemas import ProjectCreate, ProjectUpdate, ProjectResponse


router = APIRouter(prefix="/projects", tags=["Projects"])
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project"
)
@limiter.limit("10/hour")
async def create_project(
    request: Request,
    data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project with default Kanban policy

    **Rate Limit:** 10 requests per hour

    **Authorization**: Authenticated user (becomes owner)

    - **code**: Unique project code/identifier
    - **name**: Project name
    - **working_directory**: Optional working directory path
    - **tech_stack_id**: Optional tech stack reference
    - **kanban_policy**: Optional custom Kanban policy (uses default if not provided)

    The project will be automatically configured with:
    - Default Kanban board columns (Backlog, In Progress, Review, Testing, Done, Blocked, Archived)
    - WIP limits (3 for In Progress, 2 for Review/Testing)
    - Workflow transition rules following Lean Kanban principles

    Returns the created project
    """
    project = await ProjectService.create(data, current_user, db)
    return project


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List user's projects"
)
async def list_projects(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all projects owned by current user

    **Authorization**: Authenticated user

    Returns list of projects
    """
    projects = await ProjectService.get_user_projects(current_user, db)
    return projects


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID"
)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific project by ID

    Returns project details including Kanban policy
    """
    project = await ProjectService.get_by_id(project_id, db)
    return project


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project"
)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update project details

    **Authorization**: Project owner only

    - **code**: Update project code (must be unique)
    - **name**: Update project name
    - **working_directory**: Update working directory
    - **tech_stack_id**: Update tech stack
    - **kanban_policy**: Update Kanban policy (use separate endpoint for better validation)

    Returns updated project
    """
    project = await ProjectService.update(project_id, data, current_user, db)
    return project


@router.put(
    "/{project_id}/kanban-policy",
    response_model=ProjectResponse,
    summary="Update Kanban policy"
)
async def update_kanban_policy(
    project_id: int,
    policy: dict = Body(..., description="Kanban policy JSON"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update project Kanban policy

    **Authorization**: Project owner only

    The policy must include:
    - **columns**: Array of column configurations with status, name, wip_limit
    - **workflow_rules**: Object with allowed_transitions and completion_requirements

    Example policy structure:
    ```json
    {
      "columns": [
        {"status": "TODO", "name": "Backlog", "wip_limit": null, "position": 0},
        {"status": "IN_PROGRESS", "name": "In Progress", "wip_limit": 3, "position": 1}
      ],
      "workflow_rules": {
        "allowed_transitions": {
          "TODO": ["IN_PROGRESS"],
          "IN_PROGRESS": ["REVIEW", "BLOCKED"]
        },
        "completion_requirements": {
          "acceptance_criteria_required": true,
          "min_agents_assigned": 1
        }
      }
    }
    ```

    Returns updated project
    """
    project = await ProjectService.update_kanban_policy(
        project_id, policy, current_user, db
    )
    return project


@router.get(
    "/{project_id}/board",
    summary="Get Kanban board view"
)
async def get_board_view(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get Kanban board view with stories grouped by status

    Returns:
    - Project information
    - Columns with their stories
    - WIP counts and limits
    - Total and blocked story counts

    Each column includes:
    - Status and name
    - WIP limit
    - Current story count
    - Whether WIP limit is exceeded
    - List of stories in that column

    This endpoint provides the complete view needed to render a Kanban board UI
    """
    board = await ProjectService.get_board_view(project_id, db)
    return board


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project"
)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete a project

    **Authorization**: Project owner only

    The project will be marked as deleted but not removed from database.
    All related data (epics, stories, agents) will be cascaded deleted.
    """
    await ProjectService.delete(project_id, current_user, db)
