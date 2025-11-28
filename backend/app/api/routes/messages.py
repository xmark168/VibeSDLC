from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select, func, delete

from app.api.deps import CurrentUser, SessionDep
from app.models import Message as MessageModel, Project, Agent as AgentModel, AuthorType, MessageVisibility
from app.schemas import (
    ChatMessageCreate,
    ChatMessageUpdate,
    ChatMessagePublic,
    ChatMessagesPublic,
    Message,
)

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/", response_model=ChatMessagesPublic)
def list_messages(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID = Query(...),
    skip: int = 0,
    limit: int = 500,  # Increased default from 100 to handle more messages
) -> Any:
    # Validate project
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = (
        select(MessageModel)
        .where(MessageModel.project_id == project_id)
        .where(MessageModel.visibility == MessageVisibility.USER_MESSAGE)  # Only return user-facing messages
        .order_by(MessageModel.created_at.asc())
    )
    count_stmt = (
        select(func.count())
        .select_from(MessageModel)
        .where(MessageModel.project_id == project_id)
        .where(MessageModel.visibility == MessageVisibility.USER_MESSAGE)  # Only count user-facing messages
    )

    count = session.exec(count_stmt).one()
    rows = session.exec(stmt.offset(skip).limit(limit)).all()
    return ChatMessagesPublic(data=rows, count=count)


@router.post("/", response_model=ChatMessagePublic, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_in: ChatMessageCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    # Validate project
    project = session.get(Project, message_in.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    data = message_in.model_dump()

    # Resolve author
    if message_in.author_type == AuthorType.USER:
        data["user_id"] = current_user.id
        data["agent_id"] = None
    elif message_in.author_type == AuthorType.AGENT:
        if not message_in.agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required when author_type=agent")
        agent = session.get(AgentModel, message_in.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        data["user_id"] = None
        data["agent_id"] = message_in.agent_id
    else:
        # If you later add SYSTEM/TOOL, set both IDs to None
        data["user_id"] = None
        data["agent_id"] = None
    
    # Set visibility - all messages created via API are user-facing
    data["visibility"] = MessageVisibility.USER_MESSAGE

    obj = MessageModel(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)

    # Publish user messages to Kafka for agent routing
    if message_in.author_type == AuthorType.USER:
        try:
            from app.kafka import get_kafka_producer, KafkaTopics, UserMessageEvent

            producer = await get_kafka_producer()

            user_message_event = UserMessageEvent(
                message_id=obj.id,
                project_id=str(obj.project_id),
                user_id=str(current_user.id),
                content=obj.content,
                message_type=message_in.message_type or "text",
            )

            await producer.publish(
                topic=KafkaTopics.USER_MESSAGES,
                event=user_message_event,
            )
        except Exception as e:
            # Log error but don't fail the API call
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to publish message to Kafka: {e}")

    return obj


@router.patch("/{message_id}", response_model=ChatMessagePublic)
def update_message(
    message_id: UUID,
    message_in: ChatMessageUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    obj = session.get(MessageModel, message_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Message not found")

    # Only allow the original user to edit their own messages (optional policy)
    if obj.author_type == AuthorType.USER and obj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    update_data = message_in.model_dump(exclude_unset=True)
    obj.sqlmodel_update(update_data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    obj = session.get(MessageModel, message_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Message not found")

    # Only allow the original user to delete their own messages; admins can delete
    if obj.author_type == AuthorType.USER and obj.user_id != current_user.id:
        from app.models import Role
        if current_user.role != Role.ADMIN:
            raise HTTPException(status_code=403, detail="Not allowed")

    session.delete(obj)
    session.commit()
    return None


@router.delete("/by-project/{project_id}", response_model=Message)
def delete_all_messages_by_project(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    # Validate project
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only admin or project owner can clear messages
    from app.models import Role
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    # Count existing messages
    count_stmt = select(func.count()).select_from(MessageModel).where(MessageModel.project_id == project_id)
    count = session.exec(count_stmt).one() or 0

    # Bulk delete
    session.exec(delete(MessageModel).where(MessageModel.project_id == project_id))
    session.commit()

    return Message(message=f"Deleted {count} messages for project {project_id}")
