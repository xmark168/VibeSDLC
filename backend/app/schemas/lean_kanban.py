"""Lean Kanban schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class WIPLimitCreate(SQLModel):
    project_id: UUID
    column_name: str
    wip_limit: int = Field(ge=0)
    limit_type: str = Field(default="hard")


class WIPLimitUpdate(SQLModel):
    wip_limit: int = Field(ge=0)
    limit_type: Optional[str] = None


class WIPLimitPublic(SQLModel):
    id: UUID
    project_id: UUID
    column_name: str
    wip_limit: int
    limit_type: str
    created_at: datetime
    updated_at: datetime


class WIPLimitsPublic(SQLModel):
    data: list[WIPLimitPublic]
    count: int


class WorkflowPolicyCreate(SQLModel):
    project_id: UUID
    from_status: str
    to_status: str
    criteria: Optional[dict[str, Any]] = None
    is_active: bool = Field(default=True)


class WorkflowPolicyUpdate(SQLModel):
    criteria: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    definition_of_ready: Optional[list[str]] = None
    definition_of_done: Optional[list[str]] = None


class WorkflowPolicyPublic(SQLModel):
    id: UUID
    project_id: UUID
    from_status: str
    to_status: str
    criteria: Optional[dict[str, Any]] = None
    is_active: bool
    definition_of_ready: Optional[list[str]] = None
    definition_of_done: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime


class WorkflowPoliciesPublic(SQLModel):
    data: list[WorkflowPolicyPublic]
    count: int


class StoryFlowMetrics(SQLModel):
    id: UUID
    title: str
    status: str
    created_at: datetime
    cycle_time_hours: Optional[float] = None
    lead_time_hours: Optional[float] = None
    age_in_current_status_hours: float
    age_in_current_status_days: float
    blocked: bool = False
    blocker_count: int = 0


class ProjectFlowMetrics(SQLModel):
    avg_cycle_time_hours: Optional[float] = None
    avg_lead_time_hours: Optional[float] = None
    throughput_per_week: float
    total_completed: int
    work_in_progress: int
    aging_items: list[dict[str, Any]]
    bottlenecks: dict[str, Any]


class WIPViolation(SQLModel):
    column_name: str
    current_count: int
    wip_limit: int
    new_count: int
    violation_type: str = "hard"
    message: str
