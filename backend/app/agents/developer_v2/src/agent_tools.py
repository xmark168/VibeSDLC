"""Agent Tools for Developer V2 - LangChain tool definitions."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from langchain.tools import tool


# =============================================================================
# Input Schemas (Pydantic models for complex validation)
# =============================================================================

class RoutingDecisionInput(BaseModel):
    """Input schema for routing decision."""
    action: Literal["ANALYZE", "PLAN", "IMPLEMENT", "CLARIFY", "RESPOND"] = Field(
        description="Action to take: ANALYZE, PLAN, IMPLEMENT, CLARIFY, or RESPOND"
    )
    task_type: Literal["feature", "bugfix", "refactor", "enhancement", "documentation"] = Field(
        description="Type of task"
    )
    complexity: Literal["low", "medium", "high"] = Field(
        description="Complexity level"
    )
    message: str = Field(description="Vietnamese status message for user")
    reason: str = Field(description="1-line reasoning for decision")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score 0.0-1.0")


class StoryAnalysisInput(BaseModel):
    """Input schema for story analysis."""
    task_type: Literal["feature", "bugfix", "refactor", "enhancement", "documentation"] = Field(
        description="Type of task"
    )
    complexity: Literal["low", "medium", "high"] = Field(description="Complexity level")
    estimated_hours: float = Field(ge=0.5, le=100, description="Estimated hours (0.5-100)")
    summary: str = Field(description="Brief summary of what needs to be done")
    affected_files: List[str] = Field(description="Files likely to be modified")
    suggested_approach: str = Field(description="Recommended implementation approach")
    dependencies: Optional[List[str]] = Field(default=None, description="External dependencies or blockers")
    risks: Optional[List[str]] = Field(default=None, description="Potential risks or concerns")


class PlanStep(BaseModel):
    """Single step in implementation plan."""
    order: int = Field(description="Step order number")
    description: str = Field(description="What this step does")
    file_path: str = Field(description="File to create/modify")
    action: Literal["create", "modify", "delete"] = Field(description="Action type")
    estimated_minutes: int = Field(default=30, description="Estimated minutes")
    dependencies: List[int] = Field(default_factory=list, description="List of step orders this depends on")


class ImplementationPlanInput(BaseModel):
    """Input schema for implementation plan."""
    story_summary: str = Field(description="Brief summary of the implementation")
    steps: List[PlanStep] = Field(description="List of implementation steps")
    total_estimated_hours: float = Field(description="Total estimated hours")
    critical_path: Optional[List[int]] = Field(default=None, description="Step orders on critical path")
    rollback_plan: Optional[str] = Field(default=None, description="How to rollback if needed")


class CodeChangeInput(BaseModel):
    """Input schema for code change."""
    file_path: str = Field(description="Path to the file (e.g., 'app/page.tsx')")
    action: Literal["create", "modify", "delete"] = Field(description="Action type")
    description: str = Field(description="What the change does")
    code_snippet: str = Field(description="The COMPLETE code content for the file")
    line_start: Optional[int] = Field(default=None, description="Starting line for modify")
    line_end: Optional[int] = Field(default=None, description="Ending line for modify")


class SystemDesignInput(BaseModel):
    """Input schema for system design."""
    data_structures: str = Field(description="Class/interface definitions in mermaid classDiagram format")
    api_interfaces: str = Field(description="API method signatures and interfaces")
    call_flow: str = Field(description="Sequence diagram in mermaid sequenceDiagram format")
    design_notes: str = Field(description="Key design decisions and rationale")
    file_structure: List[str] = Field(description="List of files to be created")


# =============================================================================
# Tools
# =============================================================================

@tool("submit_routing_decision", args_schema=RoutingDecisionInput)
def submit_routing_decision(
    action: str,
    task_type: str,
    complexity: str,
    message: str,
    reason: str,
    confidence: float = 0.8
) -> str:
    """Submit routing decision for the story. You MUST call this tool with your decision."""
    return f"Decision submitted: {action}"


@tool("submit_story_analysis", args_schema=StoryAnalysisInput)
def submit_story_analysis(
    task_type: str,
    complexity: str,
    estimated_hours: float,
    summary: str,
    affected_files: List[str],
    suggested_approach: str,
    dependencies: Optional[List[str]] = None,
    risks: Optional[List[str]] = None
) -> str:
    """Submit story analysis result. You MUST call this tool with your analysis."""
    return f"Analysis submitted: {task_type}, {complexity}, {estimated_hours}h"


@tool("submit_implementation_plan", args_schema=ImplementationPlanInput)
def submit_implementation_plan(
    story_summary: str,
    steps: List[dict],
    total_estimated_hours: float,
    critical_path: Optional[List[int]] = None,
    rollback_plan: Optional[str] = None
) -> str:
    """Submit implementation plan. You MUST call this tool with your plan."""
    return f"Plan submitted: {len(steps)} steps, {total_estimated_hours}h"


@tool("submit_code_change", args_schema=CodeChangeInput)
def submit_code_change(
    file_path: str,
    action: str,
    description: str,
    code_snippet: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None
) -> str:
    """Submit code change. You MUST call this tool with the complete code."""
    return f"Code submitted: {action} {file_path}"


@tool("submit_system_design", args_schema=SystemDesignInput)
def submit_system_design(
    data_structures: str,
    api_interfaces: str,
    call_flow: str,
    design_notes: str,
    file_structure: List[str]
) -> str:
    """Submit system design. You MUST call this tool with your design."""
    return f"Design submitted: {len(file_structure)} files"
