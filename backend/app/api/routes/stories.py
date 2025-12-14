"""Story Management API."""
import asyncio
import logging
import uuid
from typing import Any, Optional
from enum import Enum
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import select, func, delete
import httpx
from app.api.deps import CurrentUser, SessionDep
from app.models import Story, StoryStatus, StoryType, AgentStatus
from app.schemas import StoryCreate, StoryUpdate, StoryPublic, StoriesPublic
from app.schemas.story import BulkRankUpdateRequest
from app.services.story_service import StoryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stories", tags=["stories"])


def check_agent_busy(agent_id: uuid.UUID) -> tuple[bool, str]:
    """Check if agent is busy. Returns (is_busy, reason)."""
    from app.api.routes.agent_management import get_available_pool
    manager = get_available_pool()
    if not manager:
        return False, ""
    agent = manager.get_agent(agent_id)
    if not agent:
        return False, ""
    if agent.state == AgentStatus.busy:
        return True, "Agent đang xử lý task. Vui lòng đợi hoặc stop task hiện tại trước."
    if hasattr(agent, '_task_queue') and agent._task_queue.qsize() > 0:
        return True, f"Agent có {agent._task_queue.qsize()} task đang chờ trong queue."
    return False, ""


async def run_subprocess_async(*args, **kwargs):
    """Run subprocess in thread pool."""
    import subprocess
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: subprocess.run(*args, **kwargs))


class ReviewActionType(str, Enum):
    APPLY = "apply"
    KEEP = "keep"
    REMOVE = "remove"


class ReviewActionRequest(BaseModel):
    action: ReviewActionType
    suggested_title: Optional[str] = None
    suggested_acceptance_criteria: Optional[list[str]] = None
    suggested_requirements: Optional[list[str]] = None
@router.post("/", response_model=StoryPublic)
async def create_story(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_in: StoryCreate
) -> Any:
    """Create new story (BA role)."""
    from app.models import Epic, EpicStatus
    
    story_service = StoryService(session)
    
    try:
        # If new_epic_title provided, create new epic first
        new_epic_id = None
        if story_in.new_epic_title and story_in.new_epic_title.strip():
            # Generate epic code
            existing_epics_count = session.exec(
                select(func.count()).select_from(Epic).where(Epic.project_id == story_in.project_id)
            ).one()
            epic_code = f"EPIC-{existing_epics_count + 1:03d}"
            
            # Create new epic with all provided fields
            new_epic = Epic(
                epic_code=epic_code,
                title=story_in.new_epic_title.strip(),
                description=story_in.new_epic_description.strip() if story_in.new_epic_description else None,
                domain=story_in.new_epic_domain or "General",
                project_id=story_in.project_id,
                epic_status=EpicStatus.PLANNED
            )
            session.add(new_epic)
            session.commit()
            session.refresh(new_epic)
            new_epic_id = new_epic.id
        
        story = await story_service.create_with_events(
            story_in=story_in,
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email,
            override_epic_id=new_epic_id  # Pass new epic ID explicitly
        )
        return story
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Bulk Rank Update =====
@router.patch("/bulk-rank")
def bulk_update_ranks(
    session: SessionDep,
    current_user: CurrentUser,
    request: BulkRankUpdateRequest
) -> dict:
    """Bulk update ranks for multiple stories in one transaction."""
    updated_count = 0
    for item in request.updates:
        story = session.get(Story, item.story_id)
        if story:
            story.rank = item.rank
            session.add(story)
            updated_count += 1
    session.commit()
    return {"updated": updated_count}


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
        if error_data.get("error") == "DEPENDENCIES_NOT_COMPLETED":
            raise HTTPException(status_code=409, detail=error_data)
        if error_data.get("error") == "DONE_STATUS_LOCKED":
            raise HTTPException(status_code=403, detail=error_data)
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
    from sqlalchemy.orm import selectinload
    from app.models import Epic
    
    statement = select(Story).options(selectinload(Story.epic))

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

    # Convert Story objects to dicts with epic info
    stories_data = []
    for story in stories:
        story_dict = story.model_dump() if hasattr(story, 'model_dump') else dict(story)
        # Add epic info if epic exists
        if story.epic:
            story_dict["epic_code"] = story.epic.epic_code
            story_dict["epic_title"] = story.epic.title
            story_dict["epic_description"] = story.epic.description
            story_dict["epic_domain"] = story.epic.domain
        stories_data.append(story_dict)
    
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
        story = await story_service.update_with_events(
            story_id=story_id,
            story_in=story_in,
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email
        )
        
        # Convert to StoryPublic and add epic info
        story_data = StoryPublic.model_validate(story)
        if story.epic:
            story_data.epic_code = story.epic.epic_code
            story_data.epic_title = story.epic.title
            story_data.epic_description = story.epic.description
            story_data.epic_domain = story.epic.domain
        
        return story_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Delete Story =====
@router.delete("/{story_id}")
def delete_story(
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> dict:
    """Delete story with worktree cleanup."""
    import subprocess
    import shutil
    from pathlib import Path
    
    story_service = StoryService(session)
    
    # Get story before delete to cleanup worktree
    story = story_service.get_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Stop dev server if running
    if story.running_pid:
        try:
            import os
            import signal
            os.kill(story.running_pid, signal.SIGTERM)
            logger.info(f"[delete_story] Stopped dev server (PID: {story.running_pid})")
        except (ProcessLookupError, OSError) as e:
            logger.warning(f"[delete_story] Dev server process not found or already stopped: {e}")
    
    # Cleanup worktree and branch if exists
    worktree_path = story.worktree_path
    branch_name = story.branch_name
    
    if worktree_path and Path(worktree_path).exists():
        try:
            # Get main repo path (parent of worktrees)
            worktree_parent = Path(worktree_path).parent
            main_repo = None
            
            # Try to find main repo from worktree
            result = subprocess.run(
                ["git", "rev-parse", "--git-common-dir"],
                cwd=worktree_path, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                git_common_dir = result.stdout.strip()
                main_repo = str(Path(git_common_dir).parent)
            
            # Remove worktree
            if main_repo:
                subprocess.run(
                    ["git", "worktree", "remove", worktree_path, "--force"],
                    cwd=main_repo, capture_output=True, timeout=30
                )
            
            # Fallback: just delete the directory
            if Path(worktree_path).exists():
                shutil.rmtree(worktree_path, ignore_errors=True)
                
            logger.info(f"[delete_story] Cleaned up worktree: {worktree_path}")
        except Exception as e:
            logger.warning(f"[delete_story] Failed to cleanup worktree: {e}")
    
    # Delete branch if exists
    if branch_name and worktree_path:
        try:
            # Get main repo
            worktree_parent = Path(worktree_path).parent
            result = subprocess.run(
                ["git", "rev-parse", "--git-common-dir"],
                cwd=str(worktree_parent), capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                git_common_dir = result.stdout.strip()
                main_repo = str(Path(git_common_dir).parent)
                
                subprocess.run(
                    ["git", "branch", "-D", branch_name],
                    cwd=main_repo, capture_output=True, timeout=10
                )
                logger.info(f"[delete_story] Deleted branch: {branch_name}")
        except Exception as e:
            logger.warning(f"[delete_story] Failed to delete branch: {e}")
    
    # Delete story from DB
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
        updated_story = await story_service.handle_review_action(
            story_id=story_id,
            action=action_request.action.value,
            user_id=current_user.id,
            suggested_title=action_request.suggested_title,
            suggested_acceptance_criteria=action_request.suggested_acceptance_criteria,
            suggested_requirements=action_request.suggested_requirements
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Return updated story data for apply action
    story_data = None
    if updated_story and action_request.action.value != 'remove':
        story_data = {
            "id": str(updated_story.id),
            "title": updated_story.title,
            "description": updated_story.description,
            "acceptance_criteria": updated_story.acceptance_criteria,
            "requirements": updated_story.requirements,
        }
    
    return {
        "message": f"Action '{action_request.action.value}' completed", 
        "story_id": str(story_id),
        "story": story_data
    }


# ===== List Epics =====
@router.get("/epics/{project_id}")
def list_epics(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID
) -> Any:
    """List all epics for a project."""
    from app.models import Epic
    
    statement = select(Epic).where(Epic.project_id == project_id).order_by(Epic.created_at)
    epics = session.exec(statement).all()
    
    return {
        "data": [
            {
                "id": str(epic.id),
                "epic_code": epic.epic_code,
                "title": epic.title,
                "description": epic.description,
                "domain": epic.domain,
                "status": epic.epic_status.value if epic.epic_status else None
            }
            for epic in epics
        ],
        "count": len(epics)
    }


# ===== Story Messages =====
@router.get("/{story_id}/messages")
async def get_story_messages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
) -> Any:
    """Get messages in story channel."""
    from app.models import StoryMessage
    
    # Verify story exists
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get messages ordered by created_at
    statement = (
        select(StoryMessage)
        .where(StoryMessage.story_id == story_id)
        .order_by(StoryMessage.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    messages = session.exec(statement).all()
    
    # Get total count
    count_statement = (
        select(func.count())
        .select_from(StoryMessage)
        .where(StoryMessage.story_id == story_id)
    )
    total = session.exec(count_statement).one()
    
    return {
        "data": [
            {
                "id": str(msg.id),
                "author_type": msg.author_type,
                "author_name": msg.author_name,
                "content": msg.content,
                "message_type": msg.message_type,
                "structured_data": msg.structured_data,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


class SendMessageRequest(BaseModel):
    content: str


@router.post("/{story_id}/messages")
async def send_story_message(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    request: SendMessageRequest
) -> Any:
    """Send a message to story channel."""
    from app.models import StoryMessage
    from app.websocket.connection_manager import connection_manager
    
    # Verify story exists
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Create message
    message = StoryMessage(
        story_id=story_id,
        author_type="user",
        author_name=current_user.full_name or current_user.email,
        user_id=current_user.id,
        content=request.content,
        message_type="text",
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    
    # Broadcast via WebSocket
    await connection_manager.broadcast_to_project(
        {
            "type": "story_message",
            "story_id": str(story_id),
            "message_id": str(message.id),
            "author_type": "user",
            "author_name": message.author_name,
            "content": message.content,
            "message_type": "text",
            "timestamp": message.created_at.isoformat() if message.created_at else None,
        },
        story.project_id
    )
    
    return {
        "id": str(message.id),
        "author_type": message.author_type,
        "author_name": message.author_name,
        "content": message.content,
        "message_type": message.message_type,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


@router.delete("/{story_id}/messages")
async def clear_story_messages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Clear all messages in story channel."""
    from app.models import StoryMessage
    from sqlmodel import delete
    from app.websocket.connection_manager import connection_manager
    
    # Verify story exists
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Count messages before delete
    count_statement = (
        select(func.count())
        .select_from(StoryMessage)
        .where(StoryMessage.story_id == story_id)
    )
    count = session.exec(count_statement).one()
    
    # Delete all messages for this story
    session.exec(delete(StoryMessage).where(StoryMessage.story_id == story_id))
    session.commit()
    
    # Broadcast clear event via WebSocket
    await connection_manager.broadcast_to_project(
        {
            "type": "story_messages_cleared",
            "story_id": str(story_id),
        },
        story.project_id
    )
    
    return {"message": f"Deleted {count} messages", "deleted_count": count}


# ===== Story Review (BA Agent) =====
@router.post("/{story_id}/review")
async def review_story(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Trigger BA agent to review and suggest improvements for a story."""
    from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Publish review event to trigger BA agent
    producer = await get_kafka_producer()
    event = StoryEvent(
        event_type="story.review_requested",
        project_id=str(story.project_id),
        user_id=str(current_user.id),
        story_id=str(story.id),
        title=story.title,
    )
    await producer.publish(topic=KafkaTopics.STORY_EVENTS, event=event)
    
    return {"success": True, "message": "Review requested", "story_id": str(story_id)}


# ===== Agent Task Control =====
@router.post("/{story_id}/cancel")
async def cancel_story_task(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Cancel running agent task for story."""
    from app.models.base import StoryAgentState
    from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent
    import os
    import signal
    import subprocess
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Only allow cancel in InProgress or Review status
    if story.status not in [StoryStatus.IN_PROGRESS, StoryStatus.REVIEW]:
        raise HTTPException(status_code=400, detail="Can only cancel tasks in InProgress or Review status")
    
    # Kill dev server if running
    if story.running_pid:
        try:
            os.kill(story.running_pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
        story.running_pid = None
        story.running_port = None
    
    # Stop docker container if running (non-blocking)
    if story.db_container_id:
        try:
            await run_subprocess_async(
                ["docker", "stop", story.db_container_id],
                capture_output=True,
                timeout=30
            )
            await run_subprocess_async(
                ["docker", "rm", "-f", story.db_container_id],
                capture_output=True,
                timeout=30
            )
            logger.info(f"[cancel] Stopped docker container: {story.db_container_id}")
        except Exception as e:
            logger.warning(f"[cancel] Failed to stop docker container: {e}")
        story.db_container_id = None
        story.db_port = None
    
    # Clear container from in-memory registry
    from app.agents.developer_v2.src.utils.db_container import clear_container_from_registry
    clear_container_from_registry(str(story_id))
    
    # Update state to canceled and clear checkpoint (cancel = permanent stop)
    story.agent_state = StoryAgentState.CANCELED
    story.checkpoint_thread_id = None  # Clear checkpoint - cancel means no resume
    session.add(story)
    session.commit()
    
    # Broadcast state change via WebSocket (use story_state_changed, not story_message)
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "story_state_changed",
        "story_id": str(story_id),
        "agent_state": "CANCELED",
        "old_state": None,
    }, story.project_id)
    
    # Only publish Kafka event if agent is assigned (has something to cancel)
    if story.assigned_agent_id:
        producer = await get_kafka_producer()
        event = StoryEvent(
            event_type="story.cancel",
            project_id=str(story.project_id),
            user_id=str(current_user.id),
            story_id=str(story.id),
        )
        await producer.publish(topic=KafkaTopics.STORY_EVENTS, event=event)
    
    return {"success": True, "message": "Task cancelled"}


@router.post("/{story_id}/pause")
async def pause_story_task(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Pause running agent task for story (can be resumed later)."""
    from app.models.base import StoryAgentState
    from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Only allow pause in InProgress or Review status
    if story.status not in [StoryStatus.IN_PROGRESS, StoryStatus.REVIEW]:
        raise HTTPException(status_code=400, detail="Can only pause tasks in InProgress or Review status")
    
    # Allow pause for both PENDING and PROCESSING states
    if story.agent_state not in [StoryAgentState.PENDING, StoryAgentState.PROCESSING]:
        raise HTTPException(status_code=400, detail="Can only pause pending or processing tasks")
    
    # Update state to paused
    story.agent_state = StoryAgentState.PAUSED
    session.add(story)
    session.commit()
    
    # Broadcast WebSocket notification
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "story_message",
        "story_id": str(story_id),
        "content": f"⏸️ Task đã tạm dừng",
        "message_type": "system",
        "agent_state": "PAUSED",
    }, story.project_id)
    
    # Publish pause event to stop the agent
    producer = await get_kafka_producer()
    event = StoryEvent(
        event_type="story.pause",
        project_id=str(story.project_id),
        user_id=str(current_user.id),
        story_id=str(story.id),
    )
    await producer.publish(topic=KafkaTopics.STORY_EVENTS, event=event)
    
    return {"success": True, "message": "Task paused"}


@router.post("/{story_id}/resume")
async def resume_story_task(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Resume paused agent task for story."""
    from app.models.base import StoryAgentState
    from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Only allow resume in InProgress or Review status
    if story.status not in [StoryStatus.IN_PROGRESS, StoryStatus.REVIEW]:
        raise HTTPException(status_code=400, detail="Can only resume tasks in InProgress or Review status")
    
    if story.agent_state != StoryAgentState.PAUSED:
        raise HTTPException(status_code=400, detail="Can only resume paused tasks")
    
    # Update state to processing
    story.agent_state = StoryAgentState.PROCESSING
    session.add(story)
    session.commit()
    
    # Broadcast WebSocket notification
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "story_message",
        "story_id": str(story_id),
        "content": f"▶️ Đang tiếp tục task...",
        "message_type": "system",
        "agent_state": "PROCESSING",
    }, story.project_id)
    
    # Publish resume event to continue the agent
    producer = await get_kafka_producer()
    event = StoryEvent(
        event_type="story.resume",
        project_id=str(story.project_id),
        user_id=str(current_user.id),
        story_id=str(story.id),
        title=story.title,
    )
    await producer.publish(topic=KafkaTopics.STORY_EVENTS, event=event)
    
    return {"success": True, "message": "Task resumed"}


def _kill_processes_in_worktree(worktree_path: str) -> None:
    """Kill node processes that might be locking files (Windows only)."""
    import platform
    if platform.system() != "Windows":
        return
    try:
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True, timeout=10)
    except Exception:
        pass


def _cleanup_story_resources_sync(
    worktree_path: str | None = None,
    branch_name: str | None = None,
    main_workspace: str | None = None,
    checkpoint_thread_id: str | None = None,
) -> dict:
    """Cleanup story resources. Order: checkpoint → kill → prune → remove → delete dir → prune → branch."""
    from pathlib import Path
    import subprocess, shutil, platform, tempfile, time
    
    results = {"checkpoint": False, "worktree": False, "branch": False}
    
    # Delete checkpoint
    if checkpoint_thread_id:
        try:
            from sqlmodel import Session
            from sqlalchemy import text
            from app.core.db import engine
            with Session(engine) as db:
                db.execute(text("DELETE FROM checkpoint_writes WHERE thread_id = :tid"), {"tid": checkpoint_thread_id})
                db.execute(text("DELETE FROM checkpoint_blobs WHERE thread_id = :tid"), {"tid": checkpoint_thread_id})
                db.execute(text("DELETE FROM checkpoints WHERE thread_id = :tid"), {"tid": checkpoint_thread_id})
                db.commit()
            results["checkpoint"] = True
        except Exception:
            pass
    
    if worktree_path:
        _kill_processes_in_worktree(worktree_path)
    
    # Prune first
    if main_workspace and Path(main_workspace).exists():
        try:
            subprocess.run(["git", "worktree", "prune"], cwd=main_workspace, capture_output=True, timeout=10)
        except Exception:
            pass
    
    # Remove worktree
    if worktree_path:
        worktree = Path(worktree_path)
        if worktree.exists() and main_workspace and Path(main_workspace).exists():
            try:
                subprocess.run(["git", "worktree", "remove", str(worktree), "--force"], cwd=main_workspace, capture_output=True, timeout=30)
            except Exception:
                pass
        
        if worktree.exists():
            for attempt in range(3):
                try:
                    shutil.rmtree(worktree)
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(0.5 * (attempt + 1))
                        _kill_processes_in_worktree(worktree_path)
                    elif platform.system() == "Windows":
                        try:
                            empty_dir = tempfile.mkdtemp()
                            subprocess.run(["robocopy", empty_dir, str(worktree), "/mir", "/r:0", "/w:0", "/njh", "/njs", "/nc", "/ns", "/np", "/nfl", "/ndl"], capture_output=True, timeout=30)
                            shutil.rmtree(empty_dir, ignore_errors=True)
                            shutil.rmtree(worktree, ignore_errors=True)
                        except Exception:
                            pass
        
        # Prune again
        if main_workspace and Path(main_workspace).exists():
            try:
                subprocess.run(["git", "worktree", "prune"], cwd=main_workspace, capture_output=True, timeout=10)
            except Exception:
                pass
        
        results["worktree"] = not worktree.exists()
    
    # Delete branch
    if branch_name and main_workspace and Path(main_workspace).exists():
        try:
            result = subprocess.run(["git", "branch", "-D", branch_name], cwd=main_workspace, capture_output=True, timeout=10)
            results["branch"] = result.returncode == 0
        except Exception:
            pass
    
    return results


async def cleanup_story_resources(
    worktree_path: str | None = None,
    branch_name: str | None = None,
    main_workspace: str | None = None,
    checkpoint_thread_id: str | None = None,
) -> dict:
    """
    Async wrapper for cleanup_story_resources_sync.
    Runs blocking cleanup in thread pool executor.
    """
    import asyncio
    from functools import partial
    
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(
            _cleanup_story_resources_sync,
            worktree_path=worktree_path,
            branch_name=branch_name,
            main_workspace=main_workspace,
            checkpoint_thread_id=checkpoint_thread_id,
        )
    )


async def _cleanup_and_trigger_agent(
    worktree_path: str | None,
    branch_name: str | None,
    main_workspace: str | None,
    checkpoint_thread_id: str | None,
    story_id: str,
    project_id: str,
    user_id: str,
    story_title: str,
    story_status: str = "InProgress",
) -> None:
    """
    Background task for restart: cleanup ALL resources FIRST, then trigger agent.
    
    Order is critical:
    1. Delete checkpoint - prevent agent from loading stale state with error
    2. Delete worktree/branch - prevent conflict when agent creates new worktree
    3. THEN trigger agent - agent starts with clean slate
    
    Broadcasts sub_status for smooth UX:
    - "cleaning" while cleanup in progress
    - "starting" when triggering agent
    
    Args:
        story_status: Current story status ("InProgress" or "Review") to route to correct agent
    """
    import logging
    from uuid import UUID
    from app.websocket.connection_manager import connection_manager
    
    _logger = logging.getLogger(__name__)
    
    # Broadcast "cleaning" sub-status
    await connection_manager.broadcast_to_project({
        "type": "story_state_changed",
        "story_id": story_id,
        "agent_state": "PENDING",
        "sub_status": "cleaning",
    }, UUID(project_id))
    
    # 1. CLEANUP RESOURCES (conditional based on story status)
    # - InProgress (Developer): Full cleanup - worktree, branch, checkpoint
    # - Review (Tester): Partial cleanup - only checkpoint, keep worktree for reuse
    if story_status == "InProgress":
        results = await cleanup_story_resources(
            worktree_path=worktree_path,
            branch_name=branch_name,
            main_workspace=main_workspace,
            checkpoint_thread_id=checkpoint_thread_id,
        )
    else:
        # Tester - only cleanup checkpoint, keep worktree
        results = await cleanup_story_resources(
            worktree_path=None,
            branch_name=None,
            main_workspace=main_workspace,
            checkpoint_thread_id=checkpoint_thread_id,
        )
    _logger.info(f"[restart] Cleanup completed for {story_id} (status={story_status}): {results}")
    
    # Broadcast "starting" sub-status
    await connection_manager.broadcast_to_project({
        "type": "story_state_changed",
        "story_id": story_id,
        "agent_state": "PENDING",
        "sub_status": "starting",
    }, UUID(project_id))
    
    # 2. THEN trigger agent (all resources cleaned, agent starts fresh)
    # Route to correct agent based on story status:
    # - InProgress -> Developer
    # - Review -> Tester
    from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent
    
    producer = await get_kafka_producer()
    old_status = "Todo" if story_status == "InProgress" else "InProgress"
    event = StoryEvent(
        event_type="story.status.changed",
        project_id=project_id,
        user_id=user_id,
        story_id=story_id,
        old_status=old_status,
        new_status=story_status,
        title=story_title,
    )
    await producer.publish(topic=KafkaTopics.STORY_EVENTS, event=event)
    _logger.info(f"[restart] Agent triggered for {story_id} with status {story_status}")


@router.post("/{story_id}/restart")
async def restart_story_task(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Restart agent task for story (re-publish Kafka event).
    
    Flow:
    1. Reset state in DB immediately
    2. Broadcast "pending" state to UI
    3. Return response immediately
    4. Background: cleanup worktree -> then trigger agent
    """
    import asyncio
    from app.models.base import StoryAgentState
    from pathlib import Path
    import os
    import signal
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Only allow restart in InProgress or Review status
    if story.status not in [StoryStatus.IN_PROGRESS, StoryStatus.REVIEW]:
        raise HTTPException(status_code=400, detail="Can only restart tasks in InProgress or Review status")
    
    # Check if story is currently being processed - must cancel first
    if story.agent_state == StoryAgentState.PROCESSING:
        raise HTTPException(
            status_code=409,  # Conflict
            detail="Story đang được xử lý. Vui lòng Cancel trước khi Restart."
        )
    
    # Check if agent is busy with another task
    if story.assigned_agent_id:
        is_busy, reason = check_agent_busy(story.assigned_agent_id)
        if is_busy:
            raise HTTPException(
                status_code=409,  # Conflict
                detail=reason
            )
    
    # Stop dev server if running and notify UI
    if story.running_pid:
        old_port = story.running_port
        try:
            os.kill(story.running_pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
        
        # Broadcast dev server stopped
        from app.websocket.connection_manager import connection_manager
        await connection_manager.broadcast_to_project({
            "type": "story_state_changed",
            "story_id": str(story_id),
            "running_port": None,
            "running_pid": None,
            "old_port": old_port,
        }, story.project_id)
    
    # Stop docker container if running (non-blocking)
    if story.db_container_id:
        try:
            await run_subprocess_async(
                ["docker", "stop", story.db_container_id],
                capture_output=True,
                timeout=30
            )
            await run_subprocess_async(
                ["docker", "rm", "-f", story.db_container_id],
                capture_output=True,
                timeout=30
            )
            logger.info(f"[restart] Stopped docker container: {story.db_container_id}")
        except Exception as e:
            logger.warning(f"[restart] Failed to stop docker container: {e}")
    
    # Clear container from in-memory registry to ensure fresh start
    from app.agents.developer_v2.src.utils.db_container import clear_container_from_registry
    clear_container_from_registry(str(story_id))
    
    # Clear agent's in-memory cache for this story (critical for restart after cancel)
    from app.api.routes.agent_management import _manager_registry
    for manager in _manager_registry.values():
        for agent in manager.get_all_agents():
            if hasattr(agent, 'clear_story_cache'):
                agent.clear_story_cache(str(story_id))
                logger.info(f"[restart] Cleared agent cache for story {story_id}")
    
    # Get main workspace from Project
    from app.models import Project
    project = session.get(Project, story.project_id)
    main_workspace = None
    if project and project.project_path:
        backend_root = Path(__file__).resolve().parent.parent.parent.parent
        main_workspace = str((backend_root / project.project_path).resolve())
    
    # Capture values before clearing in DB
    worktree_path = story.worktree_path
    branch_name = story.branch_name
    checkpoint_thread_id = story.checkpoint_thread_id
    project_id = story.project_id
    story_title = story.title
    story_status = story.status.value  # "InProgress" or "Review" - for routing to correct agent
    
    # Reset state immediately
    story.agent_state = StoryAgentState.PENDING
    story.assigned_agent_id = None  # Clear so new agent will be assigned
    story.running_pid = None
    story.running_port = None
    story.checkpoint_thread_id = None
    story.db_container_id = None
    story.db_port = None
    
    # Only clear worktree for Developer (InProgress), keep for Tester (Review)
    if story.status == StoryStatus.IN_PROGRESS:
        story.worktree_path = None
        story.branch_name = None
    # else: Keep worktree_path and branch_name for Tester to reuse
    session.add(story)
    session.commit()
    
    # Clear old logs for fresh start
    from app.models.story_log import StoryLog
    session.exec(
        delete(StoryLog).where(StoryLog.story_id == story_id)
    )
    session.commit()
    logger.info(f"[restart] Cleared logs for story {story_id}")
    
    # Broadcast "pending" state to UI immediately with sub_status "queued"
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "story_state_changed",
        "story_id": str(story_id),
        "agent_state": "PENDING",
        "sub_status": "queued",  # Will change to "cleaning" -> "starting" in background task
        "old_state": None,
    }, project_id)
    
    # Schedule background task: cleanup THEN trigger agent
    async def _run_cleanup_with_error_handling():
        try:
            await _cleanup_and_trigger_agent(
                worktree_path,
                branch_name,
                main_workspace,
                checkpoint_thread_id,
                str(story_id),
                str(project_id),
                str(current_user.id),
                story_title,
                story_status,  # Pass status to route to correct agent (Developer/Tester)
            )
        except Exception as e:
            logger.error(f"[restart] Background task failed for {story_id}: {e}", exc_info=True)
    
    asyncio.create_task(_run_cleanup_with_error_handling())
    logger.info(f"[restart] Background task scheduled for {story_id}")
    
    return {"success": True, "message": "Task restarting..."}


@router.post("/{story_id}/dev-server/start")
async def start_dev_server(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Start dev server for story worktree."""
    import subprocess
    import socket
    import sys
    import os
    import time
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.worktree_path:
        raise HTTPException(status_code=400, detail="No worktree path for this story")
    
    # Logger helper - saves to DB and broadcasts via WebSocket
    async def log_to_story(message: str, level: str = "info"):
        from app.websocket.connection_manager import connection_manager
        from datetime import datetime, timezone
        from app.models.story_log import StoryLog, LogLevel
        
        # Save to database
        try:
            log_entry = StoryLog(
                story_id=story_id,
                content=f"[dev-server] {message}",
                level=LogLevel(level),
                node="dev-server"
            )
            session.add(log_entry)
            session.commit()
            session.refresh(log_entry)
        except Exception as e:
            print(f"Failed to save log to DB: {e}")
        
        # Broadcast via WebSocket (use story_log type, not story_message)
        await connection_manager.broadcast_to_project({
            "type": "story_log",
            "story_id": str(story_id),
            "content": f"[dev-server] {message}",
            "level": level,
            "node": "dev-server",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, story.project_id)
    
    is_windows = sys.platform == 'win32'
    
    # Helper: Kill process by PID
    def kill_process(pid: int, force: bool = False) -> bool:
        try:
            if is_windows:
                # Windows: use taskkill
                cmd = f"taskkill /F /PID {pid} /T" if force else f"taskkill /PID {pid} /T"
                subprocess.run(cmd, shell=True, capture_output=True)
            else:
                import signal
                os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
            return True
        except Exception:
            return False
    
    # Helper: Kill processes using a directory (Windows)
    def kill_processes_using_directory(directory: str) -> int:
        killed = 0
        if is_windows:
            try:
                # Find processes with handles to the directory using handle.exe or PowerShell
                result = subprocess.run(
                    f'powershell -Command "Get-Process | Where-Object {{$_.Path -like \'*node*\' -or $_.Path -like \'*pnpm*\'}} | ForEach-Object {{ if ($_.MainModule.FileName -or $_.Path) {{ $_.Id }} }}"',
                    shell=True, capture_output=True, text=True
                )
                for pid_str in result.stdout.strip().split('\n'):
                    if pid_str.strip().isdigit():
                        pid = int(pid_str.strip())
                        if kill_process(pid, force=True):
                            killed += 1
            except Exception:
                pass
        return killed
    
    # Helper: Kill process on port
    def kill_process_on_port(port: int) -> bool:
        try:
            if is_windows:
                result = subprocess.run(
                    f'netstat -ano | findstr :{port}',
                    shell=True, capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = int(parts[-1])
                        kill_process(pid, force=True)
                        return True
            else:
                result = subprocess.run(
                    f'lsof -ti:{port}',
                    shell=True, capture_output=True, text=True
                )
                if result.stdout.strip():
                    pid = int(result.stdout.strip())
                    kill_process(pid, force=True)
                    return True
        except Exception:
            pass
        return False
    
    # Force kill existing process if any
    if story.running_pid:
        await log_to_story(f"Killing existing dev server (PID: {story.running_pid})...")
        kill_process(story.running_pid, force=True)
        await asyncio.sleep(0.5)
    
    if story.running_port:
        await log_to_story(f"Killing any process on port {story.running_port}...")
        kill_process_on_port(story.running_port)
        await asyncio.sleep(0.5)
    
    # Clean up Next.js dev lock file (prevents "is another instance running?" error)
    next_lock = os.path.join(story.worktree_path, ".next", "dev", "lock")
    if os.path.exists(next_lock):
        try:
            os.remove(next_lock)
            await log_to_story("Removed stale Next.js lock file")
        except Exception:
            pass
    
    # Find free port
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    # Helper: Wait for port to be ready (async version to not block event loop)
    async def wait_for_port_async(port: int, timeout: float = 30.0) -> bool:
        import socket
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(('127.0.0.1', port))
                    return True
            except (socket.error, socket.timeout):
                await asyncio.sleep(0.5)
        return False
    
    port = find_free_port()
    await log_to_story(f"Starting dev server on port {port}...")
    
    # Start dev server with retry logic
    max_attempts = 2
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            process = subprocess.Popen(
                f"pnpm dev --port {port}" if is_windows else ["pnpm", "dev", "--port", str(port)],
                cwd=story.worktree_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=is_windows,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if is_windows else 0,
                env={**os.environ, "FORCE_COLOR": "0"},
            )
            
            # Wait for port to be ready (up to 15 seconds)
            await log_to_story(f"Waiting for server to be ready...")
            if await wait_for_port_async(port, timeout=15.0) and process.poll() is None:
                story.running_port = port
                story.running_pid = process.pid
                session.add(story)
                session.commit()
                
                await log_to_story(f"Dev server started on port {port} (PID: {process.pid})", "success")
                
                # Broadcast state change via WebSocket
                from app.websocket.connection_manager import connection_manager
                await connection_manager.broadcast_to_project({
                    "type": "story_state_changed",
                    "story_id": str(story_id),
                    "running_port": port,
                    "running_pid": process.pid,
                }, story.project_id)
                
                return {"success": True, "port": port, "pid": process.pid}
            else:
                if process.poll() is not None:
                    raise Exception(f"Process exited with code {process.returncode}")
                else:
                    raise Exception(f"Server started but port {port} not responding after 15s")
                
        except Exception as e:
            last_error = e
            await log_to_story(f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}", "warning")
            
            if attempt < max_attempts - 1:
                # Kill processes using the directory
                await log_to_story(f"Killing processes using directory...")
                killed = kill_processes_using_directory(story.worktree_path)
                if killed:
                    await log_to_story(f"Killed {killed} processes")
                await asyncio.sleep(1)
                
                # Try new port
                port = find_free_port()
                await log_to_story(f"Retrying with port {port}...")
    
    # All attempts failed
    await log_to_story(f"Failed to start dev server after {max_attempts} attempts: {str(last_error)}", "error")
    raise HTTPException(status_code=500, detail=f"Failed to start dev server: {str(last_error)}")


@router.post("/{story_id}/dev-server/stop")
async def stop_dev_server(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Stop dev server for story."""
    import os
    import sys
    import subprocess
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Logger helper - saves to DB and broadcasts via WebSocket
    async def log_to_story(message: str, level: str = "info"):
        from app.websocket.connection_manager import connection_manager
        from datetime import datetime, timezone
        from app.models.story_log import StoryLog, LogLevel
        
        # Save to database
        try:
            log_entry = StoryLog(
                story_id=story_id,
                content=f"[dev-server] {message}",
                level=LogLevel(level),
                node="dev-server"
            )
            session.add(log_entry)
            session.commit()
            session.refresh(log_entry)
        except Exception as e:
            print(f"Failed to save log to DB: {e}")
        
        # Broadcast via WebSocket (use story_log type, not story_message)
        await connection_manager.broadcast_to_project({
            "type": "story_log",
            "story_id": str(story_id),
            "content": f"[dev-server] {message}",
            "level": level,
            "node": "dev-server",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, story.project_id)
    
    if not story.running_pid and not story.running_port:
        await log_to_story("No dev server running")
        return {"success": True, "message": "No dev server running"}
    
    is_windows = sys.platform == 'win32'
    
    # Sync helper to kill processes (runs in thread pool)
    def _kill_processes_sync(pid: int | None, port: int | None) -> None:
        if pid:
            try:
                if is_windows:
                    subprocess.run(f"taskkill /F /PID {pid} /T", shell=True, capture_output=True)
                else:
                    import signal
                    os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
        
        if port:
            try:
                if is_windows:
                    result = subprocess.run(f'netstat -ano | findstr :{port}', shell=True, capture_output=True, text=True)
                    for line in result.stdout.strip().split('\n'):
                        parts = line.split()
                        if len(parts) >= 5 and parts[-1].isdigit():
                            subprocess.run(f"taskkill /F /PID {parts[-1]} /T", shell=True, capture_output=True)
                else:
                    result = subprocess.run(f'lsof -ti:{port}', shell=True, capture_output=True, text=True)
                    if result.stdout.strip():
                        import signal
                        os.kill(int(result.stdout.strip()), signal.SIGTERM)
            except Exception:
                pass
    
    # Run kill processes in thread pool (non-blocking)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _kill_processes_sync, story.running_pid, story.running_port)
    
    project_id = story.project_id
    story.running_pid = None
    story.running_port = None
    session.add(story)
    session.commit()
    
    await log_to_story("Dev server stopped", "success")
    
    # Broadcast state change via WebSocket
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "story_state_changed",
        "story_id": str(story_id),
        "running_port": None,
        "running_pid": None,
    }, project_id)
    
    return {"success": True, "message": "Dev server stopped"}


@router.get("/{story_id}/logs")
async def get_story_logs(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500)
) -> Any:
    """Get story logs from StoryLog table."""
    from app.models import StoryLog
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get logs from StoryLog table
    statement = (
        select(StoryLog)
        .where(StoryLog.story_id == story_id)
        .order_by(StoryLog.created_at.desc())
        .limit(limit)
    )
    logs = session.exec(statement).all()
    
    return {
        "logs": [
            {
                "id": str(log.id),
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "level": log.level.value if log.level else "info",
                "node": log.node or "",
                "content": log.content,
            }
            for log in reversed(logs)
        ]
    }


def _get_story_diffs_sync(worktree_path: str) -> dict:
    """Sync function to get git diffs - runs in thread pool."""
    import subprocess
    
    # Helper: Detect default branch (master or main)
    def get_default_branch(cwd: str) -> str:
        for branch in ['master', 'main']:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                cwd=cwd, capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return branch
        return 'master'  # fallback
    
    base_branch = get_default_branch(worktree_path)
    diff_ref = f"{base_branch}...HEAD"
    
    # Get changed files with line stats
    result = subprocess.run(
        ["git", "diff", "--numstat", diff_ref],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    files = []
    diff_output = ""
    total_additions = 0
    total_deletions = 0
    
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("\t")
                if len(parts) == 3:
                    additions, deletions, filename = parts
                    add_count = int(additions) if additions != '-' else 0
                    del_count = int(deletions) if deletions != '-' else 0
                    total_additions += add_count
                    total_deletions += del_count
                    files.append({
                        "filename": filename,
                        "additions": add_count,
                        "deletions": del_count,
                        "binary": additions == '-'
                    })
        
        # Get file statuses (A/M/D)
        status_result = subprocess.run(
            ["git", "diff", "--name-status", diff_ref],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if status_result.returncode == 0:
            status_map = {}
            for line in status_result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        status_map[parts[1]] = parts[0]
            for f in files:
                f["status"] = status_map.get(f["filename"], "M")
        
        # Get full diff
        diff_result = subprocess.run(
            ["git", "diff", diff_ref],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        diff_output = diff_result.stdout if diff_result.returncode == 0 else ""
    else:
        # Fallback: show uncommitted changes
        result = subprocess.run(
            ["git", "diff", "--numstat"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    if len(parts) == 3:
                        additions, deletions, filename = parts
                        add_count = int(additions) if additions != '-' else 0
                        del_count = int(deletions) if deletions != '-' else 0
                        total_additions += add_count
                        total_deletions += del_count
                        files.append({
                            "filename": filename,
                            "additions": add_count,
                            "deletions": del_count,
                            "status": "M",
                            "binary": additions == '-'
                        })
            
            diff_result = subprocess.run(
                ["git", "diff"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            diff_output = diff_result.stdout if diff_result.returncode == 0 else ""
    
    return {
        "files": files,
        "file_count": len(files),
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "diff": diff_output,
        "base_branch": base_branch
    }


@router.get("/{story_id}/diffs")
async def get_story_diffs(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Get git diff for story worktree compared to base branch."""
    import subprocess
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.worktree_path:
        return {"files": [], "file_count": 0, "diff": "", "base_branch": None}
    
    try:
        # Run blocking git operations in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _get_story_diffs_sync, story.worktree_path)
        return result
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get diffs: {str(e)}")


@router.get("/{story_id}/file-diff")
async def get_file_diff(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    file_path: str = Query(..., description="Path to file relative to worktree")
) -> Any:
    """Get git diff for a specific file in story worktree."""
    import subprocess
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.worktree_path:
        return {"file_path": file_path, "diff": "", "has_changes": False, "error": "No worktree"}
    
    # Helper: Detect default branch
    def get_default_branch(cwd: str) -> str:
        for branch in ['master', 'main']:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                cwd=cwd, capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return branch
        return 'master'
    
    try:
        base_branch = get_default_branch(story.worktree_path)
        
        # Try diff against base branch first
        result = subprocess.run(
            ["git", "diff", f"{base_branch}...HEAD", "--", file_path],
            cwd=story.worktree_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        diff_output = result.stdout if result.returncode == 0 else ""
        
        # If no diff against branch, check uncommitted changes
        if not diff_output.strip():
            result = subprocess.run(
                ["git", "diff", "--", file_path],
                cwd=story.worktree_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            diff_output = result.stdout if result.returncode == 0 else ""
        
        # Also check staged changes if still no diff
        if not diff_output.strip():
            result = subprocess.run(
                ["git", "diff", "--cached", "--", file_path],
                cwd=story.worktree_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            diff_output = result.stdout if result.returncode == 0 else ""
        
        return {
            "file_path": file_path,
            "diff": diff_output,
            "has_changes": bool(diff_output.strip()),
            "base_branch": base_branch
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file diff: {str(e)}")


@router.get("/{story_id}/preview-files")
async def get_preview_files(
    story_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """
    Get workspace files for Sandpack preview.
    Returns files formatted for Sandpack: { "/path/to/file": "content" }
    """
    import os
    from pathlib import Path
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.worktree_path:
        return {"files": {}, "error": "No workspace for this story"}
    
    workspace_path = Path(story.worktree_path)
    if not workspace_path.exists():
        return {"files": {}, "error": "Workspace not found"}
    
    # Files to include for preview (frontend files only)
    INCLUDE_EXTENSIONS = {'.tsx', '.ts', '.jsx', '.js', '.css', '.html', '.json', '.md'}
    EXCLUDE_DIRS = {'node_modules', '.git', '.next', 'dist', 'build', '.turbo', '.cache'}
    MAX_FILE_SIZE = 100 * 1024  # 100KB max per file
    MAX_FILES = 50  # Limit number of files
    
    files = {}
    file_count = 0
    
    try:
        for root, dirs, filenames in os.walk(workspace_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            rel_root = Path(root).relative_to(workspace_path)
            
            for filename in filenames:
                if file_count >= MAX_FILES:
                    break
                    
                ext = Path(filename).suffix.lower()
                if ext not in INCLUDE_EXTENSIONS:
                    continue
                
                file_path = Path(root) / filename
                rel_path = rel_root / filename if str(rel_root) != '.' else Path(filename)
                
                try:
                    if file_path.stat().st_size > MAX_FILE_SIZE:
                        continue
                    
                    content = file_path.read_text(encoding='utf-8')
                    # Sandpack expects paths starting with /
                    sandpack_path = '/' + str(rel_path).replace('\\', '/')
                    files[sandpack_path] = content
                    file_count += 1
                except Exception:
                    # Skip files that can't be read
                    continue
        
        return {
            "files": files,
            "file_count": len(files),
            "workspace_path": str(workspace_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read workspace files: {str(e)}")


# ===== Preview Proxy =====
PROXY_HEADERS_SKIP = {'host', 'content-length', 'transfer-encoding', 'connection'}

@router.api_route("/{story_id}/preview/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_preview(
    story_id: uuid.UUID,
    path: str,
    request: Request,
    session: SessionDep,
    token: Optional[str] = Query(None),  # Accept token from query param for iframe
):
    """
    Proxy requests to the story's dev server.
    Allows full Next.js preview with API routes, hot reload, etc.
    Token can be passed via query param for iframe support.
    Static assets (_next/static, images, etc.) skip auth for performance.
    """
    # Skip auth for static assets (CSS, JS, images, fonts)
    static_prefixes = ('_next/', 'static/', 'images/', 'fonts/', 'favicon')
    is_static = path.startswith(static_prefixes) or path.endswith(('.css', '.js', '.png', '.jpg', '.svg', '.ico', '.woff', '.woff2'))
    
    if not is_static:
        # Validate token - from query param (iframe) or header
        auth_token = token
        if not auth_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                auth_token = auth_header[7:]
        
        if not auth_token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        from app.core.security import decode_access_token
        try:
            decode_access_token(auth_token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.running_port:
        raise HTTPException(
            status_code=400, 
            detail="Dev server not running. Start it first via the Start Server button."
        )
    
    # Build target URL
    target_url = f"http://localhost:{story.running_port}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    # Filter headers
    headers = {
        k: v for k, v in request.headers.items() 
        if k.lower() not in PROXY_HEADERS_SKIP
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Forward the request
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body() if request.method in ["POST", "PUT", "PATCH"] else None,
            )
            
            # Filter response headers
            response_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in {'content-encoding', 'transfer-encoding', 'content-length'}
            }
            
            content = resp.content
            content_type = resp.headers.get('content-type', 'text/html')
            
            # Inject <base> tag for HTML responses to fix relative paths
            if 'text/html' in content_type and b'<head>' in content:
                base_url = f"/api/v1/stories/{story_id}/preview/"
                base_tag = f'<base href="{base_url}">'.encode()
                content = content.replace(b'<head>', b'<head>' + base_tag, 1)
            
            return Response(
                content=content,
                status_code=resp.status_code,
                headers=response_headers,
                media_type=content_type,
            )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502, 
            detail=f"Cannot connect to dev server on port {story.running_port}. Server may have crashed."
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Dev server request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")


# ===== Merge Branch Management (Pure Git) =====

@router.post("/{story_id}/merge-to-main")
async def merge_story_to_main(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Merge story branch to main/master using pure git (no GitHub CLI).
    
    Flow:
    1. Trigger Developer agent to:
       - Merge main into story branch (resolve conflicts if any)
       - If success, merge story branch into main
       - Cleanup worktree/branch after merge
    2. Update pr_state based on result
    """
    from pathlib import Path
    from app.models import Project
    from app.models.base import StoryAgentState
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Validate story state
    if story.agent_state != StoryAgentState.FINISHED:
        raise HTTPException(status_code=400, detail="Story must be FINISHED before merging")
    
    if not story.branch_name:
        raise HTTPException(status_code=400, detail="Story has no branch to merge")
    
    if story.merge_status == "merged":
        raise HTTPException(status_code=400, detail="Story already merged")
    
    # Get main workspace from project
    project = session.get(Project, story.project_id)
    if not project or not project.project_path:
        raise HTTPException(status_code=400, detail="Project has no workspace path")
    
    backend_root = Path(__file__).resolve().parent.parent.parent.parent
    main_workspace = str((backend_root / project.project_path).resolve())
    
    if not Path(main_workspace).exists():
        raise HTTPException(status_code=400, detail="Main workspace not found")
    
    # Update state to indicate merge in progress
    story.pr_state = "merging"
    session.add(story)
    session.commit()
    
    # Broadcast WebSocket event for UI to show "merging" state
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "story_state_changed",
        "story_id": str(story_id),
        "pr_state": "merging",
    }, story.project_id)
    
    # Trigger Developer agent to handle merge (non-blocking)
    asyncio.create_task(_trigger_merge_task(
        str(story_id), 
        str(story.project_id),
        story.branch_name,
        story.worktree_path,
        main_workspace
    ))
    
    logger.info(f"[merge-to-main] Triggered merge for story {story_id}")
    
    return {
        "success": True,
        "pr_state": "merging",
        "message": "Developer agent will merge branch to main. Check pr_state for result."
    }


async def _trigger_merge_task(story_id: str, project_id: str, branch_name: str, worktree_path: str | None, main_workspace: str):
    """Background task: Trigger Developer agent to merge branch."""
    try:
        from app.core.agent.router import route_story_event
        from app.kafka.event_schemas import AgentTaskType
        
        # Small delay to ensure DB commit is visible
        await asyncio.sleep(1)
        
        # Route to available Developer agent for merge task
        await route_story_event(
            story_id=story_id,
            project_id=project_id,
            task_type=AgentTaskType.REVIEW_PR,
            priority="high",
            metadata={
                "branch_name": branch_name,
                "worktree_path": worktree_path,
                "main_workspace": main_workspace
            }
        )
        logger.info(f"[merge-to-main] Triggered merge task for story {story_id}")
    except Exception as e:
        logger.error(f"[merge-to-main] Failed to trigger merge task: {e}")
        # Update story state to indicate failure
        from uuid import UUID
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Story
        
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id))
            if story:
                story.pr_state = "error"
                story.merge_status = "merge_failed"
                session.add(story)
                session.commit()


@router.get("/{story_id}/merge-status")
async def get_merge_status(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Get current merge status of story."""
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    return {
        "pr_state": story.pr_state,
        "merge_status": story.merge_status,
        "branch_name": story.branch_name,
        "worktree_path": story.worktree_path
    }
