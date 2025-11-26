"""Project rules schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import SQLModel


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
