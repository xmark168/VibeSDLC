"""Artifact model for storing agent-generated documents."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, Column

from app.models.base import BaseModel, ArtifactType, ArtifactStatus

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.agent import Agent
    from app.models.user import User


class Artifact(BaseModel, table=True):
    __tablename__ = "artifacts"
    
    project_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE", use_alter=True, name="fk_artifacts_project_id"),
            index=True,
            nullable=False
        )
    )
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", ondelete="SET NULL")
    agent_name: str = Field(nullable=False)
    
    artifact_type: ArtifactType = Field(sa_column=Column(SQLEnum(ArtifactType)))
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_column=Column(Text))
    
    content: dict = Field(sa_column=Column(JSON))
    file_path: str | None = Field(default=None)
    
    version: int = Field(default=1)
    parent_artifact_id: UUID | None = Field(default=None, foreign_key="artifacts.id", ondelete="SET NULL")
    
    status: ArtifactStatus = Field(default=ArtifactStatus.DRAFT, sa_column=Column(SQLEnum(ArtifactStatus)))
    
    reviewed_by_user_id: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    reviewed_at: datetime | None = Field(default=None)
    review_feedback: str | None = Field(default=None, sa_column=Column(Text))
    
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    extra_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    
    project: "Project" = Relationship()
    agent: Optional["Agent"] = Relationship()
    reviewed_by: Optional["User"] = Relationship()
    parent: Optional["Artifact"] = Relationship(
        sa_relationship_kwargs={
            "remote_side": "[Artifact.id]",
            "foreign_keys": "[Artifact.parent_artifact_id]"
        }
    )
