"""
Story Management API
Endpoints for BA/TeamLeader/Dev/Tester to manage stories in Kanban board
Replaces backlog_items with proper status columns: Todo, InProgress, Review, Done
"""
import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, func
from app.api.deps import CurrentUser, SessionDep
from app.models import Story, StoryStatus, StoryType, IssueActivity, Project
from app.schemas import StoryCreate, StoryUpdate, StoryPublic, StoriesPublic

router = APIRouter(prefix="/stories", tags=["stories"])


# ===== BA/TeamLeader: Story Creation & Planning =====
@router.post("/", response_model=StoryPublic)
def create_story(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_in: StoryCreate
) -> Any:
    """
    Create new story (BA role).
    BA creates stories in TODO column by default.
    """
    # Validate project
    project = session.get(Project, story_in.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Auto-assign rank if not provided
    story_data = story_in.model_dump()
    if story_data.get("rank") is None:
        max_rank = session.exec(
            select(func.max(Story.rank)).where(
                Story.project_id == story_in.project_id,
                Story.status == (story_in.status or StoryStatus.TODO)
            )
        ).one()
        story_data["rank"] = (max_rank or 0) + 1

    story = Story(**story_data)
    session.add(story)
    session.commit()
    session.refresh(story)

    # Log activity
    activity = IssueActivity(
        issue_id=story.id,
        actor_id=str(current_user.id),
        actor_name=current_user.full_name or current_user.email,
        note="Story created by BA"
    )
    session.add(activity)
    session.commit()

    return story


# ===== Kanban Board View =====
@router.get("/kanban/{project_id}")
def get_kanban_board(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID
) -> Any:
    """
    Get Kanban board grouped by columns (Todo, InProgress, Review, Done).
    Returns stories organized by status for UI display.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from sqlalchemy.orm import selectinload
    statement = select(Story).where(
        Story.project_id == project_id
    ).options(
        selectinload(Story.parent),
        selectinload(Story.children)
    ).order_by(Story.status, Story.rank)

    stories = session.exec(statement).all()

    # Group by status
    board = {
        "Todo": [],
        "InProgress": [],
        "Review": [],
        "Done": []
    }

    for story in stories:
        column = story.status.value
        if column in board:
            board[column].append(StoryPublic.model_validate(story))

    return {
        "project_id": project_id,
        "project_name": project.name,
        "board": board
    }


# ===== TeamLeader: Assign & Review =====
@router.put("/{story_id}/assign", response_model=StoryPublic)
def assign_story(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    assignee_id: uuid.UUID,
    reviewer_id: Optional[uuid.UUID] = None
) -> Any:
    """
    Assign story to Dev/Tester (TeamLeader role).
    Updates assignee_id and optionally reviewer_id.
    """
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    old_assignee = story.assignee_id
    story.assignee_id = assignee_id
    if reviewer_id:
        story.reviewer_id = reviewer_id

    session.add(story)
    session.commit()
    session.refresh(story)

    # Log activity
    activity = IssueActivity(
        issue_id=story.id,
        actor_id=str(current_user.id),
        actor_name=current_user.full_name or current_user.email,
        assignee_from=str(old_assignee) if old_assignee else None,
        assignee_to=str(assignee_id),
        note="Story assigned by TeamLeader"
    )
    session.add(activity)
    session.commit()

    return story


# ===== Dev/Tester: Status Updates =====
@router.put("/{story_id}/status", response_model=StoryPublic)
def update_story_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    new_status: StoryStatus
) -> Any:
    """
    Update story status (Dev/Tester role).
    Dev moves: Todo -> InProgress -> Review
    Tester moves: Review -> Done (or back to InProgress if issues)
    """
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    old_status = story.status
    story.status = new_status

    # Set completed_at when moving to Done
    if new_status == StoryStatus.DONE and old_status != StoryStatus.DONE:
        from datetime import datetime, timezone
        story.completed_at = datetime.now(timezone.utc)

    session.add(story)
    session.commit()
    session.refresh(story)

    # Log activity
    activity = IssueActivity(
        issue_id=story.id,
        actor_id=str(current_user.id),
        actor_name=current_user.full_name or current_user.email,
        status_from=old_status.value,
        status_to=new_status.value,
        note=f"Status updated to {new_status.value}"
    )
    session.add(activity)
    session.commit()

    return story


# ===== List/Get/Update/Delete (Standard CRUD) =====
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
    """List stories with filters"""
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

    return StoriesPublic(data=stories, count=count)


@router.get("/{story_id}", response_model=StoryPublic)
def get_story(
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Get story details"""
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.patch("/{story_id}", response_model=StoryPublic)
def update_story(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    story_in: StoryUpdate
) -> Any:
    """Update story (BA/TeamLeader role)"""
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    update_data = story_in.model_dump(exclude_unset=True)
    story.sqlmodel_update(update_data)
    session.add(story)
    session.commit()
    session.refresh(story)

    # Log activity
    activity = IssueActivity(
        issue_id=story.id,
        actor_id=str(current_user.id),
        actor_name=current_user.full_name or current_user.email,
        note="Story updated"
    )
    session.add(activity)
    session.commit()

    return story


@router.delete("/{story_id}")
def delete_story(
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> dict:
    """Delete story"""
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    session.delete(story)
    session.commit()

    return {"message": "Story deleted successfully"}
