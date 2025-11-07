"""State definitions for Retro Coordinator Agent."""

from typing import TypedDict, Optional, List


class Feedback(TypedDict):
    """Feedback item from team member."""
    source: str  # "po", "developer", "tester"
    source_name: str
    category: str  # "what_went_well", "what_went_wrong", "improvement"
    content: str
    priority: str  # "high", "medium", "low"
    impact: Optional[str]


class Issue(TypedDict):
    """Categorized issue from feedback."""
    id: str
    category: str  # "technical", "process", "communication", "resource", "quality"
    description: str
    frequency: int  # How many times mentioned
    severity: str  # "high", "medium", "low"
    sources: List[str]  # Who mentioned it
    impact: Optional[str]


class ImprovementIdea(TypedDict):
    """Improvement idea generated from issues."""
    id: str
    title: str
    description: str
    related_issues: List[str]
    expected_benefit: str
    effort_estimate: str  # "low", "medium", "high"
    priority: str  # "high", "medium", "low"


class ActionItem(TypedDict):
    """Action item for next sprint."""
    id: str
    title: str
    description: str
    owner: str
    due_date: str
    priority: str  # "high", "medium", "low"
    related_improvement: str
    status: str  # "pending", "in_progress", "done"


class RetroState(TypedDict):
    """State for Retro Coordinator Agent."""
    sprint_id: str
    sprint_name: str
    date: str
    project_id: Optional[str]  # Project ID for rule storage

    # Collected feedback
    po_feedback: Optional[dict]  # Result from ProductOwnerAgent
    dev_feedback: Optional[dict]  # Result from DeveloperAgent
    tester_feedback: Optional[dict]  # Result from TesterAgent

    # Aggregated feedback
    all_feedback: Optional[List[Feedback]]

    # Analysis results
    categorized_issues: Optional[List[Issue]]
    improvement_ideas: Optional[List[ImprovementIdea]]

    # Action items for next sprint
    action_items: Optional[List[ActionItem]]

    # Extracted learnings (NEW)
    extracted_rules: Optional[List[dict]]  # Rules extracted from action items

    # Final summary
    retro_summary: Optional[dict]

    # Error tracking
    error: Optional[str]

