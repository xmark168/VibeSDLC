"""Developer V2 Schemas for LLM Structured Output."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """Single step in implementation plan."""
    order: int = Field(ge=1)
    description: str
    file_path: Optional[str] = None
    action: Literal["create", "modify", "delete", "test", "config", "review"] = "modify"
