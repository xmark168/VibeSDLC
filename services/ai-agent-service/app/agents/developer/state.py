"""
Developer Agent State Management

State models for Developer Agent orchestrator workflow.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskResult(BaseModel):
    """Result of processing a single task."""

    task_id: str
    task_type: str
    status: Literal["success", "failed", "skipped"] = "skipped"

    # Task context
    task_title: str = ""
    task_description: str = ""
    parent_context: str = ""
    enriched_description: str = ""

    # Subagent results
    planner_result: dict[str, Any] | None = None
    implementor_result: dict[str, Any] | None = None
    reviewer_result: dict[str, Any] | None = None

    # Execution metadata
    start_time: str | None = None
    end_time: str | None = None
    duration_seconds: float | None = None
    error_message: str | None = None


class SprintExecutionSummary(BaseModel):
    """Summary of sprint execution."""

    sprint_id: str = ""
    sprint_goal: str = ""

    # Task statistics
    total_assigned_items: int = 0
    eligible_tasks_count: int = 0
    processed_tasks_count: int = 0
    successful_tasks_count: int = 0
    failed_tasks_count: int = 0
    skipped_tasks_count: int = 0

    # Execution metadata
    start_time: str | None = None
    end_time: str | None = None
    total_duration_seconds: float | None = None

    # Results
    task_results: list[TaskResult] = Field(default_factory=list)


class DeveloperState(BaseModel):
    """State for Developer Agent orchestrator workflow."""

    # Input data
    sprint_data: dict[str, Any] = Field(default_factory=dict)
    backlog_data: list[dict[str, Any]] = Field(default_factory=list)

    # Configuration
    working_directory: str = "."
    model_name: str = "gpt-4o"
    session_id: str = ""

    # File paths
    backlog_path: str = ""
    sprint_path: str = ""

    # Workflow control
    current_phase: Literal[
        "initialize", "parse_sprint", "filter_tasks", "process_tasks", "finalize"
    ] = "initialize"

    # Task processing state
    current_task_index: int = 0
    eligible_tasks: list[dict[str, Any]] = Field(default_factory=list)

    # Execution results
    execution_summary: SprintExecutionSummary = Field(
        default_factory=SprintExecutionSummary
    )

    # Error handling
    continue_on_error: bool = True
    max_retries: int = 1

    # Tools output storage
    tools_output: dict[str, Any] = Field(default_factory=dict)
