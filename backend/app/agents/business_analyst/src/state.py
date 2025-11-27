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
    project_id: str
    task_id: str
    user_id: str
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
    
    # Interview workflow - Sequential questions
    questions: list[dict]  # All questions to ask
    current_question_index: int  # Current question being asked (0-based)
    collected_answers: list[dict]  # Answers collected so far
    waiting_for_answer: bool  # True if waiting for user to answer
    all_questions_answered: bool  # True when all questions have been answered
    
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
