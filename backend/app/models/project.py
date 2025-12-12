"""Project and related models."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Text
from sqlmodel import Field, Relationship, Column

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.agent import Agent
    from app.models.story import Story, Epic


class Project(BaseModel, table=True):
    __tablename__ = "projects"

    code: str
    name: str
    owner_id: UUID = Field(foreign_key="users.id", nullable=False, ondelete="CASCADE")
    is_init: bool = Field(default=False)

    is_private: bool = Field(default=True)
    tech_stack: str = Field(default="nodejs-react")
    wip_data: dict | None = Field(default=None, sa_column=Column(JSON))

    project_path: str | None = Field(default=None, max_length=500)
    
    active_agent_id: UUID | None = Field(
        default=None,
        foreign_key="agents.id",
        ondelete="SET NULL"
    )
    active_agent_updated_at: datetime | None = Field(default=None)
    
    websocket_connected: bool = Field(default=False)
    websocket_last_seen: datetime | None = Field(default=None)
    
    # Token budget fields for cost control
    token_budget_daily: int = Field(default=100000)
    token_budget_monthly: int = Field(default=2000000)
    tokens_used_today: int = Field(default=0)
    tokens_used_this_month: int = Field(default=0)
    budget_last_reset_daily: datetime | None = Field(default=None)
    budget_last_reset_monthly: datetime | None = Field(default=None)
    
    # Dev server state (for main workspace)
    dev_server_port: int | None = Field(default=None)
    dev_server_pid: int | None = Field(default=None)
    
    owner: "User" = Relationship(back_populates="owned_projects")
    stories: list["Story"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    epics: list["Epic"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    agents: list["Agent"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "foreign_keys": "[Agent.project_id]"
        },
    )

    rules: Optional["ProjectRules"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )
    
    preference: Optional["ProjectPreference"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )


class ProjectRules(BaseModel, table=True):
    __tablename__ = "projectrules"

    project_id: UUID = Field(foreign_key="projects.id", unique=True, nullable=False, ondelete="CASCADE")

    po_prompt: str | None = Field(default=None, sa_column=Column(Text))
    dev_prompt: str | None = Field(default=None, sa_column=Column(Text))
    tester_prompt: str | None = Field(default=None, sa_column=Column(Text))

    project: Project = Relationship(back_populates="rules")


class ProjectPreference(BaseModel, table=True):
    """User preferences per project for AI agent personalization.
    
    Flexible JSONB-based preferences storage.
    
    Example preferences:
    {
        "preferred_language": "vi",
        "communication_style": "casual",
        "response_length": "concise", 
        "emoji_usage": true,
        "expertise_level": "intermediate",
        "timezone": "Asia/Ho_Chi_Minh",
        "custom_instructions": "Always explain technical terms",
        "domain_context": "E-commerce platform",
        "tech_stack": ["React", "FastAPI", "PostgreSQL"]
    }
    """
    __tablename__ = "project_preferences"

    project_id: UUID = Field(foreign_key="projects.id", unique=True, nullable=False, ondelete="CASCADE")
    
    # All preferences stored as flexible JSONB
    preferences: dict = Field(default_factory=dict, sa_column=Column(JSON))

    project: Project = Relationship(back_populates="preference")
