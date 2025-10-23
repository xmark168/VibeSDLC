"""State models for Sprint Planner Agent."""

from typing import Optional
from pydantic import BaseModel, Field


class SprintPlannerState(BaseModel):
    """State cho Sprint Planner Agent workflow.

    Sprint Planner nhận:
    - Sprint info từ sprint.json (sprint_id, goal, dates, assigned_items)
    - Backlog items từ backlog.json

    Và enrich các items với:
    - rank (thứ tự ưu tiên)
    - estimate_value (effort estimate)
    - story_point (nếu chưa có)
    - acceptance_criteria (list criteria)
    - dependencies (list dependencies)
    - task_type (Development, Testing, Design, etc.)
    - assignments (giao việc cho team members)
    """
    # ==================== INPUT ====================
    # Sprint info
    sprint_id: str = Field(description="ID của sprint (vd: sprint-1)")
    sprint_number: int = Field(default=1, description="Sprint number")
    sprint_goal: str = Field(description="Mục tiêu của sprint")
    start_date: str = Field(description="Ngày bắt đầu sprint (YYYY-MM-DD)")
    end_date: str = Field(description="Ngày kết thúc sprint (YYYY-MM-DD)")
    sprint_duration_days: int = Field(default=14, description="Độ dài sprint (ngày)")
    velocity_plan: int = Field(default=0, description="Velocity plan từ PO")

    # Backlog items (raw from backlog.json, filtered by assigned_items)
    sprint_backlog_items: list[dict] = Field(
        default_factory=list,
        description="Danh sách backlog items đã được assigned vào sprint này (raw)"
    )

    # Team info
    team_capacity: dict = Field(
        default_factory=dict,
        description="Capacity của team: {dev_hours, qa_hours, design_hours, ...}"
    )
    team_members: list[dict] = Field(
        default_factory=list,
        description="Danh sách team members với role và capacity"
    )

    # ==================== ENRICHMENT OUTPUTS ====================
    enriched_items: list[dict] = Field(
        default_factory=list,
        description="Items sau khi enrich với rank, estimate_value, story_point, acceptance_criteria, dependencies, task_type"
    )

    # ==================== ASSIGNMENT OUTPUTS ====================
    task_assignments: list[dict] = Field(
        default_factory=list,
        description="Assignments: [{item_id, assignee, role, estimated_hours}]"
    )

    # ==================== PLANNING OUTPUTS ====================
    daily_breakdown: list[dict] = Field(
        default_factory=list,
        description="Breakdown tasks theo từng ngày trong sprint"
    )
    resource_allocation: dict = Field(
        default_factory=dict,
        description="Phân bổ resources: {dev_hours_allocated, qa_hours_allocated, ...}"
    )

    # ==================== EVALUATION ====================
    capacity_issues: list = Field(
        default_factory=list,
        description="Các vấn đề với capacity (overload, underload)"
    )
    dependency_conflicts: list = Field(
        default_factory=list,
        description="Các conflicts với dependencies"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations để improve plan"
    )
    plan_score: float = Field(
        default=0.0,
        description="Điểm đánh giá plan (0-1)"
    )
    can_proceed: bool = Field(
        default=False,
        description="Có thể proceed với plan này không"
    )

    # ==================== LOOP CONTROL ====================
    max_loops: int = Field(default=1, description="Max số lần refine")
    current_loop: int = Field(default=0, description="Loop hiện tại")

    # ==================== USER APPROVAL ====================
    user_approval: Optional[str] = Field(
        default=None,
        description="'approve' hoặc 'edit'"
    )
    user_feedback: Optional[str] = Field(
        default=None,
        description="Feedback từ user nếu chọn edit"
    )

    # ==================== FINAL OUTPUT ====================
    sprint_plan: dict = Field(
        default_factory=dict,
        description="Sprint plan hoàn chỉnh với enriched items, assignments, daily breakdown"
    )
    status: str = Field(
        default="initial",
        description="Status: initial, enriching, assigning, planning, evaluating, refining, finalized"
    )
