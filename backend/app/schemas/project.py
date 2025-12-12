"""Project-related schemas."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from pydantic import field_validator
from sqlmodel import SQLModel

if TYPE_CHECKING:
    from .agent import AgentPublic


class ProjectCreate(SQLModel):
    name: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    tech_stack: Optional[list[str]] = None
    agent_personas: Optional[dict[str, str]] = None  # {"team_leader": "persona_id", ...}

    @field_validator('tech_stack', mode='before')
    @classmethod
    def normalize_tech_stack(cls, v: Union[str, list[str], None]) -> Optional[list[str]]:
        """Convert string tech_stack to list for backward compatibility."""
        if v is None:
            return None
        if isinstance(v, str):
            # Convert single string to list
            return [v] if v else None
        return v


class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    repository_url: Optional[str] = None
    tech_stack: Optional[list[str]] = None

    @field_validator('tech_stack', mode='before')
    @classmethod
    def normalize_tech_stack(cls, v: Union[str, list[str], None]) -> Optional[list[str]]:
        """Convert string tech_stack to list for backward compatibility."""
        if v is None:
            return None
        if isinstance(v, str):
            # Convert single string to list
            return [v] if v else None
        return v


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

    @field_validator('tech_stack', mode='before')
    @classmethod
    def normalize_tech_stack(cls, v: Union[str, list[str], None]) -> Optional[list[str]]:
        """Convert string tech_stack to list for backward compatibility."""
        if v is None:
            return None
        if isinstance(v, str):
            # Convert single string to list
            return [v] if v else None
        return v


class ProjectsPublic(SQLModel):
    data: list[ProjectPublic]
    count: int
