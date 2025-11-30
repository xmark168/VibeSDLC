"""User-related schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, BaseModel
from sqlmodel import Field, SQLModel

from app.models import Role


class UserPublic(SQLModel):
    """Public user schema with basic info."""
    id: UUID
    full_name: Optional[str] = None
    email: EmailStr
    role: Role


class UserAdminPublic(SQLModel):
    """Extended user schema for admin views."""
    id: UUID
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: EmailStr
    role: Role
    is_active: bool = True
    is_locked: bool = False
    locked_until: Optional[datetime] = None
    failed_login_attempts: int = 0
    login_provider: Optional[str] = None
    balance: float = 0.0
    created_at: datetime
    updated_at: datetime


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class UsersAdminPublic(SQLModel):
    """Users list for admin with extended info."""
    data: list[UserAdminPublic]
    count: int


class UserCreate(SQLModel):
    username: str | None = None
    password: str
    email: EmailStr


class UserAdminCreate(SQLModel):
    """Admin create user with full control."""
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: EmailStr
    password: str = Field(min_length=6)
    role: Role = Role.USER
    is_active: bool = True


class UserLogin(SQLModel):
    email_or_username: str
    password: str


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserAdminUpdate(SQLModel):
    """Admin update user with full control."""
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6)
    role: Optional[Role] = None
    is_active: Optional[bool] = None


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


# Admin bulk action schemas
class BulkUserIds(BaseModel):
    """Schema for bulk user operations."""
    user_ids: list[UUID]


class UserStatsResponse(BaseModel):
    """User statistics for admin dashboard."""
    total_users: int
    active_users: int
    inactive_users: int
    locked_users: int
    admin_users: int
    regular_users: int
    users_with_oauth: int
