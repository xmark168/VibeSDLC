"""Agent-related schemas (includes pool management)."""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from sqlmodel import SQLModel
from typing import Optional
from app.models import AgentStatus


class AgentBase(SQLModel):
    name: str
    human_name: str
    role_type: str  # team_leader, business_analyst, developer, tester
    agent_type: Optional[str] = None


class AgentCreate(SQLModel):
    project_id: UUID
    role_type: str
    human_name: Optional[str] = None  # Auto-generated if not provided


class AgentUpdate(SQLModel):
    human_name: Optional[str] = None
    status: Optional[AgentStatus] = None


class AgentPublic(SQLModel):
    id: UUID
    project_id: UUID
    name: str
    human_name: str
    role_type: str
    agent_type: Optional[str] = None
    status: AgentStatus
    created_at: datetime
    updated_at: datetime


class AgentsPublic(SQLModel):
    data: list[AgentPublic]
    count: int


class PoolConfigSchema(BaseModel):
    """Pool configuration schema."""
    max_agents: int = Field(default=10, ge=1)


class CreatePoolRequest(BaseModel):
    """Request to create agent pool."""
    role_type: str = Field(..., description="Role type: team_leader, business_analyst, developer, tester")
    config: PoolConfigSchema = Field(default_factory=PoolConfigSchema)


class SpawnAgentRequest(BaseModel):
    """Request to spawn agent."""
    project_id: UUID = Field(..., description="Project ID to assign agent to")
    pool_name: str = Field(..., description="Pool name")
    role_type: str = Field(..., description="Agent role type")
    human_name: Optional[str] = Field(None, description="Optional human-friendly name")


class TerminateAgentRequest(BaseModel):
    """Request to terminate agent."""
    pool_name: str = Field(..., description="Pool name")
    agent_id: UUID = Field(..., description="Agent ID to terminate")


class PoolResponse(BaseModel):
    """Pool information response."""
    pool_name: str
    role_type: str
    active_agents: int
    max_agents: int
    total_spawned: int
    total_terminated: int
    is_running: bool
    agents: list[dict]  # Basic agent info


class SystemStatsResponse(BaseModel):
    """System statistics response."""
    uptime_seconds: float
    total_pools: int
    total_agents: int
    pools: list[PoolResponse]
