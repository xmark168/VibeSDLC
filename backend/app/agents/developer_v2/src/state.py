"""Developer V2 State Definition."""

from typing import TypedDict, Literal, Any, List, Optional


Action = Literal["ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE", "CLARIFY", "RESPOND"]
TaskType = Literal["feature", "bugfix", "refactor", "enhancement", "documentation"]
Complexity = Literal["low", "medium", "high"]


class DeveloperState(TypedDict, total=False):
    # Input from story event
    story_id: str
    story_content: str
    story_title: str
    acceptance_criteria: List[str]
    project_id: str
    task_id: str
    user_id: str
    langfuse_handler: Any
    
    # Router output
    action: Action
    task_type: TaskType
    complexity: Complexity
    
    # Analysis results
    analysis_result: dict
    affected_files: List[str]
    dependencies: List[str]
    risks: List[str]
    estimated_hours: float
    
    # Planning results
    implementation_plan: List[dict]
    current_step: int
    total_steps: int
    
    # Implementation results
    code_changes: List[dict]
    files_created: List[str]
    files_modified: List[str]
    
    # Validation results
    validation_result: dict
    tests_passed: bool
    lint_passed: bool
    ac_verified: List[str]
    
    # Output
    message: str
    reason: str
    confidence: float
    error: Optional[str]
