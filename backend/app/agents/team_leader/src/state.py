"""Team Leader State Schema for LangGraph."""

from typing import TypedDict, Optional, List, Literal, Annotated
from langgraph.graph.message import add_messages


class TeamLeaderState(TypedDict):
    """State for Team Leader graph.
    
    Actions:
    - DELEGATE: Route to specialist agent (developer, tester, business_analyst)
    - RESPOND: Quick response (greetings, acknowledgments)
    - CONVERSATION: Full conversational response with personality + web search
    """
    
    messages: Annotated[List[dict], add_messages]
    user_message: str
    user_id: str
    project_id: str
    task_id: str
    conversation_history: Optional[str]  # Recent conversation for context
    user_preferences: Optional[str]  # Project preferences for personalization
    
    # Routing decision
    action: Optional[Literal["DELEGATE", "RESPOND", "CONVERSATION"]]
    target_role: Optional[str]  # For DELEGATE: developer, tester, business_analyst
    message: Optional[str]
    reason: Optional[str]
    confidence: Optional[float]
