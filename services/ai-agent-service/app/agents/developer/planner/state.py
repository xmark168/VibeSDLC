"""
Planner State Management

State model cho planner workflow với các fields cần thiết để tương thích
với implementor và code_reviewer subagents.
"""

from typing import Any, Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class TaskRequirements(BaseModel):
    """Structured requirements từ task parsing phase."""

    task_id: str = ""
    task_title: str = ""
    requirements: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    business_rules: dict[str, str] = Field(default_factory=dict)
    technical_specs: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class CodebaseAnalysis(BaseModel):
    """Structured codebase analysis từ analysis phase."""

    files_to_create: list[dict[str, Any]] = Field(default_factory=list)
    files_to_modify: list[dict[str, Any]] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    database_changes: list[dict[str, Any]] = Field(default_factory=list)
    api_endpoints: list[dict[str, Any]] = Field(default_factory=list)
    testing_requirements: dict[str, Any] = Field(default_factory=dict)
    external_dependencies: list[dict[str, Any]] = Field(default_factory=list)
    internal_dependencies: list[dict[str, Any]] = Field(default_factory=list)


class DependencyMapping(BaseModel):
    """Dependency mapping và execution order."""

    execution_order: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: dict[str, Any] = Field(default_factory=dict)
    blocking_steps: list[int] = Field(default_factory=list)
    parallel_opportunities: list[list[int]] = Field(default_factory=list)


class ImplementationPlan(BaseModel):
    """Final implementation plan output."""

    plan_type: Literal["simple", "complex"] = "simple"
    task_id: str = ""
    description: str = ""
    complexity_score: int = 0
    complexity_reasoning: str = ""

    approach: dict[str, Any] = Field(default_factory=dict)
    implementation_steps: list[dict[str, Any]] = Field(default_factory=list)
    subtasks: list[dict[str, Any]] = Field(default_factory=list)  # For complex plans
    execution_strategy: dict[str, Any] = Field(
        default_factory=dict
    )  # For complex plans

    testing_requirements: dict[str, Any] = Field(default_factory=dict)
    rollback_plan: dict[str, Any] = Field(default_factory=dict)

    total_estimated_hours: float = 0.0
    optimized_duration: str | None = None
    story_points: int = 0

    risks: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class WebSearchResults(BaseModel):
    """Kết quả web search từ Tavily."""

    performed: bool = False
    queries: list[str] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    search_time: float = 0.0
    reason_for_search: str = ""
    reason_for_skip: str = ""


class PlannerState(BaseModel):
    """State cho Planner Agent workflow."""

    # Input
    task_description: str = ""
    codebase_context: str = ""
    codebase_path: str = ""  # Dynamic codebase path for analysis (empty = use default)

    # Tech stack detection
    tech_stack: str = ""  # e.g., "nodejs", "fastapi", "react-vite"

    # Daytona Sandbox Integration
    sandbox_id: str = ""  # ID của Daytona sandbox instance
    github_repo_url: str = ""  # URL của GitHub repository cần clone vào sandbox

    # Phase outputs
    task_requirements: TaskRequirements = Field(default_factory=TaskRequirements)
    websearch_results: WebSearchResults = Field(default_factory=WebSearchResults)
    codebase_analysis: CodebaseAnalysis = Field(default_factory=CodebaseAnalysis)
    dependency_mapping: DependencyMapping = Field(default_factory=DependencyMapping)
    implementation_plan: ImplementationPlan = Field(default_factory=ImplementationPlan)

    # Workflow control
    current_phase: Literal[
        "initialize",
        "parse_task",
        "websearch",
        "analyze_codebase",
        "map_dependencies",
        "generate_plan",
        "validate_plan",
        "finalize",
    ] = "initialize"
    max_iterations: int = 3
    current_iteration: int = 0

    # Tools output storage
    tools_output: dict[str, Any] = Field(default_factory=dict)

    # Messages for LangGraph
    messages: list[BaseMessage] = Field(default_factory=list)

    # Validation
    validation_score: float = 0.0
    validation_issues: list[str] = Field(default_factory=list)
    can_proceed: bool = False

    # Status tracking
    status: str = "initial"
    error_message: str = ""

    # Final output for implementor
    final_plan: dict[str, Any] = Field(default_factory=dict)
    ready_for_implementation: bool = False
