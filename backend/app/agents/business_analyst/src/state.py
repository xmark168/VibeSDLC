"""LangGraph State Schema for Business Analyst"""

from typing import TypedDict, Literal, Annotated
from operator import add


class BAState(TypedDict, total=False):
    """Business Analyst workflow state
    
    This state is passed through all graph nodes and accumulates information
    as the workflow progresses.
    """
    
    # Input
    user_message: str
    project_path: str
    
    # Context
    collected_info: dict
    existing_prd: dict | None
    agent_name: str
    personality_traits: list[str]
    communication_style: str
    
    # Intent & Routing
    intent: Literal["interview", "prd_create", "prd_update", "extract_stories", "domain_analysis"]
    reasoning: str  # Why this intent was chosen
    
    # Interview workflow
    questions: Annotated[list[dict], add]  # Questions to ask (accumulate with add operator)
    questions_sent: bool
    
    # PRD workflow
    prd_draft: dict | None
    prd_final: dict | None
    prd_saved: bool
    change_summary: str  # For PRD updates
    
    # Stories workflow
    stories: list[dict]
    stories_saved: bool
    
    # Domain analysis
    analysis_text: str
    
    # Error handling
    error: str | None
    retry_count: int
    
    # Result
    result: dict
    is_complete: bool
