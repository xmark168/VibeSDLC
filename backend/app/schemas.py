from datetime import date, datetime, timezone
from token import OP
from uuid import UUID, uuid4
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from .models import Role, StoryStatus, StoryType
from typing import Optional
from enum import Enum
from app.models import AuthorType

# user
class UserPublic(SQLModel):
    id: UUID
    full_name: Optional[str] = None
    email: EmailStr
    role: Role


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class UserCreate(SQLModel):
    username: str | None = None
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
    message_type: Optional[str] = "text"  # "text" | "product_brief" | "product_vision" | "product_backlog"
    structured_data: Optional[dict] = None

class ChatMessageUpdate(SQLModel):
    content: Optional[str] = None

class ChatMessagePublic(SQLModel):
    id: UUID
    project_id: UUID
    author_type: AuthorType
    user_id: Optional[UUID] = None
    agent_id: Optional[UUID] = None
    content: str
    message_type: Optional[str] = "text"  # NEW: "text" | "product_brief" | "product_vision" | "product_backlog"
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


# ============= Story Schemas =============

class StoryBase(SQLModel):
    """Base schema for Story with only UserStory and EnablerStory types"""
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    type: StoryType = Field(default=StoryType.USER_STORY)
    status: StoryStatus = Field(default=StoryStatus.TODO)
    epic_id: Optional[UUID] = None
    acceptance_criteria: Optional[str] = None
    rank: Optional[int] = None
    estimate_value: Optional[int] = None
    story_point: Optional[int] = None
    priority: Optional[int] = None
    pause: bool = False
    deadline: Optional[datetime] = None
    assignee_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    token_used: Optional[int] = None


class StoryCreate(StoryBase):
    """Schema for creating a new story (BA agent)"""
    project_id: UUID


class StoryUpdate(SQLModel):
    """Schema for updating story fields (BA/TL/Dev/Tester)"""
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[StoryType] = None
    status: Optional[StoryStatus] = None
    epic_id: Optional[UUID] = None
    acceptance_criteria: Optional[str] = None
    rank: Optional[int] = None
    estimate_value: Optional[int] = None
    story_point: Optional[int] = None
    priority: Optional[int] = None
    pause: Optional[bool] = None
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assignee_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    token_used: Optional[int] = None


class StorySimple(StoryBase):
    """Simple story schema without nested relationships"""
    id: UUID
    project_id: UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class StoryPublic(StoryBase):
    """Full story schema with relationships for Kanban display"""
    id: UUID
    project_id: UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    parent: Optional[StorySimple] = None
    children: list[StorySimple] = []


class StoriesPublic(SQLModel):
    """List of stories response"""
    data: list[StoryPublic]
    count: int


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
