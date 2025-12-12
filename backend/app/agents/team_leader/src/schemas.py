"""Team Leader Pydantic schemas."""

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    """Structured routing decision from LLM."""
    action: Literal["DELEGATE", "RESPOND", "CONVERSATION", "STATUS_CHECK", "CLARIFY", "CONFIRM_REPLACE"] = Field(
        description="DELEGATE=technical work, RESPOND=quick ack, CONVERSATION=chat/questions, STATUS_CHECK=board queries, CLARIFY=need more info, CONFIRM_REPLACE=ask to replace existing project"
    )
    target_role: Optional[Literal["business_analyst", "developer", "tester"]] = Field(
        default=None,
        description="Required for DELEGATE: business_analyst(new features), developer(implement), tester(QA)"
    )
    message: str = Field(
        description="Vietnamese response mentioning @Role when delegating"
    )
    reason: str = Field(description="1-line routing reason")
    clarification_question: Optional[str] = Field(
        default=None,
        description="Question to ask when action=CLARIFY"
    )
    confidence: float = Field(
        default=0.8,
        description="Routing confidence 0.0-1.0"
    )
    is_update_request: bool = Field(
        default=False,
        description="True if user wants to work on EXISTING project (UPDATE/ADD/EDIT/REMOVE - e.g., 'sửa story X', 'thêm feature Y', 'thêm trang about', 'thêm tính năng X', 'bổ sung Y', 'cần thêm Z', 'bỏ requirement W'). False ONLY for completely NEW project request when NO project exists or DIFFERENT domain (e.g., 'tôi muốn làm website bán hàng' as first request, or switching from 'website bán sách' to 'app quản lý công việc')."
    )


class ExtractedPreferences(BaseModel):
    """User preferences schema with typed + dynamic fields."""
    preferred_language: Optional[Literal["vi", "en"]] = None
    emoji_usage: Optional[bool] = None
    expertise_level: Optional[Literal["beginner", "intermediate", "expert"]] = None
    response_length: Optional[Literal["concise", "detailed"]] = None
    tech_stack: Optional[List[str]] = None
    communication_style: Optional[Literal["formal", "casual"]] = None
    additional: Optional[Dict[str, Any]] = Field(default=None, description="Other detected preferences")
