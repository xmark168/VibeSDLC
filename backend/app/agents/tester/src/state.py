"""Tester State Schema."""

from typing import TypedDict, Any, Literal

Action = Literal["GENERATE_TESTS", "TEST_STATUS", "CONVERSATION"]


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
    
    # Processing
    stories: list[dict]
    test_scenarios: list[dict]
    
    # Test cases - split by type
    test_cases: dict  # {"integration_tests": [...], "unit_tests": [...]}
    
    # Results - split by type
    result: dict  # {"integration": {...}, "unit": {...}}
    test_execution: dict  # {"integration": {...}, "unit": {...}}
    
    # Output
    message: str
    error: str | None
