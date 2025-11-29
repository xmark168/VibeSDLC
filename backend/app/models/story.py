"""Story, Epic, Comment and related models."""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, Column

from app.models.base import (
    BaseModel, StoryStatus, StoryType, StoryPriority, StoryAgentState, EpicStatus
)

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.agent import Agent


class Epic(BaseModel, table=True):
    __tablename__ = "epics"

    title: str
    description: str | None = Field(default=None, sa_column=Column(Text))
    project_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE", use_alter=True, name="fk_epics_project_id"),
            nullable=False
        )
    )

    domain: str | None = Field(default=None)
    epic_status: EpicStatus = Field(default=EpicStatus.PLANNED)

    project: "Project" = Relationship(back_populates="epics")
    stories: list["Story"] = Relationship(back_populates="epic")


class Story(BaseModel, table=True):
    __tablename__ = "stories"

    project_id: UUID = Field(
        foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True
    )
    parent_id: UUID | None = Field(
        default=None, foreign_key="stories.id", ondelete="SET NULL"
    )

    type: StoryType = Field(default=StoryType.USER_STORY)
    title: str
    description: str | None = Field(default=None, sa_column=Column(Text))
    status: StoryStatus = Field(default=StoryStatus.TODO)

    epic_id: UUID | None = Field(default=None, foreign_key="epics.id", ondelete="SET NULL")

    acceptance_criteria: str | None = Field(default=None, sa_column=Column(Text))

    assignee_id: UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    reviewer_id: UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )

    rank: int | None = Field(default=None)
    estimate_value: int | None = Field(default=None)
    story_point: int | None = Field(default=None)
    priority: int | None = Field(default=None)

    story_priority: StoryPriority | None = Field(default=None)
    dependencies: list = Field(default_factory=list, sa_column=Column(JSON))

    pause: bool = Field(default=False)
    deadline: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    started_at: datetime | None = Field(default=None)
    review_started_at: datetime | None = Field(default=None)

    token_used: int | None = Field(default=None)
    
    # Agent tracking - resets when story changes column
    agent_state: StoryAgentState | None = Field(default=None)
    assigned_agent_id: UUID | None = Field(
        default=None, foreign_key="agents.id", ondelete="SET NULL"
    )
    
    # Git worktree - each story has its own branch
    branch_name: str | None = Field(default=None, max_length=255)

    project: "Project" = Relationship(back_populates="stories")
    epic: Optional["Epic"] = Relationship(back_populates="stories")
    assigned_agent: Optional["Agent"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Story.assigned_agent_id]"}
    )
    parent: Optional["Story"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Story.id"},
    )
    children: list["Story"] = Relationship(back_populates="parent")
    comments: list["Comment"] = Relationship(
        back_populates="story",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    activities: list["IssueActivity"] = Relationship(
        back_populates="story", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    @property
    def cycle_time_hours(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() / 3600
        return None

    @property
    def lead_time_hours(self) -> float | None:
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds() / 3600
        return None

    @property
    def age_in_current_status_hours(self) -> float:
        status_start_time = self.created_at

        if self.status == StoryStatus.IN_PROGRESS and self.started_at:
            status_start_time = self.started_at
        elif self.status == StoryStatus.REVIEW and self.review_started_at:
            status_start_time = self.review_started_at
        elif self.status == StoryStatus.DONE and self.completed_at:
            status_start_time = self.completed_at

        current_time = datetime.now(timezone.utc)

        if status_start_time.tzinfo is None:
            status_start_time = status_start_time.replace(tzinfo=timezone.utc)

        return (current_time - status_start_time).total_seconds() / 3600


class Comment(BaseModel, table=True):
    __tablename__ = "comments"

    backlog_item_id: UUID = Field(
        foreign_key="stories.id", nullable=False, ondelete="CASCADE"
    )
    commenter_id: UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )
    content: str

    story: Story = Relationship(back_populates="comments")
    commenter: "User" = Relationship(back_populates="comments")


class IssueActivity(BaseModel, table=True):
    __tablename__ = "issue_activities"

    issue_id: UUID = Field(
        foreign_key="stories.id", nullable=False, ondelete="CASCADE"
    )
    actor_id: str | None = Field(default=None)
    actor_name: str | None = Field(default=None)

    title_from: str | None = Field(default=None)
    title_to: str | None = Field(default=None)
    status_from: str | None = Field(default=None)
    status_to: str | None = Field(default=None)
    assignee_from: str | None = Field(default=None)
    assignee_to: str | None = Field(default=None)
    reviewer_from: str | None = Field(default=None)
    reviewer_to: str | None = Field(default=None)
    rank_from: int | None = Field(default=None)
    rank_to: int | None = Field(default=None)
    estimate_from: int | None = Field(default=None)
    estimate_to: int | None = Field(default=None)
    deadline_from: datetime | None = Field(default=None)
    deadline_to: datetime | None = Field(default=None)
    type_from: str | None = Field(default=None)
    type_to: str | None = Field(default=None)
    note: str | None = Field(default=None)

    story: Story = Relationship(back_populates="activities")
