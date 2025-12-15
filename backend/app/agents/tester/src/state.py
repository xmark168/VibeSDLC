"""Tester State Schema with checkpoint/interrupt support for pause/resume."""

from typing import TypedDict, Any, Literal, Dict, Optional, List

Action = Literal["PLAN_TESTS", "TEST_STATUS", "CONVERSATION"]


class TesterState(TypedDict, total=False):
    """State for Tester LangGraph with checkpoint/interrupt support."""
    
    # Input
    user_message: str
    user_id: str
    project_id: str
    task_id: str
    story_id: str  # Primary story ID for checkpoint (aligned with dev_v2)
    story_code: str  # Story code for branch naming
    task_type: str
    story_ids: List[str]
    is_auto: bool
    action: Action
    
    # Checkpoint/Interrupt
    checkpoint_thread_id: str
    is_resume: bool
    base_branch: str
    
    # Workspace
    workspace_path: str
    branch_name: str
    workspace_ready: bool
    merged: bool
    project_path: str
    tech_stack: str
    timestamp: str
    
    # Project context
    project_context: str
    agents_md: str
    related_code: Dict
    test_examples: str
    testing_context: Dict
    
    # Pre-loaded dependencies
    dependencies_content: Dict[str, str]
    component_context: str
    
    # Skills
    skill_registry: Any
    available_skills: List[str]
    
    # Processing
    stories: List[Dict]
    test_scenarios: List[Dict]
    
    # Plan
    test_plan: List[Dict]
    total_steps: int
    current_step: int
    
    # Implement
    files_created: List[str]
    files_modified: List[str]
    
    # Review
    review_result: Optional[str]
    review_feedback: Optional[str]
    review_details: Optional[str]
    review_count: int
    total_lbtm_count: int
    step_lbtm_counts: Dict[str, int]
    review_results: List[Dict]
    failed_files: List[str]
    file_lbtm_counts: Dict[str, int]
    implementation_results: List[Dict]
    
    # Summarize
    summary: Optional[str]
    todos: Optional[Dict[str, str]]
    is_pass: Optional[str]
    summarize_feedback: Optional[str]
    summarize_count: int
    files_reviewed: Optional[str]
    
    # Run
    run_status: str
    run_result: Dict
    run_stdout: str
    run_stderr: str
    
    debug_count: int
    max_debug: int
    error_analysis: str
    debug_history: List[str]
    
    # Legacy
    test_cases: Dict
    result: Dict
    test_execution: Dict
    
    # Output
    message: str
    error: Optional[str]
    
    # Git
    git_committed: bool
    git_commit_hash: str
