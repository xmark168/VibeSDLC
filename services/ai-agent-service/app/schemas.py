from datetime import date, datetime, timezone
from token import OP
from uuid import UUID, uuid4
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from .models import Role, GitHubAccountType
from typing import Optional
from enum import Enum
from app.models import AuthorType

# user
class UserPublic(SQLModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: Role


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
    sprint_id: UUID


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
    sprint_id: Optional[UUID] = None


class BacklogItemPublic(BacklogItemBase):
    id: UUID
    sprint_id: UUID
    created_at: datetime
    updated_at: datetime


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
    sprint_from: Optional[str] = None
    sprint_to: Optional[str] = None
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
class ProjectBase(SQLModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    is_init: bool = False

class ProjectCreate(ProjectBase):
    owner_id: UUID

class ProjectUpdate(SQLModel):
    code: Optional[str] = None
    name: Optional[str] = None
    is_init: Optional[bool] = None

class ProjectPublic(ProjectBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

class ProjectsPublic(SQLModel):
    data: list[ProjectPublic]
    count: int

#sprint
class SprintBase(SQLModel):
    name: str = Field(min_length=1, max_length=255)
    number: int = Field(ge=1, description="Sprint number (1, 2, 3...)")
    goal: str = Field(min_length=1, max_length=1000)
    status: str = Field(description="Status: Planning, Active, Completed, Cancelled")
    start_date: datetime
    end_date: datetime
    velocity_plan: str = Field(default="0", description="Planned velocity")
    velocity_actual: str = Field(default="0", description="Actual velocity")

class SprintCreate(SprintBase):
    project_id: UUID

class SprintUpdate(SQLModel):
    name: Optional[str] = None
    number: Optional[int] = Field(None, ge=1)
    goal: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    velocity_plan: Optional[str] = None
    velocity_actual: Optional[str] = None

class SprintPublic(SprintBase):
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime

class SprintsPublic(SQLModel):
    data: list[SprintPublic]
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
    installation_id: int
    account_login: str
    account_type: GitHubAccountType
    repositories: Optional[dict] = None


class GitHubInstallationCreate(GitHubInstallationBase):
    user_id: UUID


class GitHubInstallationUpdate(SQLModel):
    repositories: Optional[dict] = None


class GitHubInstallationPublic(GitHubInstallationBase):
    id: UUID
    user_id: UUID
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
