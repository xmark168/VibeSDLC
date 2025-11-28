"""Team Leader Pydantic schemas."""

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    """Structured routing decision from LLM."""
    action: Literal["DELEGATE", "RESPOND", "CONVERSATION", "STATUS_CHECK"] = Field(
        description="DELEGATE to specialist, RESPOND directly, CONVERSATION for chat, STATUS_CHECK for board"
    )
    target_role: Optional[Literal["business_analyst", "developer", "tester"]] = Field(
        default=None, description="Target role (required if DELEGATE)"
    )
    message: str = Field(description="Response message to user")
    reason: str = Field(description="Routing reason for logging")


class ExtractedPreferences(BaseModel):
    """User preferences schema with typed + dynamic fields."""
    preferred_language: Optional[Literal["vi", "en"]] = None
    emoji_usage: Optional[bool] = None
    expertise_level: Optional[Literal["beginner", "intermediate", "expert"]] = None
    response_length: Optional[Literal["concise", "detailed"]] = None
    tech_stack: Optional[List[str]] = None
    communication_style: Optional[Literal["formal", "casual"]] = None
    additional: Optional[Dict[str, Any]] = Field(default=None, description="Other detected preferences")
