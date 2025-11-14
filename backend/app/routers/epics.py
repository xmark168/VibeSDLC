"""
Epic Router - API endpoints for epic management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models import User
from app.services.epic_service import EpicService
from app.kanban_schemas import EpicCreate, EpicUpdate, EpicResponse, StoryResponse


router = APIRouter(prefix="/epics", tags=["Epics"])


@router.post(
    "",
    response_model=EpicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create epic"
)
async def create_epic(
    data: EpicCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new epic

    **Authorization**: Project owner only

    - **title**: Epic title
    - **description**: Optional description
    - **project_id**: Project this epic belongs to

    Returns the created epic
    """
    epic = await EpicService.create(data, current_user, db)
    return epic


@router.get(
    "",
    response_model=List[EpicResponse],
    summary="List epics"
)
async def list_epics(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of epics

    **Filter**:
    - **project_id**: Filter epics by project (required)

    Returns list of epics
    """
    if not project_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id query parameter is required"
        )

    epics = await EpicService.get_by_project(project_id, db)
    return epics


@router.get(
    "/{epic_id}",
    response_model=EpicResponse,
    summary="Get epic by ID"
)
async def get_epic(
    epic_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific epic by ID

    Returns epic details
    """
    epic = await EpicService.get_by_id(epic_id, db)
    return epic


@router.put(
    "/{epic_id}",
    response_model=EpicResponse,
    summary="Update epic"
)
async def update_epic(
    epic_id: int,
    data: EpicUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an epic

    **Authorization**: Project owner only

    - **title**: Update title
    - **description**: Update description

    Returns updated epic
    """
    epic = await EpicService.update(epic_id, data, current_user, db)
    return epic


@router.delete(
    "/{epic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete epic"
)
async def delete_epic(
    epic_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete an epic

    **Authorization**: Project owner only

    The epic will be marked as deleted but not removed from database.
    All related stories will be cascaded deleted.
    """
    await EpicService.delete(epic_id, current_user, db)


@router.get(
    "/{epic_id}/stories",
    response_model=List[StoryResponse],
    summary="Get epic's stories"
)
async def get_epic_stories(
    epic_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all stories in this epic

    Returns list of stories ordered by creation date
    """
    stories = await EpicService.get_stories(epic_id, db)
    return stories


@router.get(
    "/{epic_id}/progress",
    summary="Get epic progress"
)
async def get_epic_progress(
    epic_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get epic progress statistics

    Returns:
    - Total stories count
    - Completed stories count
    - In progress stories count
    - Blocked stories count
    - Completion percentage
    - Stories count by status

    Useful for burndown charts and progress tracking
    """
    progress = await EpicService.get_progress(epic_id, db)
    return progress
