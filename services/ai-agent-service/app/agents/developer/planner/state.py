
from typing import List, Dict, Optional, Any, TypedDict
from pydantic import BaseModel, Field

try:
    from deepagents.state import DeepAgentState
except ImportError:
    # Fallback definition
    class DeepAgentState(TypedDict, total=False):
        messages: List[Any]
        recursion_count: int
        todos: List[Dict[str, Any]]
        files: Dict[str, str]


# Extend DeepAgentState with planner-specific fields
class PlannerAgentState(DeepAgentState):
    """
    State schema for the planner agent.

    Inherits from DeepAgentState which provides:
    - messages: Conversation history
    - recursion_count: Track recursion depth
    - And other DeepAgents standard fields

    Adds planner-specific fields for tracking context and plans.
    """

    # Working environment
    working_directory: Optional[str] = Field(
        default=".",
        description="Working directory for the agent"
    )

    codebase_tree: Optional[str] = Field(
        default="",
        description="Directory structure of the codebase"
    )

    # User request
    user_request: Optional[str] = Field(
        default="",
        description="The original user request"
    )

    # Custom rules
    custom_rules: Optional[Dict[str, Any]] = Field(
        default=None,
        description="User-defined custom rules for the codebase"
    )

    # Plan management
    proposed_plan: List[str] = Field(
        default_factory=list,
        description="List of plan steps generated"
    )

    proposed_plan_title: Optional[str] = Field(
        default="",
        description="Title of the proposed plan"
    )

    # Context gathering
    scratchpad_notes: List[str] = Field(
        default_factory=list,
        description="Notes taken during context gathering"
    )

    context_gathering_notes: Optional[str] = Field(
        default="",
        description="Condensed technical notes from context gathering"
    )

    # Document cache
    document_cache: Dict[str, str] = Field(
        default_factory=dict,
        description="Cache of fetched document contents"
    )

    # Tracking
    action_count: int = Field(
        default=0,
        description="Number of tool actions taken"
    )

    max_context_actions: int = Field(
        default=75,
        description="Maximum number of context gathering actions"
    )

    # Control
    awaiting_user: bool = Field(
        default=False,
        description="Whether agent is waiting for user input"
    )

    auto_accept_plan: bool = Field(
        default=False,
        description="Whether to auto-accept generated plans"
    )

    class Config:
        arbitrary_types_allowed = True


# For backwards compatibility with LangGraph version
PlannerState = PlannerAgentState
