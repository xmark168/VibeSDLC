"""Agent and AgentPersonaTemplate models."""

from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, UniqueConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, Column

from app.models.base import BaseModel, AgentStatus

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.message import Message
    from app.models.agent_pool import AgentPool


class AgentPersonaTemplate(BaseModel, table=True):
    __tablename__ = "agent_persona_templates"
    
    name: str = Field(nullable=False, index=True)
    role_type: str = Field(nullable=False, index=True)
    avatar: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    
    personality_traits: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    communication_style: str = Field(nullable=False)
    
    persona_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    is_active: bool = Field(default=True)
    display_order: int = Field(default=0)
    
    agents: list["Agent"] = Relationship(back_populates="persona_template")
    
    __table_args__ = (
        UniqueConstraint('name', 'role_type', name='uq_persona_name_role'),
    )


class Agent(BaseModel, table=True):
    __tablename__ = "agents"

    project_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE", use_alter=True, name="fk_agents_project_id"),
            index=True,
            nullable=False
        )
    )

    persona_template_id: UUID | None = Field(
        default=None,
        foreign_key="agent_persona_templates.id",
        ondelete="RESTRICT"
    )
    
    pool_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("agent_pools.id", ondelete="SET NULL", use_alter=True, name="fk_agents_pool_id"),
            index=True,
            nullable=True
        )
    )

    name: str
    human_name: str = Field(nullable=False)
    role_type: str = Field(nullable=False)
    agent_type: str | None = Field(default=None)

    personality_traits: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    communication_style: str | None = Field(default=None)
    persona_metadata: dict | None = Field(default=None, sa_column=Column(JSON))

    status: AgentStatus = Field(default=AgentStatus.idle)
    
    # Token usage tracking per agent
    tokens_used_total: int = Field(default=0)
    tokens_used_today: int = Field(default=0)
    llm_calls_total: int = Field(default=0)

    persona_template: Optional["AgentPersonaTemplate"] = Relationship(back_populates="agents")
    pool: Optional["AgentPool"] = Relationship(back_populates="agents")
    project: "Project" = Relationship(
        back_populates="agents",
        sa_relationship_kwargs={
            "foreign_keys": "[Agent.project_id]"
        }
    )
    messages: list["Message"] = Relationship(back_populates="agent")
