from datetime import datetime, timezone
from uuid import UUID, uuid4
from enum import Enum
from typing import Optional
from pydantic import EmailStr
from sqlmodel import Field, SQLModel, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"

class RuleType(str, Enum):
    """Rule type enum for project rules."""
    BLOCKER_PREVENTION = "blocker_prevention"
    BEST_PRACTICE = "best_practice"
    CODE_STANDARD = "code_standard"

class RuleCategory(str, Enum):
    """Rule category enum."""
    TECHNICAL = "technical"
    PROCESS = "process"
    QUALITY = "quality"
    COMMUNICATION = "communication"

class RuleSeverity(str, Enum):
    """Rule severity enum."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# class BaseModel(SQLModel):
    # id: User

# Shared properties
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    role: Role = Field(default=Role.USER, nullable=True)
    create_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship
    refresh_tokens: list["RefreshToken"] = Relationship(back_populates="user")

class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=False)
    token: str = Field(unique=True, index=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_revoked: bool = Field(default=False)

    # Relationship
    user: User | None = Relationship(back_populates="refresh_tokens")


class ProjectRule(SQLModel, table=True):
    """Project rules learned from blockers and best practices.

    This table stores actionable rules/instructions that developers and testers
    should follow to prevent blockers and improve code quality.
    """
    __tablename__ = "project_rules"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys (project_id as string for now, can be FK later)
    project_id: str = Field(index=True, max_length=100)

    # Rule metadata
    rule_type: RuleType = Field(default=RuleType.BLOCKER_PREVENTION)
    title: str = Field(max_length=255)
    description: str

    # Tagging for retrieval (stored as JSONB in PostgreSQL)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSONB))
    category: RuleCategory = Field(default=RuleCategory.TECHNICAL)
    severity: RuleSeverity = Field(default=RuleSeverity.MEDIUM)

    # Source tracking
    source_blocker_id: Optional[str] = Field(default=None, max_length=100)
    source_type: str = Field(default="daily_blocker", max_length=50)

    # Ownership
    created_by: str = Field(max_length=50)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Effectiveness tracking
    applied_count: int = Field(default=0)
    success_count: int = Field(default=0)
    effectiveness_score: float = Field(default=0.0)

    # Status
    is_active: bool = Field(default=True, index=True)
    archived_at: Optional[datetime] = Field(default=None)

