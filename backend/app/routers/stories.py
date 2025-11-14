"""
Story Router - API endpoints for story and Kanban workflow management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models import User
from app.services.story_service import StoryService
from app.kanban_schemas import StoryCreate, StoryUpdate, StoryResponse
from app.enums import StoryStatus, StoryType, StoryPriority


router = APIRouter(prefix="/stories", tags=["Stories"])
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "",
    response_model=StoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create story"
)
@limiter.limit("50/hour")
async def create_story(
    request: Request,
    data: StoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new story

    **Rate Limit:** 50 requests per hour

    **Authorization**: Project owner only (via epic)

    Stories always start with status=TODO.
    An initial status history record is automatically created.
    """
    story = await StoryService.create(data, current_user, db)
    return story


@router.get(
    "",
    response_model=List[StoryResponse],
    summary="List stories"
)
async def list_stories(
    epic_id: int = Query(..., description="Filter by epic ID (required)"),
    status_filter: Optional[StoryStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of stories

    **Filters**:
    - **epic_id**: Epic ID (required)
    - **status**: Optional status filter
    """
    stories = await StoryService.get_by_epic(epic_id, db, status_filter)
    return stories


@router.get(
    "/{story_id}",
    response_model=StoryResponse,
    summary="Get story by ID"
)
async def get_story(
    story_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific story by ID"""
    story = await StoryService.get_by_id(story_id, db)
    return story


@router.put(
    "/{story_id}",
    response_model=StoryResponse,
    summary="Update story"
)
async def update_story(
    story_id: int,
    data: StoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update story (non-status fields)

    **Authorization**: Project owner only

    To change status, use PUT /stories/{id}/status endpoint
    """
    story = await StoryService.update(story_id, data, current_user, db)
    return story


@router.delete(
    "/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete story"
)
async def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete story

    **Authorization**: Project owner only
    """
    await StoryService.delete(story_id, current_user, db)


# ==================== KANBAN WORKFLOW ====================

@router.put(
    "/{story_id}/status",
    response_model=StoryResponse,
    summary="Move story to new status"
)
async def move_story_status(
    story_id: int,
    new_status: StoryStatus = Body(..., embed=True, description="New status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Move story to new status with Lean Kanban validations

    **Authorization**: Project owner only

    **Validations applied**:
    1. **Workflow rules**: Transition must be allowed per kanban_policy
    2. **WIP limits**: Target column must not exceed WIP limit
    3. **Completion requirements**: Story must meet DoD if moving to DONE

    **Status transition rules** (default):
    - TODO → IN_PROGRESS
    - IN_PROGRESS → REVIEW, BLOCKED
    - REVIEW → IN_PROGRESS, TESTING, BLOCKED
    - TESTING → REVIEW, DONE, BLOCKED
    - BLOCKED → TODO, IN_PROGRESS, REVIEW, TESTING
    - DONE → ARCHIVED

    A status history record is automatically created.
    """
    story = await StoryService.move_status(story_id, new_status, current_user, db)
    return story


# ==================== AGENT ASSIGNMENTS ====================

@router.post(
    "/{story_id}/assign",
    status_code=status.HTTP_201_CREATED,
    summary="Assign agent to story"
)
async def assign_agent(
    story_id: int,
    agent_id: int = Body(..., embed=True),
    role: Optional[str] = Body(None, embed=True),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign an agent to a story

    **Authorization**: Project owner only

    **Validations**:
    - Agent must belong to the same project
    - Agent must be active
    - Agent cannot be assigned twice
    """
    assignment = await StoryService.assign_agent(
        story_id, agent_id, role, current_user, db
    )
    return {
        "message": "Agent assigned successfully",
        "assignment": assignment
    }


@router.delete(
    "/{story_id}/assign/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unassign agent from story"
)
async def unassign_agent(
    story_id: int,
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove agent assignment

    **Authorization**: Project owner only
    """
    await StoryService.unassign_agent(story_id, agent_id, current_user, db)


# ==================== HISTORY & METRICS ====================

@router.get(
    "/{story_id}/history",
    summary="Get status change history"
)
async def get_story_history(
    story_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete status change history for a story

    Returns all status transitions ordered by time.
    Useful for auditing and understanding story flow.
    """
    history = await StoryService.get_status_history(story_id, db)
    return history


@router.get(
    "/{story_id}/cycle-time",
    summary="Calculate cycle time"
)
async def get_cycle_time(
    story_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate story cycle time

    **Cycle time** = Time from first IN_PROGRESS to DONE

    Returns None if story hasn't completed a full cycle yet.

    This is a key Lean Kanban metric for measuring flow efficiency.
    """
    cycle_time = await StoryService.calculate_cycle_time(story_id, db)

    if not cycle_time:
        return {
            "message": "Cycle not complete yet",
            "cycle_time": None
        }

    return cycle_time
