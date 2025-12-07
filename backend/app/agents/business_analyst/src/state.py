"""LangGraph State Schema for Business Analyst"""

from typing import TypedDict, Literal, Annotated, Any
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
    has_attachments: bool  # True if user uploaded file(s)
    
    # Context
    collected_info: dict
    existing_prd: dict | None
    agent_name: str
    personality_traits: list[str]
    communication_style: str
    
    # Conversation memory (rolling summary + recent messages)
    conversation_context: str
    
    # Intent & Routing
    intent: Literal["interview", "prd_create", "prd_update", "extract_stories", "domain_analysis", "conversational"]
    reasoning: str  # Why this intent was chosen
    
    # Interview workflow - Sequential questions (legacy)
    questions: list[dict]  # All questions to ask
    current_question_index: int  # Current question being asked (0-based)
    collected_answers: list[dict]  # Answers collected so far
    waiting_for_answer: bool  # True if waiting for user to answer
    all_questions_answered: bool  # True when all questions have been answered
    
    # Interview workflow - Batch mode (preferred)
    batch_id: str | None  # Batch ID for grouped questions
    question_ids: list[str]  # List of question IDs in batch
    batch_answers: list[dict]  # All answers from batch submission
    
    # PRD workflow
    prd_draft: dict | None
    prd_final: dict | None
    prd_saved: bool
    change_summary: str  # For PRD updates
    
    # Stories workflow (Epic/Story hierarchy)
    epics: list[dict]  # List of epics, each containing stories
    stories: list[dict]  # Flat list for backward compatibility
    stories_saved: bool
    stories_approved: bool  # True after user approves stories
    created_epics: list[dict]  # Epics created in DB after approval
    created_stories: list[dict]  # Stories created in DB after approval
    approval_message: str  # Message after approval
    
    # Domain analysis & Research loop
    analysis_text: str
    research_loop_count: int  # Track how many times we've done research (max 2)
    research_done: bool  # Flag to indicate research has been done
    missing_categories: list[str]  # Categories that need more info
    domain_research: dict  # Web search results to enrich PRD
    
    # Error handling
    error: str | None
    retry_count: int
    
    # Langfuse tracing (same pattern as Team Leader)
    langfuse_handler: Any  # CallbackHandler instance passed from agent
    
    # Result
    result: dict
    is_complete: bool
