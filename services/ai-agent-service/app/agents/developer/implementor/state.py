"""
Implementor State Management

State model cho implementor workflow để thực hiện implementation plan
từ Planner Agent với Git workflow và file operations.
"""

from typing import Any, Literal

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class FileChange(BaseModel):
    """Thông tin về file change cần thực hiện."""

    file_path: str
    operation: Literal["create", "modify", "delete"] = "modify"
    content: str = ""
    change_type: Literal["full_file", "incremental"] = "incremental"
    target_function: str = ""  # For incremental changes
    target_class: str = ""  # For incremental changes
    line_range: tuple[int, int] | None = None  # For specific line modifications
    description: str = ""


class TestExecution(BaseModel):
    """Kết quả test execution."""

    test_command: str = ""
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    passed: bool = False
    failed_tests: list[str] = Field(default_factory=list)


class RunExecution(BaseModel):
    """Kết quả run and verify execution."""

    run_command: str = ""
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    success: bool = False
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3


class GitOperation(BaseModel):
    """Thông tin về Git operations."""

    operation: Literal["create_branch", "commit", "push", "create_pr"] = "commit"
    branch_name: str = ""
    commit_hash: str = ""
    commit_message: str = ""
    pr_url: str = ""
    pr_title: str = ""
    pr_description: str = ""
    files_changed: list[str] = Field(default_factory=list)
    status: str = ""


class ImplementorState(BaseModel):
    """State cho Implementor Agent workflow."""

    # Input từ Planner Agent
    task_id: str = ""
    task_description: str = ""
    implementation_plan: dict[str, Any] = Field(default_factory=dict)

    # Sandbox và codebase info
    sandbox_id: str = ""
    codebase_path: str = ""
    github_repo_url: str = ""

    # Project type và tech stack
    is_new_project: bool = False
    tech_stack: str = ""  # e.g., "fastapi", "nextjs", "react-vite"
    boilerplate_template: str = ""  # Path to boilerplate template

    # Git workflow
    base_branch: str = "main"
    feature_branch: str = ""
    current_branch: str = ""
    git_operations: list[GitOperation] = Field(default_factory=list)

    # File operations
    files_to_create: list[FileChange] = Field(default_factory=list)
    files_to_modify: list[FileChange] = Field(default_factory=list)
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)

    # Testing
    test_execution: TestExecution = Field(default_factory=TestExecution)
    tests_passed: bool = False

    # Run and Verify (before commit)
    run_execution: RunExecution = Field(default_factory=RunExecution)
    run_verified: bool = False
    run_process_id: int | None = None  # PID of running process to kill later

    # Workflow control
    current_phase: Literal[
        "initialize",
        "setup_branch",
        "copy_boilerplate",
        "generate_code",
        "implement_files",
        "run_tests",
        "run_and_verify",
        "commit_changes",
        "create_pr",
        "finalize",
    ] = "initialize"
    max_iterations: int = 3
    current_iteration: int = 0

    # Tools output storage
    tools_output: dict[str, Any] = Field(default_factory=dict)

    # Messages for LangGraph
    messages: list[BaseMessage] = Field(default_factory=list)

    # Status tracking
    status: str = "initial"
    error_message: str = ""

    # Final output
    implementation_complete: bool = False
    final_commit_hash: str = ""
    final_pr_url: str = ""
    summary: dict[str, Any] = Field(default_factory=dict)
