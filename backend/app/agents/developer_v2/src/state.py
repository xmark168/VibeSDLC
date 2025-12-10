"""Developer V2 State Definition."""

from typing import TypedDict, Literal, Any, List, Optional, Dict

Action = Literal["ANALYZE", "PLAN", "IMPLEMENT", "RESPOND"]
TaskType = Literal["feature", "bugfix", "refactor", "enhancement", "documentation", "bug_fix"]
Complexity = Literal["low", "medium", "high"]


class DeveloperState(TypedDict, total=False):
    """LangGraph state schema for Developer V2 workflow."""

    # Input
    story_id: str
    story_code: str  # Unique story code (e.g., "US-001", "EPIC-001-US-001")
    epic: str
    story_title: str
    story_content: str
    story_description: str
    story_requirements: List[str]
    acceptance_criteria: List[str]
    project_id: str
    task_id: str
    user_id: str
    langfuse_handler: Any
    langfuse_client: Any

    # Flow control
    action: Action
    task_type: TaskType
    complexity: Complexity

    # Planning
    implementation_plan: List[dict]
    current_step: int
    total_steps: int
    dependencies_content: Dict[str, str]

    # Implementation
    files_modified: List[str]

    # Workspace
    workspace_path: str
    main_workspace: str
    workspace_ready: bool
    branch_name: str
    index_ready: bool

    # Output
    message: str
    error: Optional[str]

    # Run code
    run_result: Optional[Dict[str, Any]]
    run_stdout: Optional[str]
    run_stderr: Optional[str]
    run_status: Optional[str]
    
    # Dev server
    dev_server_port: Optional[int]
    dev_server_pid: Optional[int]

    # Debug
    debug_count: int
    debug_history: Optional[List[Dict[str, Any]]]
    error_analysis: Optional[Dict[str, Any]]

    # React loop
    react_loop_count: int
    react_mode: bool

    # Skills
    tech_stack: str
    skill_registry: Any
    available_skills: List[str]

    # Context
    project_context: Optional[str]
    project_config: Optional[Dict[str, Any]]
    agents_md: Optional[str]

    # Review
    review_result: Optional[str]
    review_feedback: Optional[str]
    review_count: int
    total_lbtm_count: int
    step_lbtm_counts: Dict[str, int]

    # Summarize
    summarize_feedback: Optional[str]
