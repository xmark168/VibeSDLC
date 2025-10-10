import json
import os
import re
from typing import Any, Literal, Optional
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from langgraph.checkpoint.memory import MemorySaver

from templates.prompts.product_owner.backlog import (
    GENERATE_PROMPT,
    EVALUATE_PROMPT,
    REFINE_PROMPT,
    FINALIZE_PROMPT,
)

load_dotenv()


# ============================================================================
# Pydantic Models for Backlog Items
# ============================================================================

class BacklogItem(BaseModel):
    """Model cho một backlog item (Epic, User Story, Task, Sub-task)."""

    id: str = Field(description="ID duy nhất, ví dụ: 'EPIC-001', 'US-001', 'TASK-001'")
    type: Literal["Epic", "User Story", "Task", "Sub-task"] = Field(description="Loại backlog item")
    parent_id: Optional[str] = Field(default=None, description="ID của item cha (null nếu root level)")
    title: str = Field(description="Tiêu đề của item")
    description: str = Field(description="Mô tả chi tiết")

    # Priority & Status
    priority: Literal["High", "Medium", "Low"] = Field(default="Medium", description="Mức độ ưu tiên (sẽ được Priority Agent set)")
    status: Literal["Backlog", "Todo", "In Progress", "Done"] = Field(default="Backlog", description="Trạng thái hiện tại")

    # Estimation
    story_points: Optional[int] = Field(default=None, description="Story points (chỉ cho User Story), Fibonacci: 1,2,3,5,8,13,21")
    estimated_hours: Optional[float] = Field(default=None, description="Số giờ ước lượng (cho Task/Sub-task)")
    actual_hours: Optional[float] = Field(default=None, description="Số giờ thực tế")

    # Requirements & Criteria
    acceptance_criteria: list[str] = Field(default_factory=list, description="Tiêu chí chấp nhận")
    functional_requirements: list[str] = Field(default_factory=list, description="Yêu cầu chức năng (WHAT, không HOW)")
    non_functional_requirements: list[str] = Field(default_factory=list, description="Yêu cầu phi chức năng (performance, security, usability)")
    constraints: list[str] = Field(default_factory=list, description="Ràng buộc business/legal/compliance")

    # Assignment & Dependencies
    assigned_to: Optional[str] = Field(default=None, description="Người được assign")
    dependencies: list[str] = Field(default_factory=list, description="Danh sách item IDs phụ thuộc")
    labels: list[str] = Field(default_factory=list, description="Labels theo business domain (KHÔNG tech stack)")

    # Task-specific
    task_type: Optional[Literal["Feature Development", "Bug Fix", "Testing", "UX Design", "Content", "Research", "Documentation", "Performance", "Security", "Accessibility"]] = Field(
        default=None, description="Loại task (chỉ cho type='Task')"
    )
    severity: Optional[Literal["Blocker", "Critical", "Major", "Minor", "Trivial"]] = Field(
        default=None, description="Mức độ nghiêm trọng (cho Bug Fix)"
    )

    # Business Value
    business_value: Optional[str] = Field(default=None, description="Giá trị kinh doanh (cho Epic/User Story)")

    # Metadata
    notes: Optional[str] = Field(default=None, description="Ghi chú chung")
    created_at: Optional[str] = Field(default=None, description="Thời điểm tạo ISO 8601")
    updated_at: Optional[str] = Field(default=None, description="Thời điểm cập nhật ISO 8601")

    # Sprint & Order (sẽ được set bởi Priority/Sprint Planning Agent)
    sprint: Optional[str] = Field(default=None, description="Sprint được assign (sẽ set sau)")
    order: int = Field(default=999, description="Thứ tự ưu tiên (sẽ được Priority Agent set)")


class BacklogMetadata(BaseModel):
    """Metadata cho Product Backlog."""

    product_name: str = Field(description="Tên sản phẩm")
    version: str = Field(description="Phiên bản backlog, ví dụ: 'v1.0'")
    created_at: str = Field(description="Thời điểm tạo ISO 8601")
    last_updated: Optional[str] = Field(default=None, description="Thời điểm cập nhật lần cuối")
    total_items: int = Field(default=0, description="Tổng số backlog items")
    total_story_points: float = Field(default=0, description="Tổng story points")
    total_estimated_hours: float = Field(default=0, description="Tổng số giờ ước lượng")


class ProductBacklog(BaseModel):
    """Model cho toàn bộ Product Backlog."""

    metadata: BacklogMetadata = Field(description="Metadata về backlog")
    items: list[BacklogItem] = Field(default_factory=list, description="Danh sách tất cả backlog items")
    backlog_notes: Optional[str] = Field(default=None, description="Ghi chú chung về backlog")
    definition_of_ready: list[str] = Field(default_factory=list, description="Tiêu chí để item Ready cho Sprint")
    definition_of_done: list[str] = Field(default_factory=list, description="Tiêu chí để item Done")


# ============================================================================
# State for Backlog Agent
# ============================================================================

class BacklogState(BaseModel):
    """State cho Backlog Agent workflow - FULLY AUTOMATED (no user interaction)."""

    # Input
    product_vision: dict = Field(default_factory=dict, description="Product Vision từ Vision Agent (input)")

    # Product Backlog Items (working state)
    backlog_items: list[BacklogItem] = Field(default_factory=list, description="Danh sách tất cả backlog items (flat list)")

    # Counters cho ID generation
    epic_counter: int = 0
    user_story_counter: int = 0
    task_counter: int = 0
    subtask_counter: int = 0

    # Dependency tracking
    dependency_map: dict = Field(default_factory=dict, description="Map dependencies giữa các items")

    # Evaluation & Refinement (max_loops=2)
    current_loop: int = 0
    max_loops: int = 2
    readiness_score: float = Field(default=0.0, description="Điểm đánh giá độ sẵn sàng backlog (0.0-1.0)")
    evaluation_notes: str = Field(default="", description="Ghi chú từ evaluate node")

    # Flags for evaluate branch
    needs_split: list[str] = Field(default_factory=list, description="Danh sách item IDs cần split (từ INVEST check)")
    not_testable: list[str] = Field(default_factory=list, description="Danh sách item IDs chưa testable")
    weak_ac: list[str] = Field(default_factory=list, description="Danh sách item IDs có acceptance criteria yếu")
    missing_cases: list[str] = Field(default_factory=list, description="Danh sách item IDs thiếu edge cases")

    # Output (final)
    product_backlog: Optional[ProductBacklog] = Field(default=None, description="Product Backlog cuối cùng (output)")

    # Workflow status
    status: str = Field(default="initial", description="Trạng thái: initial, generating, evaluating, refining, finalizing, completed")


# ============================================================================
# Structured Output Models for LLM
# ============================================================================

class GenerateOutput(BaseModel):
    """Structured output từ generate node."""
    items: list[BacklogItem] = Field(description="Danh sách backlog items đã tạo")
    dependency_map: dict = Field(description="Map dependencies giữa các items")
    generation_notes: str = Field(description="Ghi chú về quá trình generate")


class EvaluateOutput(BaseModel):
    """Structured output từ evaluate node."""
    readiness_score: float = Field(description="Điểm đánh giá backlog (0.0-1.0)", ge=0.0, le=1.0)
    needs_split: list[str] = Field(description="Item IDs cần split (story_points > 13)")
    not_testable: list[str] = Field(description="Item IDs chưa testable")
    weak_ac: list[str] = Field(description="Item IDs có AC yếu")
    missing_cases: list[str] = Field(description="Item IDs thiếu edge cases")
    evaluation_notes: str = Field(description="Nhận xét chi tiết")


class RefineOutput(BaseModel):
    """Structured output từ refine node."""
    items: list[BacklogItem] = Field(description="Danh sách backlog items đã refine")
    refinement_notes: str = Field(description="Ghi chú về các thay đổi")


class FinalizeOutput(BaseModel):
    """Structured output từ finalize node."""
    metadata: BacklogMetadata = Field(description="Metadata backlog")
    items: list[BacklogItem] = Field(description="Danh sách items final")
    definition_of_ready: list[str] = Field(description="Definition of Ready")
    definition_of_done: list[str] = Field(description="Definition of Done")
    backlog_notes: str = Field(description="Ghi chú tổng quan")


# ============================================================================
# Backlog Agent Class
# ============================================================================

class BacklogAgent:
    """Backlog Agent - Tạo Product Backlog từ Product Vision (fully automated)."""

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        """Khởi tạo backlog agent.

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
        """Xây dựng LangGraph workflow."""
        graph_builder = StateGraph(BacklogState)

        # Add nodes
        graph_builder.add_node("initialize", self.initialize)
        graph_builder.add_node("generate", self.generate)
        graph_builder.add_node("evaluate", self.evaluate)
        graph_builder.add_node("refine", self.refine)
        graph_builder.add_node("finalize", self.finalize)

        # Add edges
        graph_builder.add_edge(START, "initialize")
        # graph_builder.add_edge("initialize", "generate")
        # graph_builder.add_edge("generate", "evaluate")
        # graph_builder.add_conditional_edges("evaluate", self.evaluate_branch)
        # graph_builder.add_edge("refine", "generate")  # Loop back
        # graph_builder.add_edge("finalize", END)

        checkpointer = MemorySaver()
        return graph_builder.compile(checkpointer=checkpointer)

    # ========================================================================
    # Node: Initialize
    # ========================================================================

    def initialize(self, state: BacklogState) -> BacklogState:
        """Initialize - Load Product Vision và chuẩn bị working state.

        Theo sơ đồ:
        - Load product_vision / product_goal
        - Set max_loops = 2
        - Init working memory + dependency map
        """
        print("\n" + "="*80)
        print("🚀 INITIALIZE - KHỞI TẠO BACKLOG AGENT")
        print("="*80)

        # Validate product_vision
        if not state.product_vision or len(state.product_vision) == 0:
            print("❌ Product Vision is empty!")
            state.status = "error_no_vision"
            return state

        print(f"✓ Loaded Product Vision")
        print(f"  - Product Name: {state.product_vision.get('product_name', 'N/A')}")

        # Check required fields in product_vision
        required_fields = ["draft_vision_statement", "functional_requirements"]
        missing = [f for f in required_fields if f not in state.product_vision]

        if missing:
            print(f"⚠️  Product Vision thiếu fields: {', '.join(missing)}")

        # Set max_loops
        state.max_loops = 2
        state.current_loop = 0

        # Initialize dependency map
        state.dependency_map = {}

        # Initialize counters
        state.epic_counter = 0
        state.user_story_counter = 0
        state.task_counter = 0
        state.subtask_counter = 0

        # Update status
        state.status = "initialized"

        print(f"✓ Initialized")
        print(f"  - max_loops: {state.max_loops}")
        print(f"  - Working memory ready")
        print(f"  - Dependency map ready")
        print("="*80 + "\n")

        return state

    # ========================================================================
    # Node: Generate (to be implemented)
    # ========================================================================

    def generate(self, state: BacklogState) -> BacklogState:
        """Generate backlog items từ Product Vision."""
        # TODO: Implement
        pass

    # ========================================================================
    # Node: Evaluate (to be implemented)
    # ========================================================================

    def evaluate(self, state: BacklogState) -> BacklogState:
        """Evaluate backlog quality."""
        # TODO: Implement
        pass

    # ========================================================================
    # Node: Refine (to be implemented)
    # ========================================================================

    def refine(self, state: BacklogState) -> BacklogState:
        """Refine backlog based on evaluation."""
        # TODO: Implement
        pass

    # ========================================================================
    # Node: Finalize (to be implemented)
    # ========================================================================

    def finalize(self, state: BacklogState) -> BacklogState:
        """Finalize backlog."""
        # TODO: Implement
        pass

    # ========================================================================
    # Conditional Branch
    # ========================================================================

    def evaluate_branch(self, state: BacklogState) -> str:
        """Branch sau evaluate node.

        Logic:
        - score < 0.8 AND loops < max_loops → refine
        - score ≥ 0.8 OR loops ≥ max_loops → finalize
        """
        if state.readiness_score < 0.8 and state.current_loop < state.max_loops:
            return "refine"
        else:
            return "finalize"

    # ========================================================================
    # Run Method
    # ========================================================================

    def run(self, product_vision: dict, thread_id: str | None = None) -> dict[str, Any]:
        """Chạy Backlog Agent workflow.

        Args:
            product_vision: Product Vision từ Vision Agent
            thread_id: Thread ID cho checkpointer

        Returns:
            dict: Final state với product_backlog
        """
        if thread_id is None:
            thread_id = self.session_id or "default_backlog_thread"

        initial_state = BacklogState(product_vision=product_vision)

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

    