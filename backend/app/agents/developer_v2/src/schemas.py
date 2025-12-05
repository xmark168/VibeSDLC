"""Developer V2 Schemas for LLM Structured Output."""

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# State Models (for type-safe state access)
# =============================================================================

class StoryInput(BaseModel):
    """Story input fields."""
    story_id: str = ""
    epic: str = ""
    title: str = ""
    description: str = ""
    requirements: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    project_id: str = ""
    task_id: str = ""
    user_id: str = ""


class WorkspaceState(BaseModel):
    """Workspace context fields."""
    path: str = ""
    branch: str = ""
    main: str = ""
    ready: bool = False
    index_ready: bool = False


class PlanState(BaseModel):
    """Planning state fields."""
    steps: List[dict] = Field(default_factory=list)
    logic_analysis: List[List[str]] = Field(default_factory=list)
    current_step: int = 0
    total_steps: int = 0
    dependencies_content: Dict[str, str] = Field(default_factory=dict)


class ReviewState(BaseModel):
    """Review state fields (LGTM/LBTM)."""
    result: Optional[str] = None
    feedback: Optional[str] = None
    details: Optional[str] = None
    count: int = 0
    total_lbtm: int = 0


class DebugState(BaseModel):
    """Debug/error handling state."""
    count: int = 0
    max_attempts: int = 5
    history: List[Dict[str, Any]] = Field(default_factory=list)
    error_analysis: Optional[Dict[str, Any]] = None


class SummarizeState(BaseModel):
    """Summarize state fields (IS_PASS)."""
    summary: Optional[str] = None
    todos: Dict[str, str] = Field(default_factory=dict)
    is_pass: Optional[str] = None
    feedback: Optional[str] = None
    count: int = 0


class RunCodeState(BaseModel):
    """Run code/test state."""
    status: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    stdout: str = ""
    stderr: str = ""


# =============================================================================
# LLM Structured Output Models
# =============================================================================

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
    """Single step in implementation plan (legacy, for backwards compatibility)."""
    order: int = Field(ge=1)
    description: str
    file_path: Optional[str] = None
    action: Literal["create", "modify", "delete", "test", "config", "review"] = "modify"


class PlanTask(BaseModel):
    """Single task in implementation plan (abstract)."""
    order: int = Field(ge=1)
    task: str  # Abstract description of WHAT to do


class ImplementationPlan(BaseModel):
    """Implementation plan for a story."""
    story_summary: str
    tasks: List[PlanTask]
