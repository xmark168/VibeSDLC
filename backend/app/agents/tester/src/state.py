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
    
    # CocoIndex context
    related_code: dict  # {story_id: "related code markdown"}
    project_context: str  # Project structure, AGENTS.md, etc.
    test_examples: str  # Existing test examples from project
    testing_context: dict  # Auth library, ORM, existing mocks, ESM warnings
    index_ready: bool  # Whether CocoIndex is available
    
    # Processing
    stories: list[dict]
    test_scenarios: list[dict]
    
    # Test cases - integration tests only
    test_cases: dict  # {"integration_tests": [...]}
    
    # Results - integration tests only
    result: dict  # {"integration": {...}}
    test_execution: dict
    
    # Output
    message: str
    error: str | None
