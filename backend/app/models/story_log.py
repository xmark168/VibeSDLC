"""StoryLog model for persisting story activity logs."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID
from enum import Enum

from sqlalchemy import Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, Column

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.story import Story


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class StoryLog(BaseModel, table=True):
    __tablename__ = "story_logs"

    story_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("stories.id", ondelete="CASCADE"),
            index=True,
            nullable=False
        )
    )
    
    content: str = Field(sa_column=Column(Text, nullable=False))
    
    level: LogLevel = Field(
        default=LogLevel.INFO,
        sa_column=Column(
            SQLEnum(LogLevel, name='loglevel', native_enum=True, values_callable=lambda x: [e.value for e in x]),
            nullable=False
        )
    )
    
    node: str = Field(default="", nullable=True)  # e.g., "dev-server", "plan", "implement"
    
    # Relationship
    story: Optional["Story"] = Relationship(back_populates="logs")
