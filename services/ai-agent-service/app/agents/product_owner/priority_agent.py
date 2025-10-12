"""Priority Agent - Tạo Sprint Plan từ Product Backlog."""

import json
import os
import re
from typing import Any, Literal, Optional
from datetime import datetime, timedelta

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field


load_dotenv()


# ============================================================================
# Pydantic Models for State Management
# ============================================================================

class Sprint(BaseModel):
    """Model cho một Sprint."""
    sprint_id: str = Field(description="ID: sprint-1, sprint-2, ...")
    sprint_number: int = Field(description="Số thứ tự sprint (1, 2, 3, ...)")
    sprint_goal: str = Field(description="Mục tiêu chính của sprint")
    start_date: Optional[str] = Field(default=None, description="Ngày bắt đầu (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="Ngày kết thúc (YYYY-MM-DD)")
    velocity_plan: int = Field(default=0, description="Planned velocity (story points)")
    velocity_actual: int = Field(default=0, description="Actual velocity (story points)")
    assigned_items: list[str] = Field(default_factory=list, description="IDs của items được assign")
    status: Literal["Planned", "Active", "Completed"] = Field(default="Planned")


class PriorityState(BaseModel):
    """State cho Priority Agent workflow."""
    # Input
    product_backlog: dict = Field(
        default_factory=dict,
        description="Product Backlog từ Backlog Agent (metadata + items)"
    )

    # Configuration
    sprint_duration_weeks: int = Field(
        default=2,
        description="Độ dài mỗi sprint (tuần) - sprint cycle for review/demo"
    )
    sprint_capacity_story_points: int = Field(
        default=30,
        description="Max story points per sprint (AI throughput limit for review process)"
    )

    # Calculate Priority Outputs
    prioritized_backlog: list[dict] = Field(
        default_factory=list,
        description="Backlog items đã được prioritize (có rank field)"
    )
    wsjf_calculations: dict = Field(
        default_factory=dict,
        description="WSJF calculations cho từng item {item_id: wsjf_data}"
    )

    # ========================================================================
    # Plan Sprints Outputs
    # ========================================================================
    sprints: list[dict] = Field(
        default_factory=list,
        description="Danh sách sprints với assigned items"
    )

    # ========================================================================
    # Evaluate Outputs
    # ========================================================================
    capacity_issues: list[dict] = Field(
        default_factory=list,
        description="Issues về capacity (overload, underload)"
    )
    dependency_issues: list[dict] = Field(
        default_factory=list,
        description="Issues về dependencies (sprint order conflicts)"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations để cải thiện sprint plan"
    )
    readiness_score: float = Field(
        default=0.0,
        description="Điểm readiness của sprint plan (0.0-1.0)"
    )
    can_proceed: bool = Field(
        default=False,
        description="Sprint plan có đạt yêu cầu để finalize không"
    )

    # Loop Control
    max_loops: int = Field(
        default=1,
        description="Số lần refine tối đa"
    )
    current_loop: int = Field(
        default=0,
        description="Số lần refine hiện tại"
    )

    # ========================================================================
    # Preview & User Approval
    # ========================================================================
    user_approval: Optional[str] = Field(
        default=None,
        description="User choice: 'approve', 'edit', hoặc 'reprioritize'"
    )
    user_feedback: Optional[str] = Field(
        default=None,
        description="Lý do/yêu cầu chỉnh sửa từ user"
    )

    # Final Output
    sprint_plan: dict = Field(
        default_factory=dict,
        description="Final sprint plan (metadata + prioritized_backlog + sprints)"
    )
    status: str = Field(
        default="initial",
        description="Trạng thái workflow"
    )


# ============================================================================
# Priority Agent Class
# ============================================================================

class PriorityAgent:
    """Priority Agent - Tạo Sprint Plan từ Product Backlog.

    Workflow:
    1. initialize: Load product backlog từ Backlog Agent
    2. calculate_priority: Tính WSJF scores và rank items
    3. plan_sprints: Pack items vào sprints với capacity planning
    4. evaluate: Validate sprint plan
    5. refine (if needed): Adjust sprint assignments
    6. finalize: Finalize sprint plan
    7. preview: Human-in-the-loop approval
    """

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        """Khởi tạo Priority Agent.

        Args:
            session_id: Session ID tùy chọn
            user_id: User ID tùy chọn
        """
        self.session_id = session_id
        self.user_id = user_id

        # Initialize Langfuse callback handler
        self.langfuse_handler = CallbackHandler()

        self.graph = self._build_graph()

    def _llm(self, model: str, temperature: float) -> ChatOpenAI:
        """Initialize LLM instance."""
        try:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
            return llm
        except Exception:
            return None

    def _build_graph(self) -> StateGraph:
        """Xây dựng LangGraph workflow theo sơ đồ Priority Agent."""
        graph_builder = StateGraph(PriorityState)

        # Add nodes
        graph_builder.add_node("initialize", self.initialize)
        graph_builder.add_node("calculate_priority", self.calculate_priority)
        graph_builder.add_node("plan_sprints", self.plan_sprints)
        graph_builder.add_node("evaluate", self.evaluate)
        graph_builder.add_node("refine", self.refine)
        graph_builder.add_node("finalize", self.finalize)
        graph_builder.add_node("preview", self.preview)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        # graph_builder.add_edge("initialize", "calculate_priority")
        # graph_builder.add_edge("calculate_priority", "plan_sprints")
        # graph_builder.add_edge("plan_sprints", "evaluate")
        # graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        # graph_builder.add_edge("refine", "plan_sprints")  # refine → plan_sprints
        # graph_builder.add_edge("finalize", "preview")
        # graph_builder.add_conditional_edges("preview", self.preview_branch)

        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    # ========================================================================
    # Nodes (to be implemented)
    # ========================================================================

    def initialize(self, state: PriorityState) -> PriorityState:
        """Initialize - Load và validate product backlog."""
        # TODO: Implement
        return state

    def calculate_priority(self, state: PriorityState) -> PriorityState:
        """Calculate Priority - Tính WSJF và rank items."""
        # TODO: Implement
        return state

    def plan_sprints(self, state: PriorityState) -> PriorityState:
        """Plan Sprints - Pack items vào sprints với capacity planning."""
        # TODO: Implement
        return state

    def evaluate(self, state: PriorityState) -> PriorityState:
        """Evaluate - Validate sprint plan."""
        # TODO: Implement
        return state

    def refine(self, state: PriorityState) -> PriorityState:
        """Refine - Adjust sprint assignments."""
        # TODO: Implement
        return state

    def finalize(self, state: PriorityState) -> PriorityState:
        """Finalize - Finalize sprint plan."""
        # TODO: Implement
        return state

    def preview(self, state: PriorityState) -> PriorityState:
        """Preview - Human-in-the-loop approval."""
        # TODO: Implement
        return state

    # ========================================================================
    # Branch Functions
    # ========================================================================

    def evaluate_branch(self, state: PriorityState) -> str:
        """Branch sau evaluate node.

        Logic:
        - score >= 0.8 AND loops < max_loops → finalize
        - score < 0.8 OR loops >= max_loops → refine
        """
        if state.readiness_score >= 0.8 and state.current_loop < state.max_loops:
            return "finalize"
        else:
            return "refine"

    def preview_branch(self, state: PriorityState) -> str:
        """Branch sau preview node.

        Logic:
        - user_approval == 'approve' → END
        - user_approval == 'edit' → plan_sprints
        - user_approval == 'reprioritize' → calculate_priority
        """
        if state.user_approval == "approve":
            return END
        elif state.user_approval == "reprioritize":
            return "calculate_priority"
        else:  # edit
            return "plan_sprints"

    # ========================================================================
    # Run Method
    # ========================================================================

    def run(self, product_backlog: dict, thread_id: str | None = None) -> dict[str, Any]:
        """Chạy Priority Agent workflow.

        Args:
            product_backlog: Product Backlog từ Backlog Agent
            thread_id: Thread ID cho checkpointer

        Returns:
            dict: Final state với sprint_plan
        """
        if thread_id is None:
            thread_id = self.session_id or "default_priority_thread"

        initial_state = PriorityState(product_backlog=product_backlog)

        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [self.langfuse_handler],
            "recursion_limit": 50
        }

        final_state = None
        for output in self.graph.stream(
            initial_state.model_dump(),
            config=config,
        ):
            final_state = output

        return final_state or {}
