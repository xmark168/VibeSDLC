from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from .models import Role
from typing import Optional

class UserPublic(SQLModel):
    id: UUID
    username: str
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

class SprintPublic(SQLModel):
    id: UUID
    project_id: UUID
    name: str
    number: int
    goal: str
    status: str
    start_date: datetime
    end_date: datetime
    velocity_plan: str
    velocity_actual: str
    created_at: datetime
    updated_at: datetime

class SprintsPublic(SQLModel):
    data: list[SprintPublic]
    count: int

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