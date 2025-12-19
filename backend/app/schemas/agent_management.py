"""Agent management and pool operation schemas."""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from enum import Enum


# ===== System Status Schemas =====

class SystemStatusResponse(BaseModel):
    """System-wide operational status."""
    status: str
    paused_at: datetime | None = None
    maintenance_message: str | None = None
    active_pools: int
    total_agents: int
    accepting_tasks: bool


class EmergencyActionRequest(BaseModel):
    """Request for emergency system actions."""
    action: str
    message: str | None = None
    force: bool = False


# ===== Agent Configuration Schemas =====

class AgentConfigSchema(BaseModel):
    """Agent runtime configuration."""
    llm_config: dict
    system_prompt: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, gt=0)
    timeout_seconds: int | None = Field(None, gt=0)


class AgentConfigResponse(BaseModel):
    """Response with agent configuration."""
    agent_id: UUID
    role_type: str
    config: AgentConfigSchema
    updated_at: datetime


# ===== Bulk Operations Schemas =====

class BulkAgentRequest(BaseModel):
    """Request for bulk agent operations."""
    agent_ids: list[str] = Field(..., min_length=1)


class BulkSpawnRequest(BaseModel):
    """Request to spawn multiple agents."""
    pool_name: str
    role_type: str
    count: int = Field(..., ge=1, le=20)


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""
    success_count: int
    failed_count: int
    results: list[dict]
    total: int


# ===== Auto-Scaling Schemas =====

class ScalingTriggerType(str, Enum):
    """Auto-scaling trigger types."""
    LOAD = "load"
    SCHEDULE = "schedule"
    METRIC = "metric"


class ScalingAction(str, Enum):
    """Auto-scaling actions."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"


class AutoScalingRule(BaseModel):
    """Auto-scaling rule definition."""
    rule_id: str
    pool_name: str
    rule_name: str
    trigger_type: ScalingTriggerType
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    # Trigger configuration
    load_threshold: float | None = Field(None, ge=0.0, le=1.0)
    cron_expression: str | None = None
    metric_name: str | None = None
    metric_threshold: float | None = None
    
    # Scaling configuration
    target_count: int | None = Field(None, gt=0)
    scale_amount: int = Field(1, gt=0)
    min_agents: int = Field(1, ge=0)
    max_agents: int = Field(10, ge=1)
    role_type: str | None = None


class AutoScalingRuleCreate(BaseModel):
    """Request to create auto-scaling rule."""
    pool_name: str
    rule_name: str
    trigger_type: ScalingTriggerType
    enabled: bool = True
    
    # Trigger configuration
    load_threshold: float | None = Field(None, ge=0.0, le=1.0)
    cron_expression: str | None = None
    metric_name: str | None = None
    metric_threshold: float | None = None
    
    # Scaling configuration
    target_count: int | None = Field(None, gt=0)
    scale_amount: int = Field(1, gt=0)
    min_agents: int = Field(1, ge=0)
    max_agents: int = Field(10, ge=1)
    role_type: str | None = None


# ===== Token Monitoring Schemas =====

class AgentTokenStats(BaseModel):
    """Token usage stats for agent type."""
    agent_type: str
    total_tokens: int
    total_cost_usd: float
    execution_count: int
    average_tokens_per_execution: float


class PoolTokenStats(BaseModel):
    """Token usage stats for pool."""
    pool_name: str
    agents: list[AgentTokenStats]
    total_tokens: int
    total_cost_usd: float


class SystemTokenSummary(BaseModel):
    """System-wide token usage summary."""
    pools: list[PoolTokenStats]
    grand_total_tokens: int
    grand_total_cost_usd: float
    time_range: str
    generated_at: datetime
