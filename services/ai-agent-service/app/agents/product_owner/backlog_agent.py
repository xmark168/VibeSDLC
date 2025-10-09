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
 
    