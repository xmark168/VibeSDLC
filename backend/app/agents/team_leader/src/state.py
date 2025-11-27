"""Team Leader State Schema for LangGraph (LLM-only routing)."""

from typing import TypedDict, Optional, List, Literal, Annotated
from langgraph.graph.message import add_messages


class TeamLeaderState(TypedDict):
    """State for Team Leader graph (LLM-only routing)."""
    
    messages: Annotated[List[dict], add_messages]
    user_message: str
    user_id: str
    project_id: str
    task_id: str
    action: Optional[Literal["DELEGATE", "RESPOND"]]
    target_role: Optional[str]
    message: Optional[str]
    reason: Optional[str]
    confidence: Optional[float]
