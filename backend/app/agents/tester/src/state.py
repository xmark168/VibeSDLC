"""Tester State Schema (aligned with Developer V2)."""

from typing import TypedDict, Any, Literal, Dict, Optional, List

Action = Literal["PLAN_TESTS", "TEST_STATUS", "CONVERSATION"]

# Note: E2E tests removed - only integration tests supported


class TesterState(TypedDict, total=False):
    """State for Tester LangGraph (MetaGPT-style)."""
    
    # ==========================================================================
    # Input
    # ==========================================================================
    user_message: str
    user_id: str
    project_id: str
    task_id: str
    task_type: str  # AgentTaskType value
    story_ids: List[str]
    is_auto: bool  # Auto-triggered (no user message)
    langfuse_handler: Any
    
    # Router output
    action: Action
    
    # ==========================================================================
    # Workspace context (aligned with Developer V2)
    # ==========================================================================
    workspace_path: str          # Path to git worktree for this task
    branch_name: str             # Git branch name (e.g., "test_abc123")
    main_workspace: str          # Path to main git repository
    workspace_ready: bool        # Whether workspace is set up
    merged: bool                 # Whether changes have been merged
    
    # Context (from setup)
    project_path: str
    tech_stack: str
    timestamp: str
    
    # ==========================================================================
    # Project context (aligned with Developer V2)
    # ==========================================================================
    project_context: str         # Project structure, config info
    agents_md: str               # AGENTS.md content (coding guidelines)
    
    # Project context
    related_code: Dict           # {story_id: "related code markdown"}
    test_examples: str           # Existing test examples from project
    testing_context: Dict        # Auth library, ORM, existing mocks, ESM warnings
    
    # ==========================================================================
    # Pre-loaded dependencies (MetaGPT-style - reduces tool calls)
    # ==========================================================================
    dependencies_content: Dict[str, str]  # {file_path: content}
    component_context: str  # Analyzed components for unit tests (props, exports, data-attrs)
    
    # ==========================================================================
    # Skills system (aligned with Developer V2)
    # ==========================================================================
    skill_registry: Any          # SkillRegistry instance
    available_skills: List[str]  # List of available skill IDs
    
    # Processing
    stories: List[Dict]
    test_scenarios: List[Dict]
    
    # ==========================================================================
    # Plan phase
    # ==========================================================================
    test_plan: List[Dict]  # [{type, story_id, file_path, scenarios, ...}]
    total_steps: int
    current_step: int
    
    # ==========================================================================
    # Implement phase
    # ==========================================================================
    files_created: List[str]
    files_modified: List[str]
    
    # ==========================================================================
    # Review (MetaGPT-style LGTM/LBTM)
    # ==========================================================================
    review_result: Optional[str]      # "LGTM" or "LBTM"
    review_feedback: Optional[str]    # Feedback if LBTM
    review_details: Optional[str]     # Full review details
    review_count: int                 # Count of reviews for current step
    total_lbtm_count: int             # Track total LBTM across all steps
    step_lbtm_counts: Dict[str, int]  # Per-step LBTM tracking {"0": 2, "1": 1}
    
    # ==========================================================================
    # Summarize (MetaGPT-style IS_PASS gate)
    # ==========================================================================
    summary: Optional[str]            # Summary of tests
    todos: Optional[Dict[str, str]]   # {file: issue} if any
    is_pass: Optional[str]            # "YES" or "NO"
    summarize_feedback: Optional[str] # Feedback if NO
    summarize_count: int              # Count of summarize retries
    files_reviewed: Optional[str]     # List of files reviewed
    
    # ==========================================================================
    # Run phase
    # ==========================================================================
    run_status: str  # "PASS" | "FAIL" | "ERROR"
    run_result: Dict
    run_stdout: str
    run_stderr: str
    
    # ==========================================================================
    # Debug loop
    # ==========================================================================
    debug_count: int
    max_debug: int  # default 3
    error_analysis: str
    debug_history: List[str]
    
    # ==========================================================================
    # Legacy (kept for compatibility)
    # ==========================================================================
    test_cases: Dict  # {"integration_tests": [...]}
    result: Dict  # {"integration": {...}}
    test_execution: Dict
    
    # ==========================================================================
    # Output
    # ==========================================================================
    message: str
    error: Optional[str]
