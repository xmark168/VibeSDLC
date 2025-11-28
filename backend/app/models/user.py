"""User and authentication related models."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from pydantic import EmailStr
from sqlmodel import Field, Relationship

from app.models.base import BaseModel, Role

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.story import Comment
    from app.models.billing import Subscription


class User(BaseModel, table=True):
    __tablename__ = "users"

    username: str | None = Field(default=None, max_length=50, nullable=True)
    full_name: str | None = Field(default=None, max_length=50, nullable=True)
    hashed_password: str = Field(nullable=True, sa_column_kwargs={"name": "password_hash"})
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    
    address: str | None = Field(default=None, nullable=True)
    balance: float = Field(default=0.0, nullable=True)
    is_active: bool = Field(default=True, nullable=True)
    failed_login_attempts: int = Field(default=0, nullable=False)
    locked_until: datetime | None = Field(default=None)
    two_factor_enabled: bool = Field(default=False, nullable=True)
    
    role: Role = Field(default=Role.USER, nullable=False)
    is_locked: bool = Field(default=False, nullable=False)
    login_provider: bool = Field(default=False, nullable=False)

    owned_projects: list["Project"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    comments: list["Comment"] = Relationship(
        back_populates="commenter",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    user_subscriptions: list["Subscription"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class RefreshToken(BaseModel, table=True):
    __tablename__ = "refresh_tokens"

    token: str = Field(unique=True, index=True, max_length=255)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    expires_at: datetime = Field(nullable=False)
    is_revoked: bool = Field(default=False, nullable=False)

    family_id: UUID = Field(nullable=False, index=True)
    parent_token_id: UUID | None = Field(default=None, foreign_key="refresh_tokens.id", ondelete="SET NULL")

    user: User = Relationship()
    parent: Optional["RefreshToken"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "RefreshToken.id"},
    )
    children: list["RefreshToken"] = Relationship(back_populates="parent")
