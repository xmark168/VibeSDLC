"""Developer V2 Pydantic Schemas for LLM Structured Output."""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    """Router decision for story processing."""
    action: Literal["ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE", "CLARIFY", "RESPOND"] = Field(
        description="ANALYZE=parse story, PLAN=create impl plan, IMPLEMENT=code, VALIDATE=test, CLARIFY=need info, RESPOND=direct response"
    )
    task_type: Literal["feature", "bugfix", "refactor", "enhancement", "documentation"] = Field(
        description="Type of development task"
    )
    complexity: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Estimated complexity"
    )
    message: str = Field(description="Vietnamese status message for user")
    reason: str = Field(description="1-line reasoning for decision")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class StoryAnalysis(BaseModel):
    """Analysis result from parsing user story."""
    task_type: Literal["feature", "bugfix", "refactor", "enhancement", "documentation"]
    complexity: Literal["low", "medium", "high"]
    estimated_hours: float = Field(ge=0.5, le=100.0)
    summary: str = Field(description="Brief summary of what needs to be done")
    affected_files: List[str] = Field(default_factory=list, description="Files likely to be modified")
    dependencies: List[str] = Field(default_factory=list, description="External dependencies or blockers")
    risks: List[str] = Field(default_factory=list, description="Potential risks or concerns")
    suggested_approach: str = Field(description="Recommended implementation approach")


class PlanStep(BaseModel):
    """Single step in implementation plan."""
    order: int = Field(ge=1)
    description: str
    file_path: Optional[str] = None
    action: Literal["create", "modify", "delete", "test", "config"] = Field(default="modify")
    estimated_minutes: int = Field(default=30, ge=5, le=480)
    dependencies: List[int] = Field(default_factory=list, description="Order numbers of dependent steps")


class ImplementationPlan(BaseModel):
    """Complete implementation plan for a story."""
    story_summary: str
    steps: List[PlanStep]
    total_estimated_hours: float
    critical_path: List[int] = Field(default_factory=list, description="Step orders on critical path")
    rollback_plan: Optional[str] = None


class CodeChange(BaseModel):
    """Single code change to be made."""
    file_path: str
    action: Literal["create", "modify", "delete"]
    description: str
    code_snippet: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class ImplementationResult(BaseModel):
    """Result of code implementation."""
    success: bool
    files_created: List[str] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    files_deleted: List[str] = Field(default_factory=list)
    summary: str
    next_steps: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Result of validation/testing."""
    tests_passed: bool
    lint_passed: bool
    ac_verified: List[str] = Field(default_factory=list, description="Acceptance criteria that passed")
    ac_failed: List[str] = Field(default_factory=list, description="Acceptance criteria that failed")
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

