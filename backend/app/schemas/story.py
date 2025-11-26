"""Story-related schemas."""

from uuid import UUID
from datetime import datetime, date
from sqlmodel import Field, SQLModel
from typing import Optional, Literal
from app.models import StoryStatus, StoryType


class StoryBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    story_type: StoryType = Field(default=StoryType.USER_STORY)
    priority: int = Field(default=3, ge=1, le=5)
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)
    assigned_to: Optional[UUID] = None
    sprint_id: Optional[UUID] = None
    epic_id: Optional[UUID] = None
    parent_story_id: Optional[UUID] = None
    tags: Optional[list[str]] = Field(default_factory=list)
    acceptance_criteria: Optional[str] = None
    business_value: Optional[int] = Field(None, ge=1, le=100)
    risk_level: Optional[Literal["low", "medium", "high", "critical"]] = None
    target_release: Optional[str] = None
    dependencies: Optional[list[UUID]] = Field(default_factory=list)
    blocked_by: Optional[UUID] = None
    blocking: Optional[list[UUID]] = Field(default_factory=list)
    attachments: Optional[list[str]] = Field(default_factory=list)
    labels: Optional[list[str]] = Field(default_factory=list)


class StoryCreate(StoryBase):
    project_id: UUID


class StoryPublic(StoryBase):
    id: UUID
    project_id: UUID
    status: StoryStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class StoryUpdate(SQLModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[StoryStatus] = None
    story_type: Optional[StoryType] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)
    assigned_to: Optional[UUID] = None
    sprint_id: Optional[UUID] = None
    epic_id: Optional[UUID] = None
    parent_story_id: Optional[UUID] = None
    tags: Optional[list[str]] = None
    acceptance_criteria: Optional[str] = None
    business_value: Optional[int] = Field(None, ge=1, le=100)
    risk_level: Optional[Literal["low", "medium", "high", "critical"]] = None
    target_release: Optional[str] = None
    dependencies: Optional[list[UUID]] = None
    blocked_by: Optional[UUID] = None
    blocking: Optional[list[UUID]] = None
    attachments: Optional[list[str]] = None
    labels: Optional[list[str]] = None


class StoriesPublic(SQLModel):
    data: list[dict]
    count: int
