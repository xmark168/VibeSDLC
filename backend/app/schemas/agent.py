"""Agent-related schemas (includes pool management)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import SQLModel

from app.models import AgentStatus, PoolType


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
    health_check_interval: int = Field(default=60, ge=10)


class CreatePoolRequest(BaseModel):
    pool_name: str
    role_type: str
    config: PoolConfigSchema = Field(default_factory=PoolConfigSchema)


class SpawnAgentRequest(BaseModel):
    project_id: UUID
    pool_name: str = "universal_pool"
    role_type: str
    human_name: Optional[str] = None
    heartbeat_interval: int = Field(default=30, ge=10)
    max_idle_time: int = Field(default=300, ge=60)


class TerminateAgentRequest(BaseModel):
    pool_name: str
    agent_id: UUID


class PoolResponse(BaseModel):
    pool_name: str
    role_type: str
    total_agents: int = 0
    active_agents: int = 0
    busy_agents: int = 0
    idle_agents: int = 0
    max_agents: int = 100
    is_running: bool = True
    total_spawned: int = 0
    total_terminated: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    success_rate: float = 0.0
    load: float = 0.0
    agents: list[dict] = []


class SystemStatsResponse(BaseModel):
    uptime_seconds: float
    total_pools: int
    total_agents: int
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    success_rate: float = 0.0
    recent_alerts: int = 0
    pools: list[PoolResponse]


# ===== Pool DB Schemas =====

class AgentPoolPublic(SQLModel):
    """Pool database record schema."""
    id: UUID
    pool_name: str
    role_type: Optional[str]
    pool_type: PoolType
    max_agents: int
    health_check_interval: int
    llm_model_config: Optional[dict] = None
    allowed_template_ids: Optional[list[str]] = None
    is_active: bool
    last_started_at: Optional[datetime] = None
    last_stopped_at: Optional[datetime] = None
    total_spawned: int
    total_terminated: int
    current_agent_count: int
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    auto_created: bool
    created_at: datetime
    updated_at: datetime


class UpdatePoolConfigRequest(BaseModel):
    """Update pool configuration request."""
    max_agents: Optional[int] = Field(default=None, ge=1)
    health_check_interval: Optional[int] = Field(default=None, ge=10)
    llm_model_config: Optional[dict] = None
    allowed_template_ids: Optional[list[str]] = None


class AgentPoolMetricsPublic(SQLModel):
    """Pool metrics record schema."""
    id: UUID
    pool_id: UUID
    period_start: datetime
    period_end: datetime
    total_tokens_used: int
    tokens_per_model: dict
    total_requests: int
    requests_per_model: dict
    peak_agent_count: int
    avg_agent_count: float
    total_executions: int
    successful_executions: int
    failed_executions: int
    avg_execution_duration_ms: Optional[float] = None
    snapshot_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class CreatePoolRequestExtended(BaseModel):
    """Extended pool creation request with DB fields."""
    pool_name: str
    role_type: Optional[str] = None
    pool_type: PoolType = Field(default=PoolType.FREE)
    max_agents: int = Field(default=100, ge=1)
    health_check_interval: int = Field(default=60, ge=10)
    llm_model_config: Optional[dict] = None
    allowed_template_ids: Optional[list[str]] = None


class ScalePoolRequest(BaseModel):
    """Scale pool request."""
    target_agents: int = Field(ge=0)


class PoolSuggestion(BaseModel):
    """Pool creation suggestion."""
    reason: str
    recommended_pool_name: str
    role_type: Optional[str] = None
    estimated_agents: int


# ===== Agent Activity Schemas =====

class CurrentTaskInfo(BaseModel):
    """Current task being executed by agent."""
    id: UUID
    name: str
    status: str
    progress: Optional[int] = None
    started_at: datetime


class RecentActivity(BaseModel):
    """Recent activity item."""
    id: UUID
    activity_type: str  # "message", "question", "execution"
    content: str
    created_at: datetime


class AgentActivityResponse(BaseModel):
    """Agent activity response for popup."""
    agent_id: UUID
    human_name: str
    role_type: str
    status: str
    status_message: Optional[str] = None
    skills: list[str] = []
    current_task: Optional[CurrentTaskInfo] = None
    recent_activities: list[RecentActivity] = []
