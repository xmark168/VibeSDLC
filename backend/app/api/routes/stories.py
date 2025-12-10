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
from app.schemas.story import BulkRankUpdateRequest
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
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Kill dev server if running
    if story.running_pid:
        try:
            os.kill(story.running_pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
        story.running_pid = None
        story.running_port = None
    
    # Update state to canceled and clear checkpoint (cancel = permanent stop)
    story.agent_state = StoryAgentState.CANCELED
    story.checkpoint_thread_id = None  # Clear checkpoint - cancel means no resume
    session.add(story)
    session.commit()
    
    # Broadcast WebSocket notification
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "story_message",
        "story_id": str(story_id),
        "content": f"🛑 Task đã bị hủy",
        "message_type": "system",
        "agent_state": "canceled",
    }, story.project_id)
    
    # Publish cancel event to actually stop the agent
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
        "agent_state": "paused",
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
        "agent_state": "processing",
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


@router.post("/{story_id}/restart")
async def restart_story_task(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Restart agent task for story (re-publish Kafka event)."""
    from app.models.base import StoryAgentState
    from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent
    import subprocess
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Discard old changes in worktree (if exists)
    if story.worktree_path:
        try:
            # Reset all changes to HEAD
            subprocess.run(
                ["git", "checkout", "--", "."],
                cwd=story.worktree_path,
                capture_output=True,
                timeout=30
            )
            # Remove untracked files
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=story.worktree_path,
                capture_output=True,
                timeout=30
            )
        except Exception as e:
            # Log but don't fail - worktree might not exist
            import logging
            logging.warning(f"Failed to cleanup worktree for story {story_id}: {e}")
    
    # Reset state and clear checkpoint (start fresh, not resume)
    story.agent_state = StoryAgentState.PENDING
    story.running_pid = None
    story.running_port = None
    story.checkpoint_thread_id = None  # Clear checkpoint to start fresh
    session.add(story)
    session.commit()
    
    # Clear any leftover cancel/pause signals from previous run
    from app.agents.core.task_registry import clear_signals
    clear_signals(str(story_id))
    
    # Broadcast WebSocket notification
    from app.websocket.connection_manager import connection_manager
    await connection_manager.broadcast_to_project({
        "type": "story_message",
        "story_id": str(story_id),
        "content": f"🔄 Đang chạy lại task...",
        "message_type": "system",
        "agent_state": "pending",
    }, story.project_id)
    
    # Publish event to trigger agent
    producer = await get_kafka_producer()
    event = StoryEvent(
        event_type="story.status.changed",
        project_id=str(story.project_id),
        user_id=str(current_user.id),
        story_id=str(story.id),
        old_status="Todo",
        new_status="InProgress",
        title=story.title,
    )
    await producer.publish(topic=KafkaTopics.STORY_EVENTS, event=event)
    
    return {"success": True, "message": "Task restarted"}


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
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.worktree_path:
        raise HTTPException(status_code=400, detail="No worktree path for this story")
    
    # Already running
    if story.running_pid and story.running_port:
        return {"success": True, "port": story.running_port, "message": "Dev server already running"}
    
    # Find free port
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    port = find_free_port()
    
    # Start dev server
    try:
        process = subprocess.Popen(
            ["pnpm", "dev", "--port", str(port)],
            cwd=story.worktree_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0,
        )
        
        story.running_port = port
        story.running_pid = process.pid
        session.add(story)
        session.commit()
        
        return {"success": True, "port": port, "pid": process.pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start dev server: {str(e)}")


@router.post("/{story_id}/dev-server/stop")
async def stop_dev_server(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Stop dev server for story."""
    import os
    import signal
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.running_pid:
        return {"success": True, "message": "No dev server running"}
    
    try:
        os.kill(story.running_pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass
    
    story.running_pid = None
    story.running_port = None
    session.add(story)
    session.commit()
    
    return {"success": True, "message": "Dev server stopped"}


@router.get("/{story_id}/logs")
async def get_story_logs(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500)
) -> Any:
    """Get agent logs/messages for story."""
    from app.models import StoryMessage
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Get messages as logs
    statement = (
        select(StoryMessage)
        .where(StoryMessage.story_id == story_id)
        .order_by(StoryMessage.created_at.desc())
        .limit(limit)
    )
    messages = session.exec(statement).all()
    
    return {
        "logs": [
            {
                "id": str(msg.id),
                "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                "author": msg.author_name,
                "type": msg.message_type,
                "content": msg.content,
            }
            for msg in reversed(messages)
        ]
    }


@router.get("/{story_id}/diffs")
async def get_story_diffs(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    story_id: uuid.UUID
) -> Any:
    """Get git diff for story worktree."""
    import subprocess
    
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.worktree_path:
        return {"files": [], "diff": ""}
    
    try:
        # Get changed files
        result = subprocess.run(
            ["git", "diff", "--name-status", "main...HEAD"],
            cwd=story.worktree_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        files = []
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        status, filename = parts
                        files.append({
                            "status": status,  # A=Added, M=Modified, D=Deleted
                            "filename": filename
                        })
        
        # Get full diff
        diff_result = subprocess.run(
            ["git", "diff", "main...HEAD"],
            cwd=story.worktree_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "files": files,
            "file_count": len(files),
            "diff": diff_result.stdout if diff_result.returncode == 0 else ""
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get diffs: {str(e)}")
