"""Project rules schemas."""

from uuid import UUID
from datetime import datetime
from sqlmodel import SQLModel
from typing import Optional


class ProjectRulesCreate(SQLModel):
    project_id: UUID
    po_prompt: Optional[str] = None
    dev_prompt: Optional[str] = None
    tester_prompt: Optional[str] = None


class ProjectRulesUpdate(SQLModel):
    po_prompt: Optional[str] = None
    dev_prompt: Optional[str] = None
    tester_prompt: Optional[str] = None


class ProjectRulesPublic(SQLModel):
    id: UUID
    project_id: UUID
    po_prompt: Optional[str] = None
    dev_prompt: Optional[str] = None
    tester_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime
