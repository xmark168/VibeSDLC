"""Developer V2 State Definition."""

from typing import TypedDict, Literal, Any, List, Optional, Dict


Action = Literal["ANALYZE", "DESIGN", "PLAN", "IMPLEMENT", "VALIDATE", "CLARIFY", "RESPOND", "CODE_PLAN", "SUMMARIZE"]
TaskType = Literal["feature", "bugfix", "refactor", "enhancement", "documentation"]
Complexity = Literal["low", "medium", "high"]


class DeveloperState(TypedDict, total=False):
    # Input from story event
    story_id: str
    story_content: str
    story_title: str
    acceptance_criteria: List[str]
    project_id: str
    task_id: str
    user_id: str
    langfuse_handler: Any
    
    # Router output
    action: Action
    task_type: TaskType
    complexity: Complexity
    
    # Analysis results
    analysis_result: dict
    affected_files: List[str]
    dependencies: List[str]
    risks: List[str]
    estimated_hours: float
    
    # Planning results
    implementation_plan: List[dict]
    current_step: int
    total_steps: int
    
    # Implementation results
    code_changes: List[dict]
    files_created: List[str]
    files_modified: List[str]
    
    # Validation results
    validation_result: dict
    tests_passed: bool
    lint_passed: bool
    ac_verified: List[str]
    
    # Workspace context
    workspace_path: str
    branch_name: str
    main_workspace: str
    workspace_ready: bool
    index_ready: bool  # CocoIndex semantic search ready
    merged: bool  # Branch merged to main
    
    # Output
    message: str
    reason: str
    confidence: float
    error: Optional[str]
    
    # ==========================================================================
    # MetaGPT-inspired fields
    # ==========================================================================
    
    # Code Plan & Change document (strategic guidance before coding)
    code_plan_doc: Optional[str]
    development_plan: Optional[List[str]]
    incremental_changes: Optional[List[Dict[str, str]]]
    
    # Related code context for implementation
    related_code_context: Optional[str]
    legacy_code: Optional[str]
    
    # Debug and feedback logs
    error_logs: Optional[str]
    bug_feedback: Optional[str]
    
    # Summarization and validation (IS_PASS check)
    code_summary: Optional[Dict[str, Any]]
    is_pass: Optional[bool]
    needs_revision: bool
    revision_count: int
    max_revisions: int
    
    # ==========================================================================
    # System Design (MetaGPT Architect pattern)
    # ==========================================================================
    system_design: Optional[Dict[str, Any]]  # Full design document
    data_structures: Optional[str]  # Class/interface definitions (mermaid)
    api_interfaces: Optional[str]  # API design
    call_flow: Optional[str]  # Sequence diagram (mermaid)
    design_doc: Optional[str]  # Rendered design doc
    task_doc: Optional[str]
    
    # ==========================================================================
    # Code Review (LGTM/LBTM pattern from MetaGPT)
    # ==========================================================================
    code_review_k: int  # Max review iterations (default: 2)
    code_review_passed: bool
    code_review_results: Optional[List[Dict[str, Any]]]
    code_review_iteration: int
    
    # ==========================================================================
    # Run Code (Execute tests to verify)
    # ==========================================================================
    run_result: Optional[Dict[str, Any]]  # RunCodeResult
    test_command: Optional[List[str]]
    run_stdout: Optional[str]
    run_stderr: Optional[str]
    run_status: Optional[str]  # "PASS" or "FAIL"
    
    # ==========================================================================
    # Debug Error (Fix bugs based on test output)
    # ==========================================================================
    debug_count: int
    max_debug: int  # Max debug attempts (default: 3)
    last_debug_file: Optional[str]
    debug_history: Optional[List[Dict[str, Any]]]
