"""Developer V2 State Definition.

LangGraph state schema with sections: INPUT, FLOW CONTROL, ANALYSIS, PLANNING,
IMPLEMENTATION, WORKSPACE, OUTPUT, RUN CODE, DEBUG, REACT LOOP, SKILLS, CONTEXT,
REVIEW, SUMMARIZE. All fields optional (total=False).
"""

from typing import TypedDict, Literal, Any, List, Optional, Dict

Action = Literal["ANALYZE", "PLAN", "IMPLEMENT", "RESPOND"]
TaskType = Literal["feature", "bugfix", "refactor", "enhancement", "documentation", "bug_fix"]
Complexity = Literal["low", "medium", "high"]


class DeveloperState(TypedDict, total=False):
    """LangGraph state schema for Developer V2 workflow.

    All fields optional. Flows: setup_workspace -> analyze_and_plan -> implement
    -> review -> summarize -> run_code -> (analyze_error if FAIL).
    """

    # ==================== INPUT ====================
    story_id: str
    epic: str
    story_title: str
    story_description: str
    story_requirements: List[str]
    acceptance_criteria: List[str]
    project_id: str
    task_id: str
    user_id: str
    langfuse_handler: Any

    # Flow control
    action: Action
    task_type: TaskType
    complexity: Complexity
    use_code_review: bool

    # Analysis
    analysis_result: dict
    affected_files: List[str]
    dependencies: List[str]
    risks: List[str]
    estimated_hours: float

    # Planning
    implementation_plan: List[dict]
    current_step: int
    total_steps: int
    logic_analysis: List[List[str]]
    dependencies_content: Dict[str, str]

    # Implementation
    files_created: List[str]
    files_modified: List[str]

    # Workspace
    workspace_path: str
    branch_name: str
    main_workspace: str
    workspace_ready: bool
    index_ready: bool
    merged: bool

    # Output
    message: str
    error: Optional[str]

    # Run code
    run_result: Optional[Dict[str, Any]]
    run_stdout: Optional[str]
    run_stderr: Optional[str]
    run_status: Optional[str]
    test_command: Optional[List[str]]

    # Debug
    debug_count: int
    max_debug: int
    debug_history: Optional[List[Dict[str, Any]]]
    error_analysis: Optional[Dict[str, Any]]

    # React loop
    react_loop_count: int
    max_react_loop: int
    react_mode: bool

    # Skills
    tech_stack: str
    skill_registry: Any
    available_skills: List[str]

    # Context
    project_context: Optional[str]
    agents_md: Optional[str]
    project_config: Optional[Dict[str, Any]]
    related_code_context: Optional[str]

    # Review
    review_result: Optional[str]
    review_feedback: Optional[str]
    review_details: Optional[str]
    review_count: int
    total_lbtm_count: int

    # Summarize
    summary: Optional[str]
    todos: Optional[Dict[str, str]]
    is_pass: Optional[str]
    summarize_feedback: Optional[str]
    summarize_count: int
    files_reviewed: Optional[str]
    story_summary: Optional[str]
