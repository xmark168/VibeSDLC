"""Credit and token usage schemas."""

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum


class CreditActivityType(str, Enum):
    """Types of credit activities."""
    PURCHASE = "purchase"
    DEDUCTION = "deduction"
    REFUND = "refund"
    GRANT = "grant"


class CreditActivityItem(BaseModel):
    """Credit activity item for user display."""
    id: str
    created_at: datetime
    activity_type: str
    amount: int
    tokens_used: int | None
    model_used: str | None
    llm_calls: int | None
    reason: str
    agent_name: str | None
    project_name: str | None
    story_title: str | None
    task_type: str | None


class CreditActivityResponse(BaseModel):
    """Paginated credit activity response."""
    total: int
    items: list[CreditActivityItem]
    summary: dict


class TokenMonitoringStats(BaseModel):
    """System-wide token monitoring stats."""
    today: dict
    this_month: dict
    top_users: list[dict]
    top_projects: list[dict]
    model_breakdown: dict
