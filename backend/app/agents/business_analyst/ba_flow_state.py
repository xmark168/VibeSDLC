"""State model for Business Analyst Flow."""

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Dict, List, Optional


class BAFlowState(BaseModel):
    """State for BA Flow - tracked automatically by CrewAI.
    
    This state is maintained throughout the flow execution and provides
    type-safe access to all workflow data.
    """
    
    # User context
    user_id: UUID
    user_message: str = ""
    
    # Intent & routing (determined by orchestrator)
    intent: str = "unknown"  # create_feature, edit_prd, edit_story, generate_stories, general_discussion
    action: str = ""  # ASK_CLARIFICATION, ANALYZE_DOMAIN, GENERATE_PRD, UPDATE_PRD, EXTRACT_STORIES, UPDATE_STORY, ERROR
    agent_to_use: str = ""  # requirements_engineer, domain_expert, prd_specialist, story_writer, none
    
    # Interview state
    questions_asked: List[dict] = Field(default_factory=list)
    questions_answered: List[dict] = Field(default_factory=list)
    collected_info: Dict = Field(default_factory=dict)
    
    # Artifacts
    existing_prd: Optional[Dict] = None
    has_stories: bool = False
    
    # Phase tracking
    phase: str = "initial"  # initial, interview, analysis_complete, prd_complete, complete
    is_complete: bool = False
    
    # Error handling
    error_message: Optional[str] = None
