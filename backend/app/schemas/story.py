"""Story-related schemas."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import computed_field
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
    dependencies: Optional[list[str]] = Field(default_factory=list)  # Story IDs (strings like 'US-001')
    blocked_by: Optional[UUID] = None
    blocking: Optional[list[str]] = Field(default_factory=list)  # Story IDs
    attachments: Optional[list[str]] = Field(default_factory=list)
    labels: Optional[list[str]] = Field(default_factory=list)


class StoryCreate(StoryBase):
    project_id: UUID
    story_code: Optional[str] = Field(None, max_length=50)  # e.g., "EPIC-001-US-001"
    # New epic fields (when creating new epic)
    new_epic_title: Optional[str] = Field(None, max_length=255)
    new_epic_domain: Optional[str] = Field(None, max_length=100)
    new_epic_description: Optional[str] = Field(None)


class StoryPublic(StoryBase):
    id: UUID
    project_id: UUID
    status: StoryStatus
    # Override to allow None (model allows None, but StoryBase requires int)
    priority: Optional[int] = Field(None, ge=1, le=3)
    # Story code for display (e.g., "EPIC-001-US-001")
    story_code: Optional[str] = None
    # Story type (maps from model's 'type' field)
    type: Optional[StoryType] = None
    # Additional fields from Story model
    rank: Optional[int] = None
    agent_state: Optional[StoryAgentState] = None
    assigned_agent_id: Optional[UUID] = None
    branch_name: Optional[str] = None
    worktree_path: Optional[str] = None
    running_port: Optional[int] = None
    running_pid: Optional[int] = None
    pr_url: Optional[str] = None
    merge_status: Optional[str] = None
    started_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    @computed_field
    @property
    def worktree_path_display(self) -> Optional[str]:
        """Return relative worktree path for display (last 2 segments)."""
        if not self.worktree_path:
            return None
        parts = self.worktree_path.replace('\\', '/').split('/')
        return '/'.join(parts[-2:]) if len(parts) >= 2 else self.worktree_path
    # Epic info for display
    epic_code: Optional[str] = None
    epic_title: Optional[str] = None
    epic_description: Optional[str] = None
    epic_domain: Optional[str] = None


class StoryUpdate(SQLModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[StoryStatus] = None
    story_type: Optional[StoryType] = None
    story_code: Optional[str] = Field(None, max_length=50)  # e.g., "EPIC-001-US-001"
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
    dependencies: Optional[list[str]] = None  # Story IDs (strings)
    blocked_by: Optional[UUID] = None
    blocking: Optional[list[str]] = None  # Story IDs
    attachments: Optional[list[str]] = None
    labels: Optional[list[str]] = None
    # Kanban ordering
    rank: Optional[int] = None
    # Agent tracking
    agent_state: Optional[StoryAgentState] = None
    assigned_agent_id: Optional[UUID] = None
    branch_name: Optional[str] = None


class StoriesPublic(SQLModel):
    data: list[dict]
    count: int


class BulkRankUpdate(SQLModel):
    story_id: UUID
    rank: int


class BulkRankUpdateRequest(SQLModel):
    updates: list[BulkRankUpdate]
