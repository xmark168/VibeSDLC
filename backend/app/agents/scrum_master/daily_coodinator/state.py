"""State definitions for Daily Coordinator Agent."""

from typing import TypedDict, Optional, List


class DeveloperReport(TypedDict):
    """Developer daily report."""
    developer_id: str
    developer_name: str
    date: str
    tasks_completed_yesterday: List[dict]
    tasks_in_progress: List[dict]
    tasks_planned_today: List[dict]
    blockers: List[dict]
    hours_worked_yesterday: float
    estimated_hours_today: float
    capacity_utilization: float


class TesterReport(TypedDict):
    """Tester daily report."""
    tester_id: str
    tester_name: str
    date: str
    tests_completed_yesterday: List[dict]
    tests_in_progress: List[dict]
    tests_planned_today: List[dict]
    bugs_found: List[dict]
    blockers: List[dict]
    test_coverage: float
    hours_worked_yesterday: float
    estimated_hours_today: float
    capacity_utilization: float


class Blocker(TypedDict):
    """Blocker information."""
    type: str  # technical, dependency, resource, other
    description: str
    severity: str  # high, medium, low
    owner: Optional[str]
    impact: Optional[str]


class DailyScrumState(TypedDict):
    """State for Daily Coordinator Agent."""
    sprint_id: str
    date: str
    project_id: Optional[str]  # Project ID for rule storage

    # Collected reports
    dev_reports: Optional[dict]  # Result from DeveloperAgent.get_daily_reports()
    tester_reports: Optional[dict]  # Result from TesterAgent.get_daily_reports()

    # Aggregated data
    aggregated_reports: Optional[dict]

    # Analysis results
    detected_blockers: Optional[List[Blocker]]
    blocker_analysis: Optional[dict]

    # Extracted learnings (NEW)
    extracted_rules: Optional[List[dict]]  # Rules extracted from blockers

    # Task status updates
    task_status_updates: Optional[dict]

    # Final summary
    daily_summary: Optional[dict]

    # Error tracking
    error: Optional[str]
