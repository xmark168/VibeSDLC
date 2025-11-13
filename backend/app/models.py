from datetime import datetime
from typing import List, Optional
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, JSON, Enum
from app.database import Base
from sqlalchemy.orm import  Mapped, mapped_column, relationship
from app.enums import StoryStatus, StoryType, StoryPriority, AgentType

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fullname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[dict]] = mapped_column(String(500), nullable=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    # current_plan_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("plans.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    social_accounts: Mapped[List["UserSocialAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    backup_codes: Mapped[List["TwoFactorBackupCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    # SDLC relationships
    projects: Mapped[List["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="selectin"
    )
    stories_created: Mapped[List["Story"]] = relationship(
        back_populates="created_by", cascade="all, delete-orphan", lazy="selectin"
    )
    story_status_changes: Mapped[List["StoryStatusHistory"]] = relationship(
        back_populates="changed_by", cascade="all, delete-orphan", lazy="selectin"
    )

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(500), nullable=False, index=True)  # bcrypt/Argon2 hash
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
    
    __table_args__ = (
        Index("idx_token_lookup", "token_hash", "is_revoked", "expires_at"),
    )

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    user: Mapped["User"] = relationship(back_populates="password_reset_tokens")

class TwoFactorBackupCode(Base):
    __tablename__ = "two_factor_backup_codes"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    user: Mapped["User"] = relationship(back_populates="backup_codes")
    
    __table_args__ = (
        UniqueConstraint("user_id", "code_hash", name="uq_user_backup_code"),
        Index("idx_active_codes", "user_id", "is_revoked"),
    )

class UserSocialAccount(Base):
    __tablename__ = "user_social_accounts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # MUST BE ENCRYPTED!
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    user: Mapped["User"] = relationship(back_populates="social_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_social_provider"),
        Index("idx_social_user", "user_id"),
    )


# ==================== SDLC Models ====================

class TechStack(Base):
    """Technology stack model"""
    __tablename__ = "tech_stacks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Tech specs, versions, configs
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    # Relationships
    projects: Mapped[List["Project"]] = relationship(
        back_populates="tech_stack", lazy="selectin"
    )


class Agent(Base):
    """AI Agent model"""
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="agents")
    story_assignments: Mapped[List["StoryAgentAssignment"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", lazy="selectin"
    )


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    working_directory: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tech_stack_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("tech_stacks.id", ondelete="SET NULL"), nullable=True, index=True)
    kanban_policy: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Kanban board configuration
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="projects")
    tech_stack: Mapped[Optional["TechStack"]] = relationship(back_populates="projects")
    epics: Mapped[List["Epic"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
    agents: Mapped[List["Agent"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )


class Epic(Base):
    """Epic model"""
    __tablename__ = "epics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="epics")
    stories: Mapped[List["Story"]] = relationship(
        back_populates="epic", cascade="all, delete-orphan", lazy="selectin"
    )


class Story(Base):
    """Story/User Story model"""
    __tablename__ = "story"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    epic_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("epics.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[StoryStatus] = mapped_column(Enum(StoryStatus), nullable=False, default=StoryStatus.TODO, index=True)
    type: Mapped[StoryType] = mapped_column(Enum(StoryType), nullable=False, default=StoryType.USER_STORY)
    priority: Mapped[StoryPriority] = mapped_column(Enum(StoryPriority), nullable=False, default=StoryPriority.MEDIUM, index=True)
    acceptance_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Acceptance Criteria
    token_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # AI token usage
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    # Relationships
    epic: Mapped["Epic"] = relationship(back_populates="stories")
    created_by: Mapped["User"] = relationship(back_populates="stories_created")
    agent_assignments: Mapped[List["StoryAgentAssignment"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", lazy="selectin"
    )
    status_history: Mapped[List["StoryStatusHistory"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_story_status_deleted", "status", "deleted_at"),
        Index("idx_story_epic_status", "epic_id", "status"),
    )


class StoryAgentAssignment(Base):
    """Story-Agent assignment model"""
    __tablename__ = "story_agent_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("story.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Specific role for this assignment
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    story: Mapped["Story"] = relationship(back_populates="agent_assignments")
    agent: Mapped["Agent"] = relationship(back_populates="story_assignments")

    __table_args__ = (
        UniqueConstraint("story_id", "agent_id", name="uq_story_agent"),
    )


class StoryStatusHistory(Base):
    """Story status change history model"""
    __tablename__ = "story_status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("story.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status: Mapped[Optional[StoryStatus]] = mapped_column(Enum(StoryStatus), nullable=True)  # Null for initial creation
    new_status: Mapped[StoryStatus] = mapped_column(Enum(StoryStatus), nullable=False)
    changed_by_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    story: Mapped["Story"] = relationship(back_populates="status_history")
    changed_by: Mapped["User"] = relationship(back_populates="story_status_changes")

    __table_args__ = (
        Index("idx_history_story_time", "story_id", "changed_at"),
        Index("idx_history_changed_by", "changed_by_id"),
    )

