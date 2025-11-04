"""State definitions for Sprint Planner Agent."""

from typing import Optional, Any
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """Model cho một validation issue."""
    item_id: str = Field(description="ID của backlog item")
    issue_type: str = Field(
        description="Loại issue: null_field, invalid_priority, duplicate_id, invalid_parent, circular_dependency, etc."
    )
    field_name: Optional[str] = Field(default=None, description="Tên field bị lỗi (nếu có)")
    current_value: Optional[Any] = Field(default=None, description="Giá trị hiện tại (có thể là string, list, dict, etc.)")
    expected_value: Optional[Any] = Field(default=None, description="Giá trị mong đợi (có thể là string, list, dict, etc.)")
    message: str = Field(description="Mô tả chi tiết issue")
    severity: str = Field(
        description="Mức độ nghiêm trọng: critical, high, medium, low",
        default="medium"
    )


class EnrichedItem(BaseModel):
    """Model cho một enriched backlog item."""
    id: str
    type: str
    parent_id: Optional[str] = None
    title: str
    description: str
    rank: Optional[int] = None
    status: str
    story_point: Optional[int] = None
    estimate_value: Optional[float] = None
    acceptance_criteria: list = Field(default_factory=list)
    dependencies: list = Field(default_factory=list)
    labels: list = Field(default_factory=list)
    task_type: Optional[str] = None
    business_value: Optional[str] = None
    # Enriched fields
    is_valid: bool = Field(default=True, description="Item có hợp lệ không")
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    # Assignment fields
    assigned_to_dev: Optional[str] = Field(default=None, description="Developer ID được assign")
    assigned_to_tester: Optional[str] = Field(default=None, description="Tester ID được assign")
    dev_status: Optional[str] = Field(default=None, description="Trạng thái dev: pending, in_progress, done")
    test_status: Optional[str] = Field(default=None, description="Trạng thái test: pending, in_progress, done")


class SprintPlannerState(BaseModel):
    """State cho Sprint Planner Agent workflow.

    Workflow:
    1. enrich: Đọc backlog.json và sprint.json, kiểm tra và làm giàu dữ liệu
    2. verify: Xác thực dữ liệu, nếu có lỗi quay lại enrich kèm feedback
    """

    # ========================================================================
    # Input Data
    # ========================================================================
    backlog_items: list[dict] = Field(
        default_factory=list,
        description="Danh sách backlog items từ backlog.json"
    )
    sprints: list[dict] = Field(
        default_factory=list,
        description="Danh sách sprints từ sprint.json"
    )

    # ========================================================================
    # Enrich Node Outputs
    # ========================================================================
    enriched_items: list[EnrichedItem] = Field(
        default_factory=list,
        description="Backlog items đã được enrich và validate"
    )
    enriched_sprints: list[dict] = Field(
        default_factory=list,
        description="Sprints đã được enrich"
    )

    # Validation results từ enrich node
    validation_issues: list[ValidationIssue] = Field(
        default_factory=list,
        description="Danh sách validation issues tìm được"
    )

    # Statistics
    total_items: int = Field(default=0, description="Tổng số backlog items")
    total_sprints: int = Field(default=0, description="Tổng số sprints")
    total_issues: int = Field(default=0, description="Tổng số issues tìm được")
    critical_issues_count: int = Field(default=0, description="Số lượng critical issues")

    # ========================================================================
    # Verify Node Outputs
    # ========================================================================
    is_valid: bool = Field(
        default=False,
        description="Dữ liệu có hợp lệ để tiếp tục không"
    )
    verification_passed: bool = Field(
        default=False,
        description="Verification đã pass không"
    )

    # ========================================================================
    # Assignment Node Outputs
    # ========================================================================
    dev_assignments: list[dict] = Field(
        default_factory=list,
        description="Danh sách assignments cho developers"
    )
    tester_assignments: list[dict] = Field(
        default_factory=list,
        description="Danh sách assignments cho testers"
    )
    assigned_items: list[EnrichedItem] = Field(
        default_factory=list,
        description="Enriched items với assignment info"
    )

    # ========================================================================
    # Kanban Push Node Outputs
    # ========================================================================
    kanban_cards: list[dict] = Field(
        default_factory=list,
        description="Danh sách kanban cards được push"
    )
    kanban_push_status: str = Field(
        default="pending",
        description="Trạng thái kanban push: pending, success, error, no_items"
    )

    # ========================================================================
    # User Feedback & Loop Control
    # ========================================================================
    user_feedback: Optional[str] = Field(
        default=None,
        description="Feedback từ user khi verify fail"
    )
    user_approval: Optional[str] = Field(
        default=None,
        description="User choice: 'approve' hoặc 'fix'"
    )

    # Loop control
    max_loops: int = Field(default=2, description="Số lần enrich tối đa")
    current_loop: int = Field(default=0, description="Số lần enrich hiện tại")

    # ========================================================================
    # Status & Metadata
    # ========================================================================
    status: str = Field(
        default="initial",
        description="Trạng thái workflow: initial, enriching, verifying, approved, failed"
    )
    error_message: Optional[str] = Field(default=None, description="Error message nếu có")
