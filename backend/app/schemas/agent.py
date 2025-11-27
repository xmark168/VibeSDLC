"""Agent-related schemas (includes pool management)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import SQLModel

from app.models import AgentStatus


class AgentBase(SQLModel):
    name: str
    human_name: str
    role_type: str
    agent_type: Optional[str] = None


class AgentCreate(SQLModel):
    project_id: UUID
    role_type: str
    human_name: Optional[str] = None


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
    
    persona_template_id: Optional[UUID] = None
    personality_traits: list[str] = []
    communication_style: Optional[str] = None
    persona_metadata: Optional[dict] = None
    
    created_at: datetime
    updated_at: datetime


class AgentsPublic(SQLModel):
    data: list[AgentPublic]
    count: int


class PoolConfigSchema(BaseModel):
    max_agents: int = Field(default=10, ge=1)


class CreatePoolRequest(BaseModel):
    role_type: str
    config: PoolConfigSchema = Field(default_factory=PoolConfigSchema)


class SpawnAgentRequest(BaseModel):
    project_id: UUID
    pool_name: str
    role_type: str
    human_name: Optional[str] = None


class TerminateAgentRequest(BaseModel):
    pool_name: str
    agent_id: UUID


class PoolResponse(BaseModel):
    pool_name: str
    role_type: str
    active_agents: int
    max_agents: int
    total_spawned: int
    total_terminated: int
    is_running: bool
    agents: list[dict]


class SystemStatsResponse(BaseModel):
    uptime_seconds: float
    total_pools: int
    total_agents: int
    pools: list[PoolResponse]
