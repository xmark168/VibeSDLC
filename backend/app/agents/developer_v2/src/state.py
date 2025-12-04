"""Developer V2 State Definition (Optimized)."""

from typing import TypedDict, Literal, Any, List, Optional, Dict


Action = Literal["ANALYZE", "PLAN", "IMPLEMENT", "RESPOND"]
TaskType = Literal["feature", "bugfix", "refactor", "enhancement", "documentation", "bug_fix"]
Complexity = Literal["low", "medium", "high"]


class DeveloperState(TypedDict, total=False):
    # ==========================================================================
    # Input (from story event)
    # ==========================================================================
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
    
    # ==========================================================================
    # Router/Flow control
    # ==========================================================================
    action: Action
    task_type: TaskType
    complexity: Complexity
    use_code_review: bool  # MetaGPT-style: Enable/disable code review step (default True)
    
    # ==========================================================================
    # Analysis results
    # ==========================================================================
    analysis_result: dict
    affected_files: List[str]
    dependencies: List[str]
    risks: List[str]
    estimated_hours: float
    
    # ==========================================================================
    # Planning (MetaGPT-style detailed planning)
    # ==========================================================================
    implementation_plan: List[dict]
    current_step: int
    total_steps: int
    
    # Logic analysis - MetaGPT style: [["file.ts", "Component X, function Y"]]
    logic_analysis: List[List[str]]
    
    # Pre-loaded dependency contents (reduce tool calls during implement)
    # Format: {"path/to/file.ts": "file content..."}
    dependencies_content: Dict[str, str]
    
    # ==========================================================================
    # Implementation results
    # ==========================================================================
    files_created: List[str]
    files_modified: List[str]
    
    # ==========================================================================
    # Workspace context
    # ==========================================================================
    workspace_path: str
    branch_name: str
    main_workspace: str
    workspace_ready: bool
    index_ready: bool
    merged: bool
    
    # ==========================================================================
    # Output
    # ==========================================================================
    message: str
    error: Optional[str]
    
    # ==========================================================================
    # Run code (tests/lint)
    # ==========================================================================
    run_result: Optional[Dict[str, Any]]
    run_stdout: Optional[str]
    run_stderr: Optional[str]
    run_status: Optional[str]
    test_command: Optional[List[str]]
    
    # ==========================================================================
    # Debug/Error handling
    # ==========================================================================
    debug_count: int
    max_debug: int
    debug_history: Optional[List[Dict[str, Any]]]
    error_analysis: Optional[Dict[str, Any]]
    
    # ==========================================================================
    # React loop mode
    # ==========================================================================
    react_loop_count: int
    max_react_loop: int
    react_mode: bool
    
    # ==========================================================================
    # Skills system
    # ==========================================================================
    tech_stack: str
    skill_registry: Any
    available_skills: List[str]
    
    # ==========================================================================
    # Context
    # ==========================================================================
    project_context: Optional[str]
    agents_md: Optional[str]
    project_config: Optional[Dict[str, Any]]
    related_code_context: Optional[str]
    
    # ==========================================================================
    # Review (MetaGPT-style LGTM/LBTM)
    # ==========================================================================
    review_result: Optional[str]  # "LGTM" or "LBTM"
    review_feedback: Optional[str]  # Feedback if LBTM
    review_details: Optional[str]  # Full review details
    review_count: int  # Count of reviews for current step
    total_lbtm_count: int  # Track total LBTM across all steps (for skip summarize optimization)
    
    # ==========================================================================
    # Summarize (MetaGPT-style IS_PASS gate)
    # ==========================================================================
    summary: Optional[str]  # Summary of implementation
    todos: Optional[Dict[str, str]]  # {file: issue} if any
    is_pass: Optional[str]  # "YES" or "NO"
    summarize_feedback: Optional[str]  # Feedback if NO
    summarize_count: int  # Count of summarize retries
    files_reviewed: Optional[str]  # List of files reviewed
    story_summary: Optional[str]  # Summary of the story for context
