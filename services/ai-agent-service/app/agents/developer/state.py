"""
Developer Agent State Management

This module defines the state structure for the Developer Agent workflow,
including all sub-agent states and transitions.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration"""
    TODO = "todo"
    ANALYZING = "analyzing"
    IN_PROGRESS = "in_progress"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    REVIEWING = "reviewing"
    INTEGRATING = "integrating"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"


class TaskPriority(str, Enum):
    """Task priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class QualityGateStatus(str, Enum):
    """Quality gate status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DeveloperAgentState(BaseModel):
    """Main state for Developer Agent workflow"""
    
    # Task Information
    task_id: Optional[str] = None
    task_description: Optional[str] = None
    acceptance_criteria: List[str] = Field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    story_points: Optional[int] = None
    
    # Analysis Results
    technical_requirements: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    complexity_score: Optional[float] = None
    estimated_effort: Optional[str] = None
    implementation_plan: Optional[Dict[str, Any]] = None
    
    # Implementation
    code_solution: Optional[str] = None
    code_files: Dict[str, str] = Field(default_factory=dict)  # filename -> content
    design_patterns: List[str] = Field(default_factory=list)
    
    # Testing
    test_cases: List[str] = Field(default_factory=list)
    test_files: Dict[str, str] = Field(default_factory=dict)  # filename -> content
    coverage_score: Optional[float] = None
    test_results: Optional[Dict[str, Any]] = None
    
    # Quality Gates
    lint_passed: bool = False
    lint_results: Optional[Dict[str, Any]] = None
    tests_passed: bool = False
    security_scan_passed: bool = False
    security_results: Optional[Dict[str, Any]] = None
    documentation_complete: bool = False
    
    # Documentation
    api_documentation: Optional[str] = None
    code_comments: Dict[str, str] = Field(default_factory=dict)
    user_guide: Optional[str] = None
    examples: List[str] = Field(default_factory=list)
    
    # Integration
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    review_feedback: List[str] = Field(default_factory=list)
    deployment_status: Optional[str] = None
    deployment_url: Optional[str] = None
    
    # Workflow Control
    iteration_count: int = 0
    max_iterations: int = 5
    current_step: Optional[str] = None
    awaiting_user: bool = False
    finalized: bool = False
    error_message: Optional[str] = None
    
    # Sub-agent States
    task_analyzer_complete: bool = False
    code_implementer_complete: bool = False
    test_generator_complete: bool = False
    quality_assurer_complete: bool = False
    documentation_generator_complete: bool = False
    integration_manager_complete: bool = False
    
    # Metrics
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    total_effort_hours: Optional[float] = None
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True


class TaskAnalyzerState(BaseModel):
    """State for Task Analyzer sub-agent"""
    
    # Input
    raw_task_description: str
    acceptance_criteria: List[str] = Field(default_factory=list)
    
    # Analysis Results
    parsed_requirements: List[str] = Field(default_factory=list)
    functional_requirements: List[str] = Field(default_factory=list)
    non_functional_requirements: List[str] = Field(default_factory=list)
    technical_constraints: List[str] = Field(default_factory=list)
    
    # Dependencies and Complexity
    dependencies: List[str] = Field(default_factory=list)
    complexity_factors: List[str] = Field(default_factory=list)
    complexity_score: Optional[float] = None
    
    # Effort Estimation
    estimated_hours: Optional[float] = None
    confidence_level: Optional[float] = None
    risk_factors: List[str] = Field(default_factory=list)
    
    # Implementation Plan
    implementation_steps: List[str] = Field(default_factory=list)
    recommended_patterns: List[str] = Field(default_factory=list)
    technology_stack: List[str] = Field(default_factory=list)


class CodeImplementerState(BaseModel):
    """State for Code Implementer sub-agent"""
    
    # Input
    requirements: List[str] = Field(default_factory=list)
    design_patterns: List[str] = Field(default_factory=list)
    technology_stack: List[str] = Field(default_factory=list)
    
    # Generated Code
    main_code: Optional[str] = None
    supporting_files: Dict[str, str] = Field(default_factory=dict)
    configuration_files: Dict[str, str] = Field(default_factory=dict)
    
    # Code Quality
    code_style_score: Optional[float] = None
    complexity_metrics: Optional[Dict[str, Any]] = None
    performance_considerations: List[str] = Field(default_factory=list)
    
    # Error Handling
    error_scenarios: List[str] = Field(default_factory=list)
    exception_handling: Dict[str, str] = Field(default_factory=dict)


class TestGeneratorState(BaseModel):
    """State for Test Generator sub-agent"""
    
    # Input
    code_to_test: str
    requirements: List[str] = Field(default_factory=list)
    
    # Generated Tests
    unit_tests: List[str] = Field(default_factory=list)
    integration_tests: List[str] = Field(default_factory=list)
    test_files: Dict[str, str] = Field(default_factory=dict)
    
    # Test Coverage
    coverage_target: float = 80.0
    coverage_analysis: Optional[Dict[str, Any]] = None
    uncovered_lines: List[int] = Field(default_factory=list)
    
    # Test Quality
    test_quality_score: Optional[float] = None
    edge_cases_covered: List[str] = Field(default_factory=list)
    mock_objects: Dict[str, str] = Field(default_factory=dict)


class QualityAssurerState(BaseModel):
    """State for Quality Assurer sub-agent"""
    
    # Input
    code_files: Dict[str, str] = Field(default_factory=dict)
    test_files: Dict[str, str] = Field(default_factory=dict)
    
    # Linting Results
    lint_results: Optional[Dict[str, Any]] = None
    lint_errors: List[str] = Field(default_factory=list)
    lint_warnings: List[str] = Field(default_factory=list)
    formatting_issues: List[str] = Field(default_factory=list)
    
    # Security Scan Results
    security_vulnerabilities: List[str] = Field(default_factory=list)
    security_warnings: List[str] = Field(default_factory=list)
    dependency_issues: List[str] = Field(default_factory=list)
    
    # Standards Compliance
    coding_standards_score: Optional[float] = None
    standards_violations: List[str] = Field(default_factory=list)
    best_practices_score: Optional[float] = None
    
    # Overall Quality
    overall_quality_score: Optional[float] = None
    quality_recommendations: List[str] = Field(default_factory=list)


class DocumentationGeneratorState(BaseModel):
    """State for Documentation Generator sub-agent"""
    
    # Input
    code_files: Dict[str, str] = Field(default_factory=dict)
    requirements: List[str] = Field(default_factory=list)
    
    # Generated Documentation
    api_documentation: Optional[str] = None
    code_comments: Dict[str, str] = Field(default_factory=dict)
    user_guide: Optional[str] = None
    developer_guide: Optional[str] = None
    examples: List[str] = Field(default_factory=list)
    
    # Documentation Quality
    documentation_completeness: Optional[float] = None
    clarity_score: Optional[float] = None
    accuracy_score: Optional[float] = None
    
    # Documentation Structure
    toc_generated: bool = False
    cross_references: Dict[str, List[str]] = Field(default_factory=dict)
    version_info: Optional[str] = None


class IntegrationManagerState(BaseModel):
    """State for Integration Manager sub-agent"""
    
    # Input
    code_files: Dict[str, str] = Field(default_factory=dict)
    test_files: Dict[str, str] = Field(default_factory=dict)
    documentation: Dict[str, str] = Field(default_factory=dict)
    
    # Pull Request Management
    pr_title: Optional[str] = None
    pr_description: Optional[str] = None
    pr_branch: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    
    # Code Review
    review_status: Optional[str] = None
    review_comments: List[str] = Field(default_factory=list)
    requested_changes: List[str] = Field(default_factory=list)
    approval_status: Optional[str] = None
    
    # Deployment
    deployment_target: Optional[str] = None
    deployment_status: Optional[str] = None
    deployment_url: Optional[str] = None
    rollback_plan: Optional[str] = None
    
    # CI/CD Integration
    pipeline_status: Optional[str] = None
    build_results: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None
