"""Project-related schemas."""

from uuid import UUID
from datetime import datetime
from sqlmodel import SQLModel
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import AgentPublic


class ProjectCreate(SQLModel):
    name: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    tech_stack: Optional[list[str]] = None


class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    repository_url: Optional[str] = None
    tech_stack: Optional[list[str]] = None


class ProjectPublic(SQLModel):
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    tech_stack: Optional[list[str]] = None
    owner_id: UUID
    is_init: bool
    created_at: datetime
    updated_at: datetime


class ProjectsPublic(SQLModel):
    data: list[ProjectPublic]
    count: int
