"""Tester State Schema."""

from typing import TypedDict, Any, Literal

Action = Literal["PLAN_TESTS", "TEST_STATUS", "CONVERSATION"]


class TesterState(TypedDict, total=False):
    """State for Tester LangGraph."""
    
    # Input
    user_message: str
    user_id: str
    project_id: str
    task_id: str
    task_type: str  # AgentTaskType value
    story_ids: list[str]
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
    
    # CocoIndex context
    related_code: dict           # {story_id: "related code markdown"}
    test_examples: str           # Existing test examples from project
    testing_context: dict        # Auth library, ORM, existing mocks, ESM warnings
    index_ready: bool            # Whether CocoIndex is available
    
    # ==========================================================================
    # Skills system (aligned with Developer V2)
    # ==========================================================================
    skill_registry: Any          # SkillRegistry instance
    available_skills: list[str]  # List of available skill IDs
    
    # Processing
    stories: list[dict]
    test_scenarios: list[dict]
    
    # Plan phase
    test_plan: list[dict]  # [{type, story_id, file_path, scenarios, ...}]
    total_steps: int
    current_step: int
    
    # Implement phase
    files_created: list[str]
    files_modified: list[str]
    
    # Run phase
    run_status: str  # "PASS" | "FAIL" | "ERROR"
    run_result: dict
    run_stdout: str
    run_stderr: str
    
    # Debug loop
    debug_count: int
    max_debug: int  # default 3
    error_analysis: str
    debug_history: list[str]
    
    # Legacy (kept for compatibility)
    test_cases: dict  # {"integration_tests": [...]}
    result: dict  # {"integration": {...}}
    test_execution: dict
    
    # Output
    message: str
    error: str | None
