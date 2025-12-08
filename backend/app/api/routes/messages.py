import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import FileResponse
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
from app.core.config import DOCUMENT_UPLOAD_LIMITS

logger = logging.getLogger(__name__)

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
    
    # Populate agent_name for each message
    result = []
    for msg in rows:
        msg_dict = {
            "id": msg.id,
            "project_id": msg.project_id,
            "author_type": msg.author_type,
            "user_id": msg.user_id,
            "agent_id": msg.agent_id,
            "agent_name": None,
            "content": msg.content,
            "message_type": msg.message_type,
            "structured_data": msg.structured_data,
            "message_metadata": msg.message_metadata,
            "attachments": msg.attachments,
            "created_at": msg.created_at,
            "updated_at": msg.updated_at,
        }
        
        # Get agent name if agent_id exists
        if msg.agent_id:
            agent = session.get(AgentModel, msg.agent_id)
            if agent:
                msg_dict["agent_name"] = agent.human_name or agent.name
        
        # Also check message_metadata for agent_name (fallback)
        if not msg_dict["agent_name"] and msg.message_metadata:
            msg_dict["agent_name"] = msg.message_metadata.get("agent_name")
        
        result.append(ChatMessagePublic(**msg_dict))
    
    return ChatMessagesPublic(data=result, count=count)


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


@router.post("/with-file", response_model=ChatMessagePublic, status_code=status.HTTP_201_CREATED)
async def create_message_with_file(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: UUID = Form(...),
    content: str = Form(...),
    file: UploadFile | None = File(None),
) -> Any:
    """Create a message with optional file attachment.
    
    Supports .docx files up to 10MB.
    The file content will be extracted and included in the message for BA processing.
    """
    # Validate project
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    attachment = None
    
    if file:
        # Validate file size (read file first)
        file_bytes = await file.read()
        
        if len(file_bytes) > DOCUMENT_UPLOAD_LIMITS["max_file_size"]:
            max_mb = DOCUMENT_UPLOAD_LIMITS["max_file_size"] // 1024 // 1024
            raise HTTPException(
                status_code=413,
                detail=f"File quá lớn. Giới hạn: {max_mb} MB"
            )
        
        # Validate extension
        ext = Path(file.filename).suffix.lower() if file.filename else ""
        if ext not in DOCUMENT_UPLOAD_LIMITS["allowed_extensions"]:
            raise HTTPException(
                status_code=400,
                detail=f"Định dạng file không hỗ trợ. Chấp nhận: {', '.join(DOCUMENT_UPLOAD_LIMITS['allowed_extensions'])}"
            )
        
        # Extract text from document
        try:
            from app.utils.document_parser import extract_text, sanitize_filename
            extracted_text = extract_text(file.filename, file_bytes)
        except Exception as e:
            logger.error(f"Failed to extract text from {file.filename}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Không thể đọc nội dung file: {str(e)}"
            )
        
        # Sanitize filename for safe storage
        sanitized_name = sanitize_filename(file.filename)
        
        # Validate extracted text length
        if len(extracted_text) > DOCUMENT_UPLOAD_LIMITS["max_text_length"]:
            raise HTTPException(
                status_code=400,
                detail=f"Nội dung file quá dài ({len(extracted_text):,} ký tự). Giới hạn: {DOCUMENT_UPLOAD_LIMITS['max_text_length']:,} ký tự"
            )
        
        # Save file to disk
        upload_dir = Path(f"projects/{project_id}/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{sanitized_name}"
        file_path = upload_dir / safe_filename
        file_path.write_bytes(file_bytes)
        
        logger.info(f"Saved uploaded file: {file_path} ({len(file_bytes)} bytes)")
        
        # Log extracted text for debugging
        logger.info(f"=== EXTRACTED TEXT FROM {file.filename} ({len(extracted_text)} chars) ===")
        logger.info(f"CONTENT PREVIEW (first 500 chars):\n{extracted_text[:500]}")
        logger.info(f"=== END EXTRACTED TEXT ===")
        
        attachment = {
            "type": "document",
            "filename": file.filename,
            "file_path": str(file_path),
            "file_size": len(file_bytes),
            "mime_type": file.content_type,
            "extracted_text": extracted_text,
        }
    
    # Create message
    obj = MessageModel(
        project_id=project_id,
        content=content,
        author_type=AuthorType.USER,
        user_id=current_user.id,
        visibility=MessageVisibility.USER_MESSAGE,
        message_type="text" if not attachment else "document_upload",
        attachments=[attachment] if attachment else None,
    )
    session.add(obj)
    session.commit()
    session.refresh(obj)
    
    logger.info(f"Created message {obj.id} with attachment: {attachment['filename'] if attachment else 'none'}")
    
    # Publish to Kafka for agent routing
    try:
        from app.kafka import get_kafka_producer, KafkaTopics, UserMessageEvent
        
        producer = await get_kafka_producer()
        
        user_message_event = UserMessageEvent(
            message_id=obj.id,
            project_id=str(obj.project_id),
            user_id=str(current_user.id),
            content=obj.content,
            message_type=obj.message_type or "text",
            attachments=[attachment] if attachment else None,
        )
        
        await producer.publish(
            topic=KafkaTopics.USER_MESSAGES,
            event=user_message_event,
        )
        logger.info(f"Published message {obj.id} to Kafka")
    except Exception as e:
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


@router.get("/{message_id}/attachments/{attachment_index}/download")
async def download_attachment(
    session: SessionDep,
    current_user: CurrentUser,
    message_id: UUID,
    attachment_index: int = 0,
) -> FileResponse:
    """Download a file attachment from a message.
    
    Args:
        message_id: The message ID containing the attachment
        attachment_index: Index of the attachment (default 0 for first file)
    
    Returns:
        The file as a download response
    """
    # Get message
    msg = session.get(MessageModel, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check attachments exist
    if not msg.attachments or len(msg.attachments) == 0:
        raise HTTPException(status_code=404, detail="No attachments found")
    
    if attachment_index >= len(msg.attachments):
        raise HTTPException(status_code=404, detail="Attachment index out of range")
    
    attachment = msg.attachments[attachment_index]
    file_path = Path(attachment.get("file_path", ""))
    
    if not file_path.exists():
        logger.error(f"Attachment file not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Return file for download
    return FileResponse(
        path=file_path,
        filename=attachment.get("filename", "download"),
        media_type=attachment.get("mime_type", "application/octet-stream"),
    )
