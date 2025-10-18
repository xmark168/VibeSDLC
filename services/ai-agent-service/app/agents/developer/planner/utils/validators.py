"""
Planner Validators

Validation utilities cho planner workflow.
"""

from typing import Dict, Any, List, Tuple
import re


def validate_task_requirements(task_requirements: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate task requirements completeness và quality.
    
    Args:
        task_requirements: TaskRequirements object as dict
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check required fields
    required_fields = ["task_id", "requirements", "acceptance_criteria"]
    for field in required_fields:
        if not task_requirements.get(field):
            issues.append(f"Missing required field: {field}")
    
    # Validate requirements quality
    requirements = task_requirements.get("requirements", [])
    if len(requirements) < 1:
        issues.append("At least one functional requirement is needed")
    
    # Check for vague requirements
    vague_patterns = [
        r"\b(some|many|few|several|various)\b",
        r"\b(good|bad|better|worse|nice|cool)\b",
        r"\b(easy|hard|simple|complex)\b"
    ]
    
    for req in requirements:
        for pattern in vague_patterns:
            if re.search(pattern, req, re.IGNORECASE):
                issues.append(f"Vague requirement detected: '{req[:50]}...'")
                break
    
    # Validate acceptance criteria
    acceptance_criteria = task_requirements.get("acceptance_criteria", [])
    if len(acceptance_criteria) < 1:
        issues.append("At least one acceptance criterion is needed")
    
    # Check for measurable criteria
    measurable_keywords = ["should", "must", "will", "can", "cannot", "verify", "test"]
    measurable_count = 0
    
    for criterion in acceptance_criteria:
        if any(keyword in criterion.lower() for keyword in measurable_keywords):
            measurable_count += 1
    
    if measurable_count == 0:
        issues.append("Acceptance criteria should be measurable and testable")
    
    return len(issues) == 0, issues


def validate_codebase_analysis(codebase_analysis: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate codebase analysis completeness.
    
    Args:
        codebase_analysis: CodebaseAnalysis object as dict
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check if any files are identified
    files_to_create = codebase_analysis.get("files_to_create", [])
    files_to_modify = codebase_analysis.get("files_to_modify", [])
    
    if not files_to_create and not files_to_modify:
        issues.append("No files identified for creation or modification")
    
    # Validate file paths
    for file_path in files_to_create + files_to_modify:
        if not validate_file_path(file_path):
            issues.append(f"Invalid file path: {file_path}")
    
    # Check for affected modules
    affected_modules = codebase_analysis.get("affected_modules", [])
    if not affected_modules and (files_to_create or files_to_modify):
        issues.append("No affected modules identified despite file changes")
    
    # Validate testing requirements
    testing_requirements = codebase_analysis.get("testing_requirements", {})
    if not testing_requirements:
        issues.append("Testing requirements not specified")
    
    return len(issues) == 0, issues


def validate_dependency_mapping(dependency_mapping: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate dependency mapping logic.
    
    Args:
        dependency_mapping: DependencyMapping object as dict
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check execution order
    execution_order = dependency_mapping.get("execution_order", [])
    if not execution_order:
        issues.append("No execution order specified")
    
    # Validate execution order structure
    for i, step in enumerate(execution_order):
        if not isinstance(step, dict):
            issues.append(f"Execution step {i+1} is not properly structured")
            continue
            
        if "step" not in step:
            issues.append(f"Execution step {i+1} missing 'step' field")
        
        if "dependencies" not in step:
            issues.append(f"Execution step {i+1} missing 'dependencies' field")
    
    # Check for circular dependencies
    circular_deps = find_circular_dependencies(execution_order)
    if circular_deps:
        issues.append(f"Circular dependencies detected: {circular_deps}")
    
    # Validate parallel opportunities
    parallel_opportunities = dependency_mapping.get("parallel_opportunities", [])
    if len(execution_order) > 3 and not parallel_opportunities:
        issues.append("Consider identifying parallel execution opportunities for efficiency")
    
    return len(issues) == 0, issues


def validate_implementation_plan(implementation_plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate implementation plan completeness và consistency.
    
    Args:
        implementation_plan: ImplementationPlan object as dict
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check required fields
    required_fields = ["task_id", "complexity_score", "implementation_steps"]
    for field in required_fields:
        if field not in implementation_plan:
            issues.append(f"Missing required field: {field}")
    
    # Validate complexity score
    complexity_score = implementation_plan.get("complexity_score", 0)
    if not isinstance(complexity_score, int) or complexity_score < 1 or complexity_score > 10:
        issues.append("Complexity score must be integer between 1-10")
    
    # Validate implementation steps
    implementation_steps = implementation_plan.get("implementation_steps", [])
    if not implementation_steps:
        issues.append("No implementation steps specified")
    
    total_hours = 0
    for i, step in enumerate(implementation_steps):
        step_issues = validate_implementation_step(step, i+1)
        issues.extend(step_issues)
        
        # Accumulate hours
        estimated_hours = step.get("estimated_hours", 0)
        if isinstance(estimated_hours, (int, float)):
            total_hours += estimated_hours
    
    # Validate total effort
    plan_total_hours = implementation_plan.get("total_estimated_hours", 0)
    if abs(total_hours - plan_total_hours) > 0.1:
        issues.append(f"Total hours mismatch: steps sum to {total_hours}, plan shows {plan_total_hours}")
    
    # Validate story points
    story_points = implementation_plan.get("story_points", 0)
    if not isinstance(story_points, int) or story_points not in [1, 2, 3, 5, 8, 13, 21]:
        issues.append("Story points must be Fibonacci number: 1, 2, 3, 5, 8, 13, 21")
    
    # Check effort consistency
    if story_points > 0 and total_hours > 0:
        hours_per_point = total_hours / story_points
        if hours_per_point < 0.5 or hours_per_point > 8:
            issues.append(f"Effort ratio unusual: {hours_per_point:.1f} hours per story point")
    
    # Validate risks
    risks = implementation_plan.get("risks", [])
    if complexity_score >= 7 and not risks:
        issues.append("High complexity tasks should identify potential risks")
    
    return len(issues) == 0, issues


def validate_implementation_step(step: Dict[str, Any], step_number: int) -> List[str]:
    """
    Validate individual implementation step.
    
    Args:
        step: Implementation step dict
        step_number: Step number for error reporting
        
    Returns:
        List of validation issues
    """
    issues = []
    
    # Check required fields
    required_fields = ["title", "description", "estimated_hours"]
    for field in required_fields:
        if field not in step:
            issues.append(f"Step {step_number} missing required field: {field}")
    
    # Validate title
    title = step.get("title", "")
    if len(title) < 5:
        issues.append(f"Step {step_number} title too short: '{title}'")
    
    # Validate description
    description = step.get("description", "")
    if len(description) < 10:
        issues.append(f"Step {step_number} description too brief")
    
    # Validate estimated hours
    estimated_hours = step.get("estimated_hours", 0)
    if not isinstance(estimated_hours, (int, float)) or estimated_hours <= 0:
        issues.append(f"Step {step_number} invalid estimated hours: {estimated_hours}")
    elif estimated_hours > 40:
        issues.append(f"Step {step_number} estimated hours too high: {estimated_hours} (consider breaking down)")
    
    # Validate files
    files = step.get("files", [])
    if not files:
        issues.append(f"Step {step_number} should specify affected files")
    
    return issues


def validate_file_path(file_path: str) -> bool:
    """
    Validate file path format.
    
    Args:
        file_path: File path to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not file_path or not isinstance(file_path, str):
        return False
    
    # Check for invalid characters
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    if any(char in file_path for char in invalid_chars):
        return False
    
    # Check for reasonable length
    if len(file_path) > 260:  # Windows MAX_PATH limit
        return False
    
    # Check for valid extension
    valid_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml', '.md', '.txt', '.sql']
    if '.' in file_path:
        extension = '.' + file_path.split('.')[-1]
        if extension not in valid_extensions:
            return False
    
    return True


def find_circular_dependencies(execution_order: List[Dict[str, Any]]) -> List[str]:
    """
    Find circular dependencies trong execution order.
    
    Args:
        execution_order: List of execution steps
        
    Returns:
        List of circular dependency descriptions
    """
    circular_deps = []
    
    # Build dependency graph
    step_map = {}
    for step in execution_order:
        step_name = step.get("step", "")
        dependencies = step.get("dependencies", [])
        step_map[step_name] = dependencies
    
    # Check for cycles using DFS
    visited = set()
    rec_stack = set()
    
    def has_cycle(node, path):
        if node in rec_stack:
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            circular_deps.append(" -> ".join(cycle))
            return True
        
        if node in visited:
            return False
        
        visited.add(node)
        rec_stack.add(node)
        
        for dependency in step_map.get(node, []):
            if has_cycle(dependency, path + [node]):
                return True
        
        rec_stack.remove(node)
        return False
    
    for step_name in step_map:
        if step_name not in visited:
            has_cycle(step_name, [])
    
    return circular_deps


def calculate_validation_score(
    completeness_score: float,
    consistency_score: float,
    effort_score: float,
    risk_score: float
) -> float:
    """
    Calculate overall validation score.
    
    Args:
        completeness_score: Completeness score (0.0-1.0)
        consistency_score: Consistency score (0.0-1.0)
        effort_score: Effort estimation score (0.0-1.0)
        risk_score: Risk assessment score (0.0-1.0)
        
    Returns:
        Overall validation score (0.0-1.0)
    """
    # Weighted average with emphasis on completeness and consistency
    weights = {
        "completeness": 0.35,
        "consistency": 0.35,
        "effort": 0.20,
        "risk": 0.10
    }
    
    overall_score = (
        completeness_score * weights["completeness"] +
        consistency_score * weights["consistency"] +
        effort_score * weights["effort"] +
        risk_score * weights["risk"]
    )
    
    return round(overall_score, 3)


def validate_plan_readiness(implementation_plan: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Comprehensive validation of plan readiness for implementation.
    
    Args:
        implementation_plan: Complete implementation plan
        
    Returns:
        Tuple of (is_ready, validation_score, issues_list)
    """
    all_issues = []
    
    # Validate each component
    plan_valid, plan_issues = validate_implementation_plan(implementation_plan)
    all_issues.extend(plan_issues)
    
    # Calculate component scores
    completeness_score = 1.0 - (len([i for i in plan_issues if "missing" in i.lower()]) * 0.2)
    consistency_score = 1.0 - (len([i for i in plan_issues if "mismatch" in i.lower()]) * 0.3)
    effort_score = 1.0 - (len([i for i in plan_issues if "hours" in i.lower() or "effort" in i.lower()]) * 0.25)
    risk_score = 1.0 - (len([i for i in plan_issues if "risk" in i.lower()]) * 0.2)
    
    # Ensure scores are in valid range
    completeness_score = max(0.0, min(1.0, completeness_score))
    consistency_score = max(0.0, min(1.0, consistency_score))
    effort_score = max(0.0, min(1.0, effort_score))
    risk_score = max(0.0, min(1.0, risk_score))
    
    # Calculate overall score
    validation_score = calculate_validation_score(
        completeness_score, consistency_score, effort_score, risk_score
    )
    
    # Determine readiness (threshold: 0.7)
    is_ready = validation_score >= 0.7 and len(all_issues) == 0
    
    return is_ready, validation_score, all_issues
