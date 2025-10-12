"""
Developer Agent Configuration

This module contains configuration settings for the Developer Agent
and its sub-agents.
"""

import os
from typing import List
from dataclasses import dataclass


@dataclass
class TaskAnalyzerConfig:
    """Configuration for Task Analyzer sub-agent"""

    # Analysis settings
    complexity_weight_functional: float = 0.4
    complexity_weight_non_functional: float = 0.3
    complexity_weight_dependencies: float = 0.3

    # Effort estimation
    base_hours_per_complexity: float = 8.0
    max_effort_hours: float = 40.0
    min_effort_hours: float = 1.0

    # Confidence thresholds
    high_confidence_threshold: float = 0.8
    medium_confidence_threshold: float = 0.6
    low_confidence_threshold: float = 0.4


@dataclass
class CodeImplementerConfig:
    """Configuration for Code Implementer sub-agent"""

    # Code generation settings
    max_code_length: int = 10000
    include_type_hints: bool = True
    include_docstrings: bool = True
    include_error_handling: bool = True

    # Code quality settings
    max_function_length: int = 50
    max_class_length: int = 200
    max_parameters: int = 5

    # Design patterns
    preferred_patterns: List[str] = None

    def __post_init__(self):
        if self.preferred_patterns is None:
            self.preferred_patterns = [
                "Repository Pattern",
                "Factory Pattern",
                "Observer Pattern",
                "Strategy Pattern",
            ]


@dataclass
class TestGeneratorConfig:
    """Configuration for Test Generator sub-agent"""

    # Coverage settings
    target_coverage: float = 80.0
    minimum_coverage: float = 70.0
    critical_path_coverage: float = 95.0

    # Test types
    generate_unit_tests: bool = True
    generate_integration_tests: bool = True
    generate_end_to_end_tests: bool = False

    # Test quality
    max_test_length: int = 100
    include_edge_cases: bool = True
    include_performance_tests: bool = False

    # Mock settings
    auto_generate_mocks: bool = True
    mock_external_services: bool = True


@dataclass
class QualityAssurerConfig:
    """Configuration for Quality Assurer sub-agent"""

    # Quality gates
    linting_enabled: bool = True
    security_scan_enabled: bool = True
    standards_check_enabled: bool = True
    performance_check_enabled: bool = False

    # Thresholds
    lint_error_threshold: int = 0
    lint_warning_threshold: int = 10
    security_vulnerability_threshold: int = 0
    security_warning_threshold: int = 5

    # Quality scores
    minimum_quality_score: float = 80.0
    target_quality_score: float = 90.0

    # Tools
    linting_tool: str = "ruff"
    security_tool: str = "bandit"
    formatting_tool: str = "black"


@dataclass
class DocumentationGeneratorConfig:
    """Configuration for Documentation Generator sub-agent"""

    # Documentation types
    generate_api_docs: bool = True
    generate_user_guide: bool = True
    generate_developer_guide: bool = True
    generate_examples: bool = True

    # Quality settings
    target_completeness: float = 85.0
    minimum_clarity_score: float = 80.0

    # Format settings
    docstring_style: str = "google"  # google, numpy, sphinx
    include_type_hints: bool = True
    include_examples_in_docstrings: bool = True

    # Output formats
    output_formats: List[str] = None

    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ["markdown", "html"]


@dataclass
class IntegrationManagerConfig:
    """Configuration for Integration Manager sub-agent"""

    # Pull request settings
    auto_create_pr: bool = True
    pr_template_path: str = None
    required_reviewers: List[str] = None

    # Deployment settings
    auto_deploy_on_approval: bool = False
    deployment_environments: List[str] = None

    # CI/CD settings
    run_tests_on_pr: bool = True
    run_security_scan_on_pr: bool = True
    require_ci_passing: bool = True

    # Rollback settings
    auto_rollback_on_failure: bool = True
    rollback_timeout_minutes: int = 30

    def __post_init__(self):
        if self.deployment_environments is None:
            self.deployment_environments = ["staging", "production"]
        if self.required_reviewers is None:
            self.required_reviewers = []


@dataclass
class CodeReviewerConfig:
    """Configuration for Code Reviewer sub-agent"""

    # Review settings
    approval_threshold: float = 80.0
    logic_review_enabled: bool = True
    security_review_enabled: bool = True
    performance_review_enabled: bool = True
    architecture_review_enabled: bool = True

    # Scoring weights
    logic_weight: float = 0.3
    security_weight: float = 0.25
    performance_weight: float = 0.15
    maintainability_weight: float = 0.15
    readability_weight: float = 0.15

    # Thresholds
    critical_issue_threshold: int = 0
    major_issue_threshold: int = 3
    auto_approve_score: float = 95.0


@dataclass
class RefactoringAgentConfig:
    """Configuration for Refactoring Agent sub-agent"""

    # Detection settings
    smell_detection_enabled: bool = True
    debt_tracking_enabled: bool = True
    auto_refactor: bool = False

    # Thresholds
    max_method_lines: int = 50
    max_class_lines: int = 300
    max_parameters: int = 5
    max_complexity: int = 10

    # Priorities
    prioritize_security_debt: bool = True
    prioritize_performance_debt: bool = True

    # Effort estimation
    small_effort_hours: float = 2.0
    medium_effort_hours: float = 8.0
    large_effort_hours: float = 24.0


@dataclass
class DependencyManagerConfig:
    """Configuration for Dependency Manager sub-agent"""

    # Update settings
    auto_update_patch: bool = False
    auto_update_minor: bool = False
    check_frequency_days: int = 7

    # Security settings
    vulnerability_check_enabled: bool = True
    block_critical_vulnerabilities: bool = True
    block_high_vulnerabilities: bool = False

    # Health thresholds
    minimum_health_score: float = 70.0
    outdated_threshold_days: int = 180

    # Tools
    vulnerability_scanner: str = "pip-audit"  # pip-audit, safety, snyk


@dataclass
class PerformanceOptimizerConfig:
    """Configuration for Performance Optimizer sub-agent"""

    # Profiling settings
    profiling_enabled: bool = True
    auto_optimize: bool = False
    performance_threshold_ms: float = 1000.0

    # Optimization priorities
    optimize_cpu_bound: bool = True
    optimize_io_bound: bool = True
    optimize_memory: bool = True
    optimize_database: bool = True

    # Caching settings
    suggest_caching: bool = True
    cache_hit_rate_threshold: float = 0.7

    # Thresholds
    critical_slowness_ms: float = 5000.0
    high_slowness_ms: float = 2000.0
    memory_leak_threshold_mb: float = 100.0


@dataclass
class DeveloperAgentConfig:
    """Main configuration for Developer Agent"""

    # General settings
    max_iterations: int = 5
    timeout_minutes: int = 60
    retry_attempts: int = 3

    # Sub-agent configurations
    task_analyzer: TaskAnalyzerConfig = None
    code_implementer: CodeImplementerConfig = None
    test_generator: TestGeneratorConfig = None
    quality_assurer: QualityAssurerConfig = None
    code_reviewer: CodeReviewerConfig = None
    refactoring_agent: RefactoringAgentConfig = None
    dependency_manager: DependencyManagerConfig = None
    performance_optimizer: PerformanceOptimizerConfig = None
    documentation_generator: DocumentationGeneratorConfig = None
    integration_manager: IntegrationManagerConfig = None

    # Environment settings
    environment: str = "development"
    debug_mode: bool = False
    verbose_logging: bool = False

    def __post_init__(self):
        if self.task_analyzer is None:
            self.task_analyzer = TaskAnalyzerConfig()
        if self.code_implementer is None:
            self.code_implementer = CodeImplementerConfig()
        if self.test_generator is None:
            self.test_generator = TestGeneratorConfig()
        if self.quality_assurer is None:
            self.quality_assurer = QualityAssurerConfig()
        if self.code_reviewer is None:
            self.code_reviewer = CodeReviewerConfig()
        if self.refactoring_agent is None:
            self.refactoring_agent = RefactoringAgentConfig()
        if self.dependency_manager is None:
            self.dependency_manager = DependencyManagerConfig()
        if self.performance_optimizer is None:
            self.performance_optimizer = PerformanceOptimizerConfig()
        if self.documentation_generator is None:
            self.documentation_generator = DocumentationGeneratorConfig()
        if self.integration_manager is None:
            self.integration_manager = IntegrationManagerConfig()


def load_config_from_env() -> DeveloperAgentConfig:
    """Load configuration from environment variables"""

    return DeveloperAgentConfig(
        max_iterations=int(os.getenv("DEV_MAX_ITERATIONS", "5")),
        timeout_minutes=int(os.getenv("DEV_TIMEOUT_MINUTES", "60")),
        retry_attempts=int(os.getenv("DEV_RETRY_ATTEMPTS", "3")),
        environment=os.getenv("ENVIRONMENT", "development"),
        debug_mode=os.getenv("DEV_DEBUG", "false").lower() == "true",
        verbose_logging=os.getenv("DEV_VERBOSE", "false").lower() == "true",
        task_analyzer=TaskAnalyzerConfig(
            complexity_weight_functional=float(os.getenv("TASK_COMPLEXITY_FUNCTIONAL", "0.4")),
            complexity_weight_non_functional=float(
                os.getenv("TASK_COMPLEXITY_NON_FUNCTIONAL", "0.3")
            ),
            complexity_weight_dependencies=float(os.getenv("TASK_COMPLEXITY_DEPENDENCIES", "0.3")),
            base_hours_per_complexity=float(os.getenv("TASK_BASE_HOURS", "8.0")),
            max_effort_hours=float(os.getenv("TASK_MAX_HOURS", "40.0")),
        ),
        code_implementer=CodeImplementerConfig(
            max_code_length=int(os.getenv("CODE_MAX_LENGTH", "10000")),
            include_type_hints=os.getenv("CODE_INCLUDE_TYPE_HINTS", "true").lower() == "true",
            include_docstrings=os.getenv("CODE_INCLUDE_DOCSTRINGS", "true").lower() == "true",
            include_error_handling=os.getenv("CODE_INCLUDE_ERROR_HANDLING", "true").lower()
            == "true",
        ),
        test_generator=TestGeneratorConfig(
            target_coverage=float(os.getenv("TEST_TARGET_COVERAGE", "80.0")),
            minimum_coverage=float(os.getenv("TEST_MINIMUM_COVERAGE", "70.0")),
            generate_unit_tests=os.getenv("TEST_GENERATE_UNIT", "true").lower() == "true",
            generate_integration_tests=os.getenv("TEST_GENERATE_INTEGRATION", "true").lower()
            == "true",
        ),
        quality_assurer=QualityAssurerConfig(
            linting_enabled=os.getenv("QA_LINTING_ENABLED", "true").lower() == "true",
            security_scan_enabled=os.getenv("QA_SECURITY_ENABLED", "true").lower() == "true",
            minimum_quality_score=float(os.getenv("QA_MINIMUM_SCORE", "80.0")),
            linting_tool=os.getenv("QA_LINTING_TOOL", "ruff"),
            security_tool=os.getenv("QA_SECURITY_TOOL", "bandit"),
        ),
        documentation_generator=DocumentationGeneratorConfig(
            generate_api_docs=os.getenv("DOC_GENERATE_API", "true").lower() == "true",
            generate_user_guide=os.getenv("DOC_GENERATE_USER_GUIDE", "true").lower() == "true",
            target_completeness=float(os.getenv("DOC_TARGET_COMPLETENESS", "85.0")),
            docstring_style=os.getenv("DOC_DOCSTRING_STYLE", "google"),
        ),
        integration_manager=IntegrationManagerConfig(
            auto_create_pr=os.getenv("INTEGRATION_AUTO_PR", "true").lower() == "true",
            auto_deploy_on_approval=os.getenv("INTEGRATION_AUTO_DEPLOY", "false").lower() == "true",
            run_tests_on_pr=os.getenv("INTEGRATION_RUN_TESTS", "true").lower() == "true",
        ),
    )


def get_default_config() -> DeveloperAgentConfig:
    """Get default configuration"""
    return DeveloperAgentConfig()


# Global configuration instance
config = load_config_from_env()



