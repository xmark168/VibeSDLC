"""
Story Management API
Endpoints for BA/TeamLeader/Dev/Tester to manage stories in Kanban board
"""
import uuid
from typing import Any, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import select, func

from app.api.deps import CurrentUser, SessionDep
from app.models import Story, StoryStatus, StoryType
from app.schemas import StoryCreate, StoryUpdate, StoryPublic, StoriesPublic
from app.services.story_service import StoryService

router = APIRouter(prefix="/stories", tags=["stories"])


# ===== Request/Response Models =====
class ReviewActionType(str, Enum):
    APPLY = "apply"
    KEEP = "keep"
    REMOVE = "remove"


class ReviewActionRequest(BaseModel):
    action: ReviewActionType
    suggested_title: Optional[str] = None
    suggested_acceptance_criteria: Optional[list[str]] = None
    suggested_requirements: Optional[list[str]] = None


# ===== Story Creation =====
@router.post("/", response_model=StoryPublic)
async def create_story(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_in: StoryCreate
) -> Any:
    """Create new story (BA role)."""
    story_service = StoryService(session)
    
    try:
        story = await story_service.create_with_events(
            story_in=story_in,
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email
        )
        return story
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Kanban Board =====
@router.get("/kanban/{project_id}")
def get_kanban_board(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID
) -> Any:
    """Get Kanban board grouped by columns with WIP limits."""
    story_service = StoryService(session)
    
    try:
        return story_service.get_kanban_board(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Assignment =====
@router.put("/{story_id}/assign", response_model=StoryPublic)
def assign_story(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    assignee_id: uuid.UUID,
    reviewer_id: Optional[uuid.UUID] = None
) -> Any:
    """Assign story to Dev/Tester (TeamLeader role)."""
    story_service = StoryService(session)
    
    try:
        return story_service.assign(
            story_id=story_id,
            assignee_id=assignee_id,
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email,
            reviewer_id=reviewer_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Status Update =====
@router.put("/{story_id}/status", response_model=StoryPublic)
async def update_story_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    new_status: StoryStatus
) -> Any:
    """Update story status with Lean Kanban enforcement."""
    story_service = StoryService(session)
    
    try:
        return await story_service.update_status_with_validation(
            story_id=story_id,
            new_status=new_status,
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email,
            user_email=current_user.email
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        error_data = e.args[0] if e.args else {"message": str(e)}
        if error_data.get("error") == "WIP_LIMIT_EXCEEDED":
            raise HTTPException(status_code=409, detail=error_data)
        raise HTTPException(status_code=422, detail=error_data)


# ===== List Stories =====
@router.get("/", response_model=StoriesPublic)
def list_stories(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: Optional[uuid.UUID] = Query(None),
    status: Optional[StoryStatus] = Query(None),
    assignee_id: Optional[uuid.UUID] = Query(None),
    type: Optional[StoryType] = Query(None),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """List stories with filters."""
    statement = select(Story)

    if project_id:
        statement = statement.where(Story.project_id == project_id)
    if status:
        statement = statement.where(Story.status == status)
    if assignee_id:
        statement = statement.where(Story.assignee_id == assignee_id)
    if type:
        statement = statement.where(Story.type == type)

    statement = statement.order_by(Story.rank)

    count_statement = select(func.count()).select_from(Story)
    if project_id:
        count_statement = count_statement.where(Story.project_id == project_id)

    count = session.exec(count_statement).one()
    stories = session.exec(statement.offset(skip).limit(limit)).all()

    # Convert Story objects to dicts for StoriesPublic
    stories_data = [story.model_dump() if hasattr(story, 'model_dump') else dict(story) for story in stories]
    return StoriesPublic(data=stories_data, count=count)


# ===== Get by Project =====
@router.get("/project/{project_id}", response_model=StoriesPublic)
def get_stories_by_project(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID,
    status: Optional[StoryStatus] = Query(None),
    assignee_id: Optional[uuid.UUID] = Query(None),
    type: Optional[StoryType] = Query(None),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get stories for a specific project."""
    story_service = StoryService(session)
    
    if status:
        stories = story_service.get_by_project_and_status(project_id, status)
    elif assignee_id:
        stories = story_service.get_by_project_and_assignee(project_id, assignee_id)
    elif type:
        stories = story_service.get_by_project_and_type(project_id, type)
    else:
        stories = story_service.get_all_by_project(project_id)
    
    # Apply pagination
    total = len(stories)
    stories = stories[skip:skip + limit]
    
    # Convert Story objects to dicts for StoriesPublic
    stories_data = [story.model_dump() if hasattr(story, 'model_dump') else dict(story) for story in stories]
    return StoriesPublic(data=stories_data, count=total)


# ===== Get Single Story =====
@router.get("/{story_id}", response_model=StoryPublic)
def get_story(
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Get story details."""
    story_service = StoryService(session)
    story = story_service.get_by_id(story_id)
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


# ===== Update Story =====
@router.patch("/{story_id}", response_model=StoryPublic)
async def update_story(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    story_in: StoryUpdate
) -> Any:
    """Update story (BA/TeamLeader role)."""
    story_service = StoryService(session)
    
    try:
        return await story_service.update_with_events(
            story_id=story_id,
            story_in=story_in,
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Delete Story =====
@router.delete("/{story_id}")
def delete_story(
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> dict:
    """Delete story."""
    story_service = StoryService(session)
    
    if not story_service.delete(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    
    return {"message": "Story deleted successfully"}


# ===== Review Action =====
@router.post("/{story_id}/review-action")
async def handle_review_action(
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    action_request: ReviewActionRequest
) -> dict:
    """Handle user action on story review (apply/keep/remove)."""
    story_service = StoryService(session)
    
    try:
        await story_service.handle_review_action(
            story_id=story_id,
            action=action_request.action.value,
            user_id=current_user.id,
            suggested_title=action_request.suggested_title,
            suggested_acceptance_criteria=action_request.suggested_acceptance_criteria,
            suggested_requirements=action_request.suggested_requirements
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return {"message": f"Action '{action_request.action.value}' completed", "story_id": str(story_id)}
