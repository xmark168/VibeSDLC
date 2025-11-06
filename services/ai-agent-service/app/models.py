from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum
from pydantic import EmailStr
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy import JSON
from typing import Optional
from sqlalchemy import JSON, Column

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


class GitHubAccountType(str, Enum):
    USER = "User"
    ORGANIZATION = "Organization"


class GitHubInstallationStatus(str, Enum):
    PENDING = "pending"
    INSTALLED = "installed"
    DELETED = "deleted"


class BaseModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
        nullable=False,
    )


# Shared properties
class User(BaseModel, table=True):
    __tablename__ = "users"

    full_name: str = Field(max_length=50, nullable=True)
    hashed_password: str = Field(nullable=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    role: Role = Field(default=Role.USER, nullable=True)

    # Account status fields for security
    is_active: bool = Field(default=True, nullable=True)
    is_locked: bool = Field(default=False, nullable=False)
    locked_until: datetime | None = Field(default=None)
    failed_login_attempts: int = Field(default=0, nullable=False)

    login_provider: bool = Field(default=False, nullable=False)

    owned_projects: list["Project"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    comments: list["Comment"] = Relationship(
        back_populates="commenter",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    github_installations: list["GitHubInstallation"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


# GitHub App Integration
class GitHubInstallation(BaseModel, table=True):
    __tablename__ = "github_installations"

    installation_id: int | None = Field(default=None, unique=True, index=True, nullable=True)
    account_login: str = Field(nullable=False)
    account_type: GitHubAccountType = Field(nullable=False, default=GitHubAccountType.USER)
    account_status: GitHubInstallationStatus = Field(
        nullable=False,
        default=GitHubInstallationStatus.PENDING,
        index=True
    )
    repositories: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    user_id: UUID | None = Field(default=None, foreign_key="users.id", nullable=True, ondelete="CASCADE")

    user: User = Relationship(back_populates="github_installations")


class Project(BaseModel, table=True):
    __tablename__ = "projects"

    code: str
    name: str
    owner_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    is_init: bool = Field(default=False)

    # GitHub integration fields
    github_repository_url: str | None = Field(default=None, unique=True, nullable=True)
    github_repository_name: str | None = Field(default=None, nullable=True)
    is_private: bool = Field(default=True)
    tech_stack: str = Field(default="nodejs-react")
    owner: User = Relationship(back_populates="owned_projects")
    sprints: list["Sprint"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Sprint(BaseModel, table=True):
    __tablename__ = "sprints"

    project_id: UUID = Field(
        foreign_key="projects.id", nullable=False, ondelete="CASCADE"
    )
    name: str
    number: int
    goal: str
    status: str
    start_date: datetime
    end_date: datetime
    velocity_plan: str
    velocity_actual: str

    project: Project = Relationship(back_populates="sprints")
    backlog_items: list["BacklogItem"] = Relationship(
        back_populates="sprint",  # ✅ SỬA từ backlog_items="sprint"
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class BacklogItem(BaseModel, table=True):
    __tablename__ = "backlog_items"

    sprint_id: UUID = Field(
        foreign_key="sprints.id", nullable=False, ondelete="CASCADE"
    )
    parent_id: UUID | None = Field(
        default=None, foreign_key="backlog_items.id", ondelete="SET NULL"
    )
    type: str
    title: str
    description: str | None = Field(default=None)
    status: str
    reviewer_id: UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    assignee_id: UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    rank: int | None = Field(default=None)
    estimate_value: int | None = Field(default=None)
    story_point: int | None = Field(default=None)
    pause: bool = Field(default=False)
    deadline: datetime | None = Field(default=None)

    sprint: Sprint = Relationship(back_populates="backlog_items")
    parent: Optional["BacklogItem"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "BacklogItem.id"},
    )
    children: list["BacklogItem"] = Relationship(back_populates="parent")
    comments: list["Comment"] = Relationship(
        back_populates="backlog_item",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    activities: list["IssueActivity"] = Relationship(
        back_populates="issue", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Comment(BaseModel, table=True):
    __tablename__ = "comments"

    backlog_item_id: UUID = Field(
        foreign_key="backlog_items.id", nullable=False, ondelete="CASCADE"
    )
    commenter_id: UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )
    content: str

    backlog_item: BacklogItem = Relationship(back_populates="comments")
    commenter: User = Relationship(back_populates="comments")


class IssueActivity(BaseModel, table=True):
    __tablename__ = "issue_activities"

    issue_id: UUID = Field(
        foreign_key="backlog_items.id", nullable=False, ondelete="CASCADE"
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
    sprint_from: str | None = Field(default=None)
    sprint_to: str | None = Field(default=None)
    type_from: str | None = Field(default=None)
    type_to: str | None = Field(default=None)
    note: str | None = Field(default=None)

    issue: BacklogItem = Relationship(back_populates="activities") 

class AuthorType(str, Enum):
    USER = "user"
    AGENT = "agent"


class Agent(BaseModel, table=True):
    __tablename__ = "agents"

    name: str
    agent_type: str | None = Field(default=None)

    # Relationship to messages authored by this agent
    messages: list["Message"] = Relationship(back_populates="agent")


class Message(BaseModel, table=True):
    __tablename__ = "messages"

    # Single-session-per-project: attach all messages to a project
    project_id: UUID = Field(foreign_key="projects.id", nullable=False, ondelete="CASCADE", index=True)

    # Author info: either user or agent (or system/tool)
    author_type: AuthorType = Field(default=AuthorType.USER, nullable=False)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", ondelete="SET NULL")

    # Message payload
    content: str

    # Structured data fields for agent previews
    message_type: str = Field(default="text", nullable=True)  # "text" | "product_brief" | "product_vision" | "product_backlog" | "sprint_plan"
    structured_data: dict | None = Field(default=None, sa_column=Column(JSON))  # JSON data (brief/vision/backlog/sprint)
    message_metadata: dict | None = Field(default=None, sa_column=Column(JSON))  # Message metadata (preview_id, quality_score, approved_by, etc.)

    # Relationship back to agent
    agent: Agent | None = Relationship(back_populates="messages")


class RefreshToken(BaseModel, table=True):
    __tablename__ = "refresh_tokens"

    token: str = Field(unique=True, index=True, max_length=255)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    expires_at: datetime = Field(nullable=False)
    is_revoked: bool = Field(default=False, nullable=False)

    # Token family tracking for rotation detection
    family_id: UUID = Field(nullable=False, index=True)
    parent_token_id: UUID | None = Field(default=None, foreign_key="refresh_tokens.id", ondelete="SET NULL")

    # Relationships
    user: User = Relationship()
    parent: Optional["RefreshToken"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "RefreshToken.id"},
    )
    children: list["RefreshToken"] = Relationship(back_populates="parent")
    
