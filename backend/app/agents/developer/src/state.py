"""Developer V2 State Definition."""

from typing import TypedDict, Literal, Any, List, Optional, Dict

Action = Literal["ANALYZE", "PLAN", "IMPLEMENT", "RESPOND", "END"]
TaskType = Literal["feature", "bugfix", "refactor", "enhancement", "documentation", "bug_fix"]
GraphTaskType = Literal["message", "implement_story"]
Complexity = Literal["low", "medium", "high"]


class DeveloperState(TypedDict, total=False):
    """LangGraph state schema for Developer V2 workflow."""

    # Input
    story_id: str
    story_code: str 
    epic: str
    story_title: str
    story_content: str
    story_description: str
    story_requirements: List[str]
    acceptance_criteria: List[str]
    project_id: str
    task_id: str
    user_id: str

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

    # Router/Chat
    graph_task_type: GraphTaskType  # Task type for graph routing
    user_message: str  # User message content (for chat nodes)
    response: str  # Agent response (from chat nodes)
