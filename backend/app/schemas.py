from datetime import date, datetime, timezone
from token import OP
from uuid import UUID, uuid4
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from .models import Role, GitHubAccountType, GitHubInstallationStatus
from typing import Optional
from enum import Enum
from app.models import AuthorType

# user
class UserPublic(SQLModel):
    id: UUID
    full_name: Optional[str] = None
    email: EmailStr
    role: Role
    github_installation_id: Optional[int] = None  # GitHub installation_id from linked installation (deprecated, use github_installations)
    github_installations: Optional[list["GitHubInstallationPublic"]] = None  # Full GitHub installation data


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class UserCreate(SQLModel):
    username: str
    password: str
    email: EmailStr


class UserLogin(SQLModel):
    email_or_username: str
    password: str

class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserUpdateMe(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)

class UserRegister(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=3)

class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(SQLModel):
    user_id: Optional[str] = None

class TokenPayload(SQLModel):
    sub: Optional[str] = None  # subject - user ID in JWT standard
    type: Optional[str] = None  # token type (access/refresh)

class RefreshTokenRequest(SQLModel):
    refresh_token: str

class Message(SQLModel):
    message: str

# chat/messages
class ChatMessageBase(SQLModel):
    content: str
    author_type: AuthorType

class ChatMessageCreate(ChatMessageBase):
    project_id: UUID
    agent_id: Optional[UUID] = None

class ChatMessageUpdate(SQLModel):
    content: Optional[str] = None

class ChatMessagePublic(SQLModel):
    id: UUID
    project_id: UUID
    author_type: AuthorType
    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    content: str
    message_type: Optional[str] = "text"  # NEW: "text" | "product_brief" | "product_vision" | "product_backlog" | "sprint_plan"
    structured_data: Optional[dict] = None  # NEW: JSON data for previews
    message_metadata: Optional[dict] = None  # NEW: Message metadata (preview_id, quality_score, etc.)
    created_at: datetime
    updated_at: datetime

class ChatMessagesPublic(SQLModel):
    data: list[ChatMessagePublic]
    count: int
    
class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8)

# Authentication schemas
class LoginRequest(SQLModel):
    email: EmailStr
    password: Optional[str] = None
    fullname: Optional[str] = None
    login_provider: bool = Field(description="false = credential login, true = OAuth provider login")

class LoginResponse(SQLModel):
    user_id: UUID
    access_token: str
    refresh_token: str

class RegisterRequest(SQLModel):
    email: EmailStr = Field(description="Email address")
    fullname: str = Field(min_length=1, max_length=50, description="Full name")
    password: str = Field(min_length=8, description="Password (min 8 chars, must contain letter and number)")
    confirm_password: str = Field(description="Password confirmation")

class RegisterResponse(SQLModel):
    message: str
    email: EmailStr
    expires_in: int

class ConfirmCodeRequest(SQLModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, description="6-digit verification code")

class ConfirmCodeResponse(SQLModel):
    message: str
    user_id: UUID

class ResendCodeRequest(SQLModel):
    email: EmailStr

class ResendCodeResponse(SQLModel):
    message: str
    email: EmailStr
    expires_in: int

class RefreshTokenResponse(SQLModel):
    user_id: UUID
    access_token: str
    refresh_token: str

class LogoutResponse(SQLModel):
    message: str

class ForgotPasswordRequest(SQLModel):
    email: EmailStr

class ForgotPasswordResponse(SQLModel):
    message: str
    expires_in: int

class ResetPasswordRequest(SQLModel):
    token: str
    new_password: str = Field(min_length=8)
    confirm_password: str

class ResetPasswordResponse(SQLModel):
    message: str

# backlog

class BacklogItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    type: str = Field(description="Type: Epic, Story, Task, Sub-task")
    status: str = Field(description="Status: Backlog, Todo, Doing, Done")
    rank: Optional[int] = None
    estimate_value: Optional[int] = None
    story_point: Optional[int] = None
    pause: bool = False
    deadline: Optional[datetime] = None
    assignee_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None


class BacklogItemCreate(BacklogItemBase):
    project_id: UUID


class BacklogItemUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    rank: Optional[int] = None
    estimate_value: Optional[int] = None
    story_point: Optional[int] = None
    pause: Optional[bool] = None
    deadline: Optional[datetime] = None
    assignee_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


# TraDS ============= Kanban Hierarchy Support
class BacklogItemSimple(BacklogItemBase):
    """Simple schema without nested relationships to prevent recursion"""
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class BacklogItemPublic(BacklogItemBase):
    """Public schema with parent/children for Kanban hierarchy display"""
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime
    parent: Optional[BacklogItemSimple] = None
    children: list[BacklogItemSimple] = []


class BacklogItemsPublic(SQLModel):
    data: list[BacklogItemPublic]
    count: int

class BacklogItemType(str, Enum):
    EPIC = "Epic"
    USER_STORY = "User story"
    TASK = "Task"
    SUB_TASK = "Sub-task"

class BacklogItemsStatus(str, Enum):
    BACKLOG = "Backlog"
    TODO = "Todo"
    DOING = "Doing"
    DONE = "Done"

class IssueActivityBase(SQLModel):
    action: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    title_from: Optional[str] = None
    title_to: Optional[str] = None
    status_from: Optional[str] = None
    status_to: Optional[str] = None
    assignee_from: Optional[str] = None
    assignee_to: Optional[str] = None
    reviewer_from: Optional[str] = None
    reviewer_to: Optional[str] = None
    rank_from: Optional[int] = None
    rank_to: Optional[int] = None
    estimate_from: Optional[int] = None
    estimate_to: Optional[int] = None
    deadline_from: Optional[datetime] = None
    deadline_to: Optional[datetime] = None
    type_from: Optional[str] = None
    type_to: Optional[str] = None
    note: Optional[str] = None


class IssueActivityCreate(IssueActivityBase):
    issue_id: UUID


class IssueActivityPublic(IssueActivityBase):
    id: UUID
    issue_id: UUID
    created_at: datetime


class IssueActivitiesPublic(SQLModel):
    data: list[IssueActivityPublic]
    count: int

# comment
class CommentBase(SQLModel):
    content: str = Field(min_length=1)


class CommentCreate(CommentBase):
    backlog_item_id: UUID
    commenter_id: UUID


class CommentUpdate(SQLModel):
    content: str = Field(min_length=1)


class CommentPublic(CommentBase):
    id: UUID
    backlog_item_id: UUID
    commenter_id: UUID
    created_at: datetime


class CommentsPublic(SQLModel):
    data: list[CommentPublic]
    count: int

# project
class ProjectCreate(SQLModel):
    """Schema for creating a new project. Code is auto-generated."""
    name: str = Field(min_length=1, max_length=255)
    is_private: bool = Field(default=True)
    tech_stack: str = Field(default="nodejs-react")
    repository_url: Optional[str] = Field(default=None, max_length=500)


class ProjectUpdate(SQLModel):
    """Schema for updating a project. All fields are optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_init: Optional[bool] = None
    is_private: Optional[bool] = None
    tech_stack: Optional[str] = None
    repository_url: Optional[str] = Field(None, max_length=500)


class ProjectPublic(SQLModel):
    """Schema for project response with all fields from model."""
    id: UUID
    code: str
    name: str
    owner_id: UUID
    is_init: bool
    is_private: bool
    tech_stack: str
    github_repository_url: Optional[str] = None
    github_repository_id: Optional[int] = None
    github_repository_name: Optional[str] = None
    github_installation_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ProjectsPublic(SQLModel):
    """Schema for list of projects response."""
    data: list[ProjectPublic]
    count: int

# agent
class AgentBase(SQLModel):
    name: str
    agent_type: Optional[str] = None

class AgentCreate(AgentBase):
    pass

class AgentUpdate(SQLModel):
    name: Optional[str] = None
    agent_type: Optional[str] = None

class AgentPublic(AgentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class AgentsPublic(SQLModel):
    data: list[AgentPublic]
    count: int


# GitHub Integration schemas
class GitHubInstallationBase(SQLModel):
    installation_id: int | None
    account_login: str
    account_type: GitHubAccountType
    account_status: GitHubInstallationStatus
    repositories: Optional[dict] = None


class GitHubInstallationCreate(GitHubInstallationBase):
    user_id: UUID | None = None


class GitHubInstallationUpdate(SQLModel):
    repositories: Optional[dict] = None
    account_status: Optional[GitHubInstallationStatus] = None
    installation_id: Optional[int] = None


class GitHubInstallationPublic(GitHubInstallationBase):
    id: UUID
    user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class GitHubInstallationsPublic(SQLModel):
    data: list[GitHubInstallationPublic]
    count: int


# GitHub Repository schemas
class GitHubRepository(SQLModel):
    id: int
    name: str
    full_name: str
    url: str
    description: Optional[str] = None
    private: bool
    owner: str


class GitHubRepositoriesPublic(SQLModel):
    data: list[GitHubRepository]
    count: int


# Project GitHub linking schemas
class ProjectGitHubLink(SQLModel):
    github_repository_id: int
    github_repository_name: str
    github_installation_id: UUID


class ProjectGitHubUnlink(SQLModel):
    pass


# Create repository from template schemas
class CreateRepoFromTemplateRequest(SQLModel):
    """Request schema for creating a repository from a template."""
    template_owner: str = Field(description="Owner of the template repository (e.g., 'organization' or 'username')")
    template_repo: str = Field(description="Name of the template repository")
    new_repo_name: str = Field(min_length=1, max_length=255, description="Name for the new repository")
    new_repo_description: Optional[str] = Field(None, max_length=1000, description="Description for the new repository")
    is_private: bool = Field(default=False, description="Whether the new repository should be private")
    github_installation_id: int = Field(description="GitHub installation ID to use for creating the repository")


class CreateRepoFromTemplateResponse(SQLModel):
    """Response schema for repository creation."""
    success: bool = Field(description="Whether the repository was created successfully")
    repository_id: Optional[int] = Field(None, description="GitHub repository ID")
    repository_name: Optional[str] = Field(None, description="Name of the created repository")
    repository_full_name: Optional[str] = Field(None, description="Full name of the created repository (owner/name)")
    repository_url: Optional[str] = Field(None, description="URL of the created repository")
    repository_description: Optional[str] = Field(None, description="Description of the created repository")
    repository_private: Optional[bool] = Field(None, description="Whether the repository is private")
    message: Optional[str] = Field(None, description="Success or error message")


# TraDS ============= Sprint Retrospective Schemas
class BlockerCreate(SQLModel):
    backlog_item_id: UUID
    blocker_type: str  # "DEV_BLOCKER" or "TEST_BLOCKER"
    description: str

class BlockerPublic(SQLModel):
    id: UUID
    backlog_item_id: UUID
    reported_by_user_id: UUID
    blocker_type: str
    description: str
    created_at: datetime

class BlockersPublic(SQLModel):
    data: list[BlockerPublic]
    count: int

class ProjectRulesCreate(SQLModel):
    project_id: UUID
    po_prompt: Optional[str] = None
    dev_prompt: Optional[str] = None
    tester_prompt: Optional[str] = None

class ProjectRulesUpdate(SQLModel):
    po_prompt: Optional[str] = None
    dev_prompt: Optional[str] = None
    tester_prompt: Optional[str] = None

class ProjectRulesPublic(SQLModel):
    id: UUID
    project_id: UUID
    po_prompt: Optional[str] = None
    dev_prompt: Optional[str] = None
    tester_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Rebuild models to resolve forward references
UserPublic.model_rebuild()
