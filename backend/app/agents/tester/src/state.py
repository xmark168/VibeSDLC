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
    
    # Context (from setup)
    project_path: str
    tech_stack: str
    timestamp: str
    
    # CocoIndex context
    related_code: dict  # {story_id: "related code markdown"}
    project_context: str  # Project structure, AGENTS.md, etc.
    test_examples: str  # Existing test examples from project
    testing_context: dict  # Auth library, ORM, existing mocks, ESM warnings
    index_ready: bool  # Whether CocoIndex is available
    
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
