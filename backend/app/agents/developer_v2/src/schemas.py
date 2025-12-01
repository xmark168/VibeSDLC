"""Developer V2 Schemas for LLM Structured Output."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class StoryAnalysis(BaseModel):
    """Story analysis result."""
    task_type: Literal["feature", "bugfix", "refactor", "enhancement", "documentation"]
    complexity: Literal["low", "medium", "high"]
    estimated_hours: float = Field(ge=0.5, le=100.0)
    summary: str
    affected_files: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    suggested_approach: str


class PlanStep(BaseModel):
    """Single step in implementation plan."""
    order: int = Field(ge=1)
    description: str
    file_path: Optional[str] = None
    action: Literal["create", "modify", "delete", "test", "config"] = "modify"


class ImplementationPlan(BaseModel):
    """Implementation plan for a story."""
    story_summary: str
    steps: List[PlanStep]
