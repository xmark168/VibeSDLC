"""Team Leader State."""

from typing import TypedDict, Literal, Any

Action = Literal["DELEGATE", "RESPOND", "CONVERSATION", "STATUS_CHECK", "CLARIFY", "CONFIRM_REPLACE", "CONFIRM_EXISTING"]


class TeamLeaderState(TypedDict, total=False):
    # Input
    user_message: str
    user_id: str
    project_id: str
    task_id: str
    conversation_history: str
    user_preferences: str
    langfuse_handler: Any
    attachments: list  # File attachments from user upload
    # Output
    action: Action
    target_role: str
    message: str
    reason: str
    confidence: float
    wip_blocked: bool
    clarification_question: str
    # Project replace confirmation
    existing_prd_title: str
    existing_stories_count: int
    needs_replace_confirm: bool
    waiting_for_answer: bool
