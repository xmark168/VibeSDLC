"""Pydantic schemas for Team Leader agent."""

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field


class ExtractedPreferences(BaseModel):
    """Hybrid schema: core typed fields + dynamic dict for flexibility.
    
    Used by extract_preferences node for structured LLM output.
    """
    
    # === CORE PREFERENCES (strongly typed) ===
    preferred_language: Optional[Literal["vi", "en"]] = Field(
        default=None, 
        description="User's preferred language: 'vi' for Vietnamese, 'en' for English"
    )
    emoji_usage: Optional[bool] = Field(
        default=None,
        description="Whether user wants emojis in responses"
    )
    expertise_level: Optional[Literal["beginner", "intermediate", "expert"]] = Field(
        default=None,
        description="User's technical expertise level"
    )
    response_length: Optional[Literal["concise", "detailed"]] = Field(
        default=None,
        description="Preferred response length"
    )
    tech_stack: Optional[List[str]] = Field(
        default=None,
        description="Technologies/frameworks mentioned by user"
    )
    communication_style: Optional[Literal["formal", "casual"]] = Field(
        default=None,
        description="Preferred communication tone"
    )
    
    # === DYNAMIC PREFERENCES (flexible) ===
    additional: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Any other preferences detected: timezone, domain_context, custom_instructions, working_hours, notification_preference, etc."
    )
