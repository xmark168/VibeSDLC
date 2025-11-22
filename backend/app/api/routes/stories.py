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
async def create_story(
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

    # Publish story created event to Kafka
    try:
        from app.kafka import get_kafka_producer, KafkaTopics, StoryCreatedEvent

        producer = await get_kafka_producer()

        await producer.publish(
            topic=KafkaTopics.STORY_EVENTS,
            event=StoryCreatedEvent(
                project_id=story.project_id,
                user_id=current_user.id,
                story_id=story.id,
                title=story.title,
                description=story.description,
                story_type=story.type.value if story.type else "UserStory",
                status=story.status.value,
                epic_id=story.epic_id,
                assignee_id=story.assignee_id,
                reviewer_id=story.reviewer_id,
                created_by_agent=None,
            ),
        )
    except Exception as e:
        # Log error but don't fail the API call
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to publish story created event to Kafka: {e}")

    return story


# ===== Kanban Board View =====
@router.get("/kanban/{project_id}")
def get_kanban_board(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID
) -> Any:
    """
    Get Kanban board grouped by columns with WIP limits.
    Returns stories organized by status plus WIP limit information.
    """
    from app.models import ColumnWIPLimit

    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from sqlalchemy.orm import selectinload
    statement = select(Story).where(
        Story.project_id == project_id
    ).options(
        selectinload(Story.parent),
        selectinload(Story.children),
        selectinload(Story.epic)
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

    # Fetch WIP limits for this project
    wip_limits_query = session.exec(
        select(ColumnWIPLimit).where(ColumnWIPLimit.project_id == project_id)
    ).all()

    wip_limits = {
        limit.column_name: {
            "wip_limit": limit.wip_limit,
            "limit_type": limit.limit_type
        }
        for limit in wip_limits_query
    }

    return {
        "project_id": project_id,
        "project_name": project.name,
        "board": board,
        "wip_limits": wip_limits  # Include WIP limits in response
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
async def update_story_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    new_status: StoryStatus
) -> Any:
    """
    Update story status with Lean Kanban enforcement.
    - Enforces WIP limits (hard limits block transition)
    - Validates workflow policies (DoR/DoD)
    - Tracks flow metrics timestamps
    """
    from datetime import datetime, timezone
    from sqlmodel import and_
    from app.models import ColumnWIPLimit, WorkflowPolicy

    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    old_status = story.status

    # Skip validation if status unchanged
    if old_status == new_status:
        return story

    # === STEP 1: Validate WIP Limits (Hard Enforcement) ===
    wip_limit = session.exec(
        select(ColumnWIPLimit).where(
            and_(
                ColumnWIPLimit.project_id == story.project_id,
                ColumnWIPLimit.column_name == new_status.value
            )
        )
    ).first()

    if wip_limit:
        # Count current items in target column (excluding this story)
        current_count = session.exec(
            select(func.count()).select_from(Story).where(
                and_(
                    Story.project_id == story.project_id,
                    Story.status == new_status,
                    Story.id != story_id
                )
            )
        ).one()

        # Check if exceeds WIP limit
        if current_count >= wip_limit.wip_limit and wip_limit.limit_type == "hard":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "WIP_LIMIT_EXCEEDED",
                    "message": f"Cannot move to {new_status.value}: WIP limit {wip_limit.wip_limit} exceeded",
                    "column": new_status.value,
                    "current_count": current_count,
                    "wip_limit": wip_limit.wip_limit
                }
            )

    # === STEP 2: Validate Workflow Policies ===
    policy = session.exec(
        select(WorkflowPolicy).where(
            and_(
                WorkflowPolicy.project_id == story.project_id,
                WorkflowPolicy.from_status == old_status.value,
                WorkflowPolicy.to_status == new_status.value,
                WorkflowPolicy.is_active == True
            )
        )
    ).first()

    if policy and policy.criteria:
        violations = []

        # Check each criteria
        if policy.criteria.get("assignee_required") and not story.assignee_id:
            violations.append("Story must have an assignee")

        if policy.criteria.get("no_blockers") and story.has_active_blockers():
            violations.append("Story has active blockers that must be resolved")

        if policy.criteria.get("acceptance_criteria_defined") and not story.acceptance_criteria:
            violations.append("Acceptance criteria must be defined")

        if policy.criteria.get("story_points_estimated") and not story.story_point:
            violations.append("Story points must be estimated")

        if violations:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "POLICY_VIOLATION",
                    "message": "Workflow policy not satisfied",
                    "violations": violations,
                    "policy": {
                        "from": old_status.value,
                        "to": new_status.value
                    }
                }
            )

    # === STEP 3: Update Status and Flow Timestamps ===
    story.status = new_status
    now = datetime.now(timezone.utc)

    # Track flow metrics based on new status
    if new_status == StoryStatus.IN_PROGRESS and not story.started_at:
        story.started_at = now
    elif new_status == StoryStatus.REVIEW and not story.review_started_at:
        story.review_started_at = now
    elif new_status == StoryStatus.DONE and old_status != StoryStatus.DONE:
        story.completed_at = now

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

    # Publish story status changed event to Kafka
    try:
        from app.kafka import get_kafka_producer, KafkaTopics, StoryStatusChangedEvent

        producer = await get_kafka_producer()

        await producer.publish(
            topic=KafkaTopics.STORY_EVENTS,
            event=StoryStatusChangedEvent(
                project_id=story.project_id,
                user_id=current_user.id,
                story_id=story.id,
                old_status=old_status.value,
                new_status=new_status.value,
                changed_by=str(current_user.id),
                transition_reason=f"Updated by {current_user.email}",
            ),
        )
    except Exception as e:
        # Log error but don't fail the API call
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to publish story status changed event to Kafka: {e}")

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
async def update_story(
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

    # Publish story updated event to Kafka
    try:
        from app.kafka import get_kafka_producer, KafkaTopics, StoryUpdatedEvent

        producer = await get_kafka_producer()

        await producer.publish(
            topic=KafkaTopics.STORY_EVENTS,
            event=StoryUpdatedEvent(
                project_id=story.project_id,
                user_id=current_user.id,
                story_id=story.id,
                updated_fields=update_data,
                updated_by=str(current_user.id),
            ),
        )
    except Exception as e:
        # Log error but don't fail the API call
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to publish story updated event to Kafka: {e}")

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
