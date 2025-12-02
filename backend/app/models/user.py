"""User and authentication related models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import JSON, String, UniqueConstraint
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel, Role

if TYPE_CHECKING:
    from app.models.billing import Subscription
    from app.models.project import Project
    from app.models.story import Comment


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"
    FACEBOOK = "facebook"


class User(BaseModel, table=True):
    __tablename__ = "users"

    username: str | None = Field(default=None, max_length=50, nullable=True)
    full_name: str | None = Field(default=None, max_length=50, nullable=True)
    hashed_password: str = Field(
        nullable=True, sa_column_kwargs={"name": "password_hash"}
    )
    email: EmailStr = Field(unique=True, index=True, max_length=255)

    address: str | None = Field(default=None, nullable=True)
    balance: float = Field(default=0.0, nullable=True)
    is_active: bool = Field(default=True, nullable=True)
    failed_login_attempts: int = Field(default=0, nullable=False)
    locked_until: datetime | None = Field(default=None)
    two_factor_enabled: bool = Field(default=False, nullable=True)
    totp_secret: str | None = Field(default=None, nullable=True)
    backup_codes: list[str] | None = Field(default=None, sa_column=Column(JSON))

    role: Role = Field(default=Role.USER, nullable=False)
    is_locked: bool = Field(default=False, nullable=False)
    login_provider: str | None = Field(default=None, nullable=True)
    avatar_url: str | None = Field(default=None, max_length=500, nullable=True)

    owned_projects: list["Project"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    user_subscriptions: list["Subscription"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    linked_accounts: list["LinkedAccount"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class LinkedAccount(BaseModel, table=True):
    """Linked OAuth accounts for a user"""

    __tablename__ = "linked_accounts"

    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    provider: OAuthProvider = Field(sa_column=Column(String(20), nullable=False))
    provider_user_id: str = Field(nullable=False, max_length=255)
    provider_email: str = Field(nullable=False, max_length=255)

    user: User = Relationship(back_populates="linked_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )


class RefreshToken(BaseModel, table=True):
    __tablename__ = "refresh_tokens"

    token: str = Field(unique=True, index=True, max_length=255)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    expires_at: datetime = Field(nullable=False)
    is_revoked: bool = Field(default=False, nullable=False)

    family_id: UUID = Field(nullable=False, index=True)
    parent_token_id: UUID | None = Field(
        default=None, foreign_key="refresh_tokens.id", ondelete="SET NULL"
    )

    user: User = Relationship()
    parent: Optional["RefreshToken"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "RefreshToken.id"},
    )
    children: list["RefreshToken"] = Relationship(back_populates="parent")
