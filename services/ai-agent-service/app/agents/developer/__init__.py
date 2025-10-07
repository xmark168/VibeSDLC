"""
Developer Agent Package

This package contains the Developer Agent and its sub-agents for implementing
code solutions and ensuring code quality throughout the development lifecycle.

Sub-Agents:
- Task Analyzer: Analyzes and breaks down development tasks
- Code Implementer: Implements code solutions following best practices
- Test Generator: Creates comprehensive test suites
- Quality Assurer: Ensures code quality and standards compliance
- Code Reviewer: Reviews code logic, security, and architecture
- Refactoring Agent: Identifies code smells and manages technical debt
- Dependency Manager: Manages dependencies and security vulnerabilities
- Performance Optimizer: Profiles and optimizes code performance
- Documentation Generator: Generates comprehensive documentation
- Integration Manager: Handles integration and deployment processes
"""

from .state import (
    DeveloperAgentState,
    TaskAnalyzerState,
    CodeImplementerState,
    TestGeneratorState,
    QualityAssurerState,
    DocumentationGeneratorState,
    IntegrationManagerState,
    TaskStatus,
    TaskPriority,
    QualityGateStatus,
)

from .workflows import (
    WorkflowStep,
    WorkflowTransition,
    TaskAnalysisWorkflow,
    CodeImplementationWorkflow,
    TestGenerationWorkflow,
    QualityAssuranceWorkflow,
    DocumentationGenerationWorkflow,
    IntegrationManagementWorkflow,
)

__all__ = [
    # State classes
    "DeveloperAgentState",
    "TaskAnalyzerState",
    "CodeImplementerState",
    "TestGeneratorState",
    "QualityAssurerState",
    "DocumentationGeneratorState",
    "IntegrationManagerState",
    # Enums
    "TaskStatus",
    "TaskPriority",
    "QualityGateStatus",
    "WorkflowStep",
    # Workflow classes
    "WorkflowTransition",
    "TaskAnalysisWorkflow",
    "CodeImplementationWorkflow",
    "TestGenerationWorkflow",
    "QualityAssuranceWorkflow",
    "DocumentationGenerationWorkflow",
    "IntegrationManagementWorkflow",
]
