"""Team Leader State Schema."""

from typing import TypedDict, Literal, Any

Action = Literal["DELEGATE", "RESPOND", "CONVERSATION", "STATUS_CHECK"]


class TeamLeaderState(TypedDict, total=False):
    """State for Team Leader graph."""
    
    # Input (required)
    user_message: str
    user_id: str
    project_id: str
    task_id: str
    
    # Input (optional)
    conversation_history: str
    user_preferences: str
    langfuse_handler: Any
    
    # Output
    action: Action
    target_role: str  # developer, tester, business_analyst
    message: str
    reason: str
    confidence: float
    wip_blocked: bool
