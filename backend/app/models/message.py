"""Message and AgentConversation models."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import JSON, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, Column

from app.models.base import BaseModel, AuthorType, MessageVisibility

if TYPE_CHECKING:
    from app.models.agent import Agent


class Message(BaseModel, table=True):
    __tablename__ = "messages"

    project_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE", use_alter=True, name="fk_messages_project_id"),
            index=True,
            nullable=False
        )
    )

    author_type: AuthorType = Field(default=AuthorType.USER, nullable=False)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", ondelete="SET NULL")

    content: str

    visibility: MessageVisibility = Field(
        default=MessageVisibility.USER_MESSAGE,
        sa_column=Column(
            SQLEnum(MessageVisibility, name='messagevisibility', native_enum=True, values_callable=lambda x: [e.value for e in x]),
            nullable=False
        )
    )

    message_type: str = Field(default="text", nullable=True)
    structured_data: dict | None = Field(default=None, sa_column=Column(JSON))
    message_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    
    # File attachments (documents, images, etc.)
    # Format: [{"type": "document", "filename": "...", "file_path": "...", "file_size": 123, "mime_type": "...", "extracted_text": "..."}]
    attachments: list[dict] | None = Field(default=None, sa_column=Column(JSON))

    agent: Optional["Agent"] = Relationship(back_populates="messages")


class AgentConversation(BaseModel, table=True):
    __tablename__ = "agent_conversations"

    project_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE", use_alter=True, name="fk_agent_conversations_project_id"),
            index=True,
            nullable=False
        )
    )
    execution_id: UUID | None = Field(default=None, foreign_key="agent_executions.id", ondelete="CASCADE")

    sender_type: str = Field(nullable=False)
    sender_name: str = Field(nullable=False)
    recipient_type: str | None = Field(default=None)
    recipient_name: str | None = Field(default=None)

    message_type: str = Field(nullable=False)
    content: str = Field(sa_column=Column(Text))
    structured_data: dict | None = Field(default=None, sa_column=Column(JSON))

    extra_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
