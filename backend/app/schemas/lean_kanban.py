"""Kanban schemas for WIP limits."""

from datetime import datetime
from typing import Optional
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


class WIPViolation(SQLModel):
    column_name: str
    current_count: int
    wip_limit: int
    new_count: int
    violation_type: str = "hard"
    message: str
