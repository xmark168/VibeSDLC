"""Team Leader State."""

from typing import TypedDict, Literal, Any

Action = Literal["DELEGATE", "RESPOND", "CONVERSATION", "STATUS_CHECK"]


class TeamLeaderState(TypedDict, total=False):
    # Input
    user_message: str
    user_id: str
    project_id: str
    task_id: str
    conversation_history: str
    user_preferences: str
    langfuse_handler: Any
    # Output
    action: Action
    target_role: str
    message: str
    reason: str
    confidence: float
    wip_blocked: bool
