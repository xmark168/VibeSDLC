"""Story-related schemas."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.models import StoryStatus, StoryType, StoryAgentState


class StoryBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    story_type: StoryType = Field(default=StoryType.USER_STORY)
    priority: int = Field(default=2, ge=1, le=3)
    story_point: Optional[int] = Field(None, ge=1, le=21)  # Fibonacci scale
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)
    assigned_to: Optional[UUID] = None
    sprint_id: Optional[UUID] = None
    epic_id: Optional[UUID] = None
    parent_story_id: Optional[UUID] = None
    tags: Optional[list[str]] = Field(default_factory=list)
    acceptance_criteria: Optional[list[str]] = Field(default_factory=list)
    requirements: Optional[list[str]] = Field(default_factory=list)
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
    # Override to allow None (model allows None, but StoryBase requires int)
    priority: Optional[int] = Field(None, ge=1, le=3)
    # Additional fields from Story model
    rank: Optional[int] = None
    agent_state: Optional[StoryAgentState] = None
    assigned_agent_id: Optional[UUID] = None
    branch_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class StoryUpdate(SQLModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[StoryStatus] = None
    story_type: Optional[StoryType] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    story_point: Optional[int] = Field(None, ge=1, le=21)
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)
    assigned_to: Optional[UUID] = None
    sprint_id: Optional[UUID] = None
    epic_id: Optional[UUID] = None
    parent_story_id: Optional[UUID] = None
    tags: Optional[list[str]] = None
    acceptance_criteria: Optional[list[str]] = None
    requirements: Optional[list[str]] = None
    business_value: Optional[int] = Field(None, ge=1, le=100)
    risk_level: Optional[Literal["low", "medium", "high", "critical"]] = None
    target_release: Optional[str] = None
    dependencies: Optional[list[UUID]] = None
    blocked_by: Optional[UUID] = None
    blocking: Optional[list[UUID]] = None
    attachments: Optional[list[str]] = None
    labels: Optional[list[str]] = None
    # Agent tracking
    agent_state: Optional[StoryAgentState] = None
    assigned_agent_id: Optional[UUID] = None
    branch_name: Optional[str] = None


class StoriesPublic(SQLModel):
    data: list[dict]
    count: int
