"""Developer V2 Schemas for LLM Structured Output and type-safe state access."""

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# State Models (for type-safe state access via state_helpers.py)
# =============================================================================

class StoryInput(BaseModel):
    """Story input fields from Kafka delegation."""
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
    """Git workspace/worktree state (path, branch, ready status)."""
    path: str = ""
    branch: str = ""
    main: str = ""
    ready: bool = False
    index_ready: bool = False


class PlanState(BaseModel):
    """Implementation plan state. Order: database -> API -> components -> pages."""
    steps: List[dict] = Field(default_factory=list)
    logic_analysis: List[List[str]] = Field(default_factory=list)
    current_step: int = 0
    total_steps: int = 0
    dependencies_content: Dict[str, str] = Field(default_factory=dict)


class ReviewState(BaseModel):
    """Code review state. LGTM=approve, LBTM=reject. Max 2 LBTM/step."""
    result: Optional[str] = None
    feedback: Optional[str] = None
    details: Optional[str] = None
    count: int = 0
    total_lbtm: int = 0


class DebugState(BaseModel):
    """Debug/error recovery state. Max 5 iterations."""
    count: int = 0
    max_attempts: int = 5
    history: List[Dict[str, Any]] = Field(default_factory=list)
    error_analysis: Optional[Dict[str, Any]] = None


class SummarizeState(BaseModel):
    """IS_PASS gate state. YES=complete, NO=needs work. Max 2 NO iterations."""
    summary: Optional[str] = None
    todos: Dict[str, str] = Field(default_factory=dict)
    is_pass: Optional[str] = None
    feedback: Optional[str] = None
    count: int = 0


class RunCodeState(BaseModel):
    """Build/test execution state. PASS=success, FAIL=routes to analyze_error."""
    status: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    stdout: str = ""
    stderr: str = ""


# =============================================================================
# LLM Structured Output Models (for with_structured_output)
# =============================================================================

class StoryAnalysis(BaseModel):
    """Story analysis result from LLM."""
    task_type: Literal["feature", "bugfix", "refactor", "enhancement", "documentation"]
    complexity: Literal["low", "medium", "high"]
    estimated_hours: float = Field(ge=0.5, le=100.0)
    summary: str
    affected_files: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    suggested_approach: str


class PlanStep(BaseModel):
    """Single step in implementation plan. One file per step."""
    order: int = Field(ge=1)
    description: str
    file_path: Optional[str] = None
    action: Literal["create", "modify", "delete", "test", "config", "review"] = "modify"


class PlanTask(BaseModel):
    """Abstract task in implementation plan (WHAT, not HOW)."""
    order: int = Field(ge=1)
    task: str


class ImplementationPlan(BaseModel):
    """Complete implementation plan from analyze_and_plan node."""
    story_summary: str
    tasks: List[PlanTask]
