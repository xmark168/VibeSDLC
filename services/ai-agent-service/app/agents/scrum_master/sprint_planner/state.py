"""State models for Sprint Planner Agent."""

from typing import Optional
from pydantic import BaseModel, Field


class SprintPlannerState(BaseModel):
    """State cho Sprint Planner Agent workflow.

    Sprint Planner nhận sprint backlog (các items đã được assigned vào sprint)
    và lập plan chi tiết cho sprint.
    """
    # Input
    sprint_id: str = Field(description="ID của sprint cần plan (vd: sprint-1)")
    sprint_goal: str = Field(description="Mục tiêu của sprint")
    sprint_backlog_items: list[dict] = Field(
        default_factory=list,
        description="Danh sách backlog items đã được assigned vào sprint này"
    )
    sprint_duration_days: int = Field(
        default=14,
        description="Độ dài sprint (ngày), mục tiêu 2 tuần"
    )
    team_capacity: dict = Field(
        default_factory=dict,
        description="Capacity của team: {dev_hours, qa_hours, design_hours, ...}"
    )

    # Generate outputs
    daily_breakdown: list[dict] = Field(
        default_factory=list,
        description="Breakdown tasks theo từng ngày trong sprint"
    )
    resource_allocation: dict = Field(
        default_factory=dict,
        description="Phân bổ resources cho các tasks"
    )
    enriched_tasks: list[dict] = Field(
        default_factory=list,
        description="Tasks với rank, story_point, deadline, status đã được tính"
    )

    # Evaluate outputs
    capacity_issues: list[dict] = Field(
        default_factory=list,
        description="Các vấn đề với capacity (overload, underload)"
    )
    dependency_conflicts: list[dict] = Field(
        default_factory=list,
        description="Các conflicts với dependencies"
    )
    recommendations: list[str] = Field(default_factory=list)
    plan_score: float = Field(
        default=0.0,
        description="Điểm đánh giá plan (0-1)"
    )
    can_proceed: bool = False

    # Loop control
    max_loops: int = 2
    current_loop: int = 0

    # Preview & user approval
    user_approval: Optional[str] = Field(
        default=None,
        description="'approve' hoặc 'edit'"
    )
    user_feedback: Optional[str] = Field(
        default=None,
        description="Feedback to user nếu chọn edit"
    )

    # Final output
    sprint_plan: dict = Field(
        default_factory=dict,
        description="Sprint plan hoàn chỉnh"
    )
    status: str = "initial"
