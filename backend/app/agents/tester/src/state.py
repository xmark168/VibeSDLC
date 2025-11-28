"""Tester State Schema."""

from typing import TypedDict, Any


class TesterState(TypedDict, total=False):
    """State for Tester LangGraph."""
    
    # Input (required)
    project_id: str
    story_ids: list[str]
    project_path: str
    tech_stack: str
    timestamp: str
    
    # Input (optional)
    user_message: str  # For manual @Tester requests
    langfuse_handler: Any
    
    # Processing state
    stories: list[dict]
    test_scenarios: list[dict]
    test_cases: list[dict]
    test_content: str
    
    # Output
    result: dict
    error: str | None
