"""AgentPool and AgentPoolMetrics models - must be imported before Agent."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON
from sqlmodel import Field, Relationship, Column

from app.models.base import BaseModel, PoolType

if TYPE_CHECKING:
    from app.models.agent import Agent


class AgentPool(BaseModel, table=True):
    __tablename__ = "agent_pools"
    
    pool_name: str = Field(unique=True, nullable=False)
    role_type: str | None = Field(default=None, index=True)
    
    pool_type: PoolType = Field(default=PoolType.FREE, index=True)
    
    max_agents: int = Field(default=100)
    health_check_interval: int = Field(default=60)
    
    llm_model_config: dict | None = Field(default=None, sa_column=Column(JSON))
    allowed_template_ids: list[str] | None = Field(default=None, sa_column=Column(JSON))
    
    is_active: bool = Field(default=True, index=True)
    last_started_at: datetime | None = Field(default=None)
    last_stopped_at: datetime | None = Field(default=None)
    
    total_spawned: int = Field(default=0)
    total_terminated: int = Field(default=0)
    current_agent_count: int = Field(default=0)
    
    created_by: UUID | None = Field(
        default=None,
        foreign_key="users.id",
        ondelete="SET NULL"
    )
    updated_by: UUID | None = Field(
        default=None,
        foreign_key="users.id",
        ondelete="SET NULL"
    )
    auto_created: bool = Field(default=False)
    
    agents: list["Agent"] = Relationship(back_populates="pool")
    metrics: list["AgentPoolMetrics"] = Relationship(
        back_populates="pool",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class AgentPoolMetrics(BaseModel, table=True):
    __tablename__ = "agent_pool_metrics"
    
    pool_id: UUID = Field(
        foreign_key="agent_pools.id",
        nullable=False,
        ondelete="CASCADE",
        index=True
    )
    
    period_start: datetime = Field(nullable=False, index=True)
    period_end: datetime = Field(nullable=False)
    
    total_tokens_used: int = Field(default=0)
    tokens_per_model: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    total_requests: int = Field(default=0)
    requests_per_model: dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    peak_agent_count: int = Field(default=0)
    avg_agent_count: float = Field(default=0.0)
    
    total_executions: int = Field(default=0)
    successful_executions: int = Field(default=0)
    failed_executions: int = Field(default=0)
    
    avg_execution_duration_ms: float | None = Field(default=None)
    
    snapshot_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    
    pool: "AgentPool" = Relationship(back_populates="metrics")
