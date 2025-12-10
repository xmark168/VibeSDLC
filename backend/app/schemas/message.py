"""Message-related schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlmodel import SQLModel

from app.models import AuthorType


class ChatMessageBase(SQLModel):
    content: str
    author_type: AuthorType


class ChatMessageCreate(ChatMessageBase):
    project_id: UUID
    agent_id: Optional[UUID] = None
    message_type: Optional[str] = "text"
    structured_data: Optional[dict] = None
    attachments: Optional[list[dict]] = None


class ChatMessageUpdate(SQLModel):
    content: Optional[str] = None


class ChatMessagePublic(SQLModel):
    id: UUID
    project_id: UUID
    author_type: AuthorType
    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None  # Agent's human-readable name
    persona_avatar: Optional[str] = None  # Agent's persona avatar URL
    content: str
    message_type: Optional[str] = "text"
    structured_data: Optional[Any] = None
    message_metadata: Optional[dict] = None
    attachments: Optional[list[dict]] = None
    created_at: datetime
    updated_at: datetime


class ChatMessagesPublic(SQLModel):
    data: list[ChatMessagePublic]
    count: int
