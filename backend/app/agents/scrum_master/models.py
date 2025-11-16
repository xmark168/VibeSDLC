"""Database-compatible Pydantic models for Scrum Master Agent.

Models này match với database schema (backlog_items và sprints tables)
nhưng không cần database connection - chỉ để validate và format output.
"""

from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


# ==================== ENUMS ====================

class SprintStatus(str, Enum):
    """Sprint status enum - khớp với database."""
    PLANNED = "Planned"
    ACTIVE = "Active"
    COMPLETED = "Completed"


class ItemType(str, Enum):
    """Backlog item type enum - khớp với database."""
    EPIC = "Epic"
    USER_STORY = "User Story"
    TASK = "Task"
    SUB_TASK = "Sub-task"


class ItemStatus(str, Enum):
    """Backlog item status enum - khớp với database."""
    BACKLOG = "Backlog"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class TaskType(str, Enum):
    """Task type for assignment."""
    DEVELOPMENT = "Development"
    TESTING = "Testing"
    DESIGN = "Design"
    DOCUMENTATION = "Documentation"
    DEVOPS = "DevOps"


# ==================== DATABASE MODELS ====================

class SprintDB(BaseModel):
    """Sprint model - khớp với sprints table trong database.
    
    Database schema:
    - id (PK)
    - project_id (FK)
    - name
    - number
    - goal
    - status
    - start_date
    - end_date
    - velocity_plan
    - velocity_actual
    - created_at
    - updated_at
    """
    id: str = Field(description="Sprint ID (sprint-1, sprint-2, ...)")
    project_id: str = Field(default="project-001", description="Project ID (hardcoded for now)")
    name: str = Field(description="Sprint name (e.g., 'Sprint 1')")
    number: int = Field(description="Sprint number (1, 2, 3, ...)")
    goal: str = Field(description="Sprint goal")
    status: SprintStatus = Field(default=SprintStatus.PLANNED)
    start_date: Optional[date] = Field(default=None, description="Sprint start date")
    end_date: Optional[date] = Field(default=None, description="Sprint end date")
    velocity_plan: int = Field(default=0, description="Planned velocity (story points)")
    velocity_actual: int = Field(default=0, description="Actual velocity (story points)")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class BacklogItemDB(BaseModel):
    """Backlog item model - khớp với backlog_items table trong database.
    
    Database schema:
    - id (PK)
    - sprint_id (FK to sprints)
    - parent_id (Self-referencing FK)
    - type
    - title
    - description
    - status
    - reviewer_id (FK to users)
    - assignee_id (FK to users)
    - rank
    - estimate_value (hours for Task/Sub-task)
    - story_point (points for User Story)
    - pause
    - deadline
    - created_at
    - updated_at
    
    Note: Dependencies, acceptance_criteria, labels sẽ cần thêm vào DB sau
    """
    id: str = Field(description="Item ID (EPIC-001, US-001, TASK-001, SUB-001)")
    sprint_id: Optional[str] = Field(default=None, description="Sprint ID (FK)")
    parent_id: Optional[str] = Field(default=None, description="Parent item ID (FK)")
    type: ItemType = Field(description="Item type")
    title: str = Field(description="Item title")
    description: str = Field(default="", description="Item description")
    status: ItemStatus = Field(default=ItemStatus.BACKLOG)
    reviewer_id: Optional[str] = Field(default=None, description="Reviewer user ID")
    assignee_id: Optional[str] = Field(default=None, description="Assignee user ID")
    rank: int = Field(description="Priority rank (1 = highest)")
    estimate_value: Optional[float] = Field(default=None, description="Estimate hours (Task/Sub-task)")
    story_point: Optional[int] = Field(default=None, description="Story points (User Story)")
    pause: bool = Field(default=False, description="Is task paused?")
    deadline: Optional[date] = Field(default=None, description="Task deadline")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Extra fields từ PO output (không có trong DB hiện tại)
    # Sẽ cần migration để thêm vào DB sau
    acceptance_criteria: list[str] = Field(default_factory=list, description="Acceptance criteria (not in DB yet)")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies (not in DB yet)")
    labels: list[str] = Field(default_factory=list, description="Labels (not in DB yet)")
    task_type: Optional[TaskType] = Field(default=None, description="Task type for assignment (not in DB yet)")

    class Config:
        use_enum_values = True


# ==================== HELPER MODELS ====================

class TeamMember(BaseModel):
    """Team member model."""
    id: str = Field(description="User ID")
    name: str = Field(description="User name")
    role: Literal["developer", "tester", "designer", "reviewer"] = Field(description="Role")


class DoRCheckResult(BaseModel):
    """Definition of Ready check result."""
    item_id: str
    passed: bool
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AssignmentResult(BaseModel):
    """Task assignment result."""
    item_id: str
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    status: ItemStatus
    reason: str = Field(description="Why assigned to this person")


class ScrumMasterOutput(BaseModel):
    """Final output từ Scrum Master Agent - ready for database insert."""
    sprints: list[SprintDB] = Field(description="Sprints ready for DB insert")
    backlog_items: list[BacklogItemDB] = Field(description="Backlog items ready for DB insert")
    assignments: list[AssignmentResult] = Field(description="Assignment details")
    dor_results: list[DoRCheckResult] = Field(description="DoR check results")
    summary: dict = Field(description="Summary statistics")

