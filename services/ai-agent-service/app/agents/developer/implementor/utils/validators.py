"""
Implementor Validators

Validation utilities cho implementor workflow.
"""

import re
from typing import Any


def validate_implementation_plan(
    implementation_plan: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Validate implementation plan completeness và quality.

    Args:
        implementation_plan: Implementation plan từ Planner Agent

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Check required fields - support both nested and flat formats
    # Try nested format first
    if "task_info" in implementation_plan:
        task_info = implementation_plan["task_info"]
        task_id = task_info.get("task_id", "")
        description = task_info.get("description", "")
    else:
        # Fall back to flat format
        task_id = implementation_plan.get("task_id", "")
        description = implementation_plan.get("description", "")

    if not task_id:
        issues.append("Missing required field: task_id")
    if not description:
        issues.append("Missing required field: description")

    # Validate file operations - support both nested and flat formats
    if "file_changes" in implementation_plan:
        file_changes = implementation_plan["file_changes"]
        files_to_create = file_changes.get("files_to_create", [])
        files_to_modify = file_changes.get("files_to_modify", [])
    else:
        files_to_create = implementation_plan.get("files_to_create", [])
        files_to_modify = implementation_plan.get("files_to_modify", [])

    if not files_to_create and not files_to_modify:
        issues.append("No file operations specified - nothing to implement")

    # Validate file creation specs
    for i, file_spec in enumerate(files_to_create):
        file_issues = _validate_file_spec(file_spec, "create", i)
        issues.extend(file_issues)

    # Validate file modification specs
    for i, file_spec in enumerate(files_to_modify):
        file_issues = _validate_file_spec(file_spec, "modify", i)
        issues.extend(file_issues)

    return len(issues) == 0, issues


def validate_file_changes(
    files_to_create: list[dict[str, Any]], files_to_modify: list[dict[str, Any]]
) -> tuple[bool, list[str]]:
    """
    Validate file change specifications.

    Args:
        files_to_create: List of file creation specs
        files_to_modify: List of file modification specs

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Check for duplicate file paths
    all_paths = []

    for file_spec in files_to_create:
        path = file_spec.get("file_path", "")
        if path in all_paths:
            issues.append(f"Duplicate file path in creation list: {path}")
        all_paths.append(path)

    for file_spec in files_to_modify:
        path = file_spec.get("file_path", "")
        if path in [f.get("file_path") for f in files_to_create]:
            issues.append(f"File marked for both creation and modification: {path}")

    # Validate file paths
    for file_spec in files_to_create + files_to_modify:
        path_issues = _validate_file_path(file_spec.get("file_path", ""))
        issues.extend(path_issues)

    return len(issues) == 0, issues


def validate_git_operations(
    branch_name: str, commit_message: str = "", base_branch: str = "main"
) -> tuple[bool, list[str]]:
    """
    Validate Git operation parameters.

    Args:
        branch_name: Feature branch name
        commit_message: Commit message (optional)
        base_branch: Base branch name

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Validate branch name
    if not branch_name:
        issues.append("Branch name is required")
    else:
        # Git branch name rules
        invalid_chars = r"[~^:?*\[\]\\]"
        if re.search(invalid_chars, branch_name):
            issues.append(f"Branch name contains invalid characters: {branch_name}")

        if branch_name.startswith(".") or branch_name.endswith("."):
            issues.append("Branch name cannot start or end with '.'")

        if "//" in branch_name:
            issues.append("Branch name cannot contain consecutive slashes")

        if len(branch_name) > 250:
            issues.append("Branch name too long (max 250 characters)")

    # Validate commit message if provided
    if commit_message:
        if len(commit_message.split("\n")[0]) > 72:
            issues.append("Commit message first line too long (max 72 characters)")

        if not commit_message.strip():
            issues.append("Commit message cannot be empty")

    return len(issues) == 0, issues


def validate_tech_stack(tech_stack: str) -> tuple[bool, list[str]]:
    """
    Validate tech stack specification.

    Args:
        tech_stack: Technology stack identifier

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Supported tech stacks
    supported_stacks = {
        "fastapi",
        "python",
        "django",
        "flask",
        "nextjs",
        "react",
        "react-vite",
        "vue",
        "angular",
        "nodejs",
        "express",
        "nestjs",
        "spring",
        "java",
        "dotnet",
        "csharp",
        "go",
        "golang",
        "rust",
    }

    if tech_stack and tech_stack.lower() not in supported_stacks:
        issues.append(f"Unsupported tech stack: {tech_stack}")
        issues.append(f"Supported stacks: {', '.join(sorted(supported_stacks))}")

    return len(issues) == 0, issues


def validate_test_execution(
    test_command: str, exit_code: int, duration: float
) -> tuple[bool, list[str]]:
    """
    Validate test execution results.

    Args:
        test_command: Test command that was executed
        exit_code: Exit code from test execution
        duration: Test execution duration in seconds

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Check test command
    if not test_command.strip():
        issues.append("Test command is empty")

    # Check exit code
    if exit_code != 0:
        issues.append(f"Tests failed with exit code: {exit_code}")

    # Check duration (reasonable bounds)
    if duration < 0:
        issues.append("Invalid test duration (negative)")
    elif duration > 1800:  # 30 minutes
        issues.append(f"Test execution took too long: {duration:.1f}s")

    return len(issues) == 0, issues


def _validate_file_spec(
    file_spec: dict[str, Any], operation: str, index: int
) -> list[str]:
    """
    Validate individual file specification.

    Args:
        file_spec: File specification dictionary
        operation: "create" or "modify"
        index: Index in the list for error reporting

    Returns:
        List of validation issues
    """
    issues = []

    # Check required fields - support both nested and flat formats
    file_path = file_spec.get("file_path") or file_spec.get("path", "")
    if not file_path:
        issues.append(f"File {operation} #{index}: missing file_path or path")

    # Content will be generated by generate_code node, so don't require it here
    # if operation == "create" and not file_spec.get("content"):
    #     issues.append(f"File creation #{index}: missing content")

    # Validate file path - use the mapped file_path
    # file_path already extracted above with fallback
    if file_path:
        path_issues = _validate_file_path(file_path)
        for issue in path_issues:
            issues.append(f"File {operation} #{index}: {issue}")

    # Validate content for security
    content = file_spec.get("content", "")
    if content:
        security_issues = _validate_file_content_security(content)
        for issue in security_issues:
            issues.append(f"File {operation} #{index}: {issue}")

    return issues


def _validate_file_path(file_path: str) -> list[str]:
    """
    Validate file path for security và correctness.

    Args:
        file_path: File path to validate

    Returns:
        List of validation issues
    """
    issues = []

    if not file_path:
        return ["Empty file path"]

    # Security checks
    if ".." in file_path:
        issues.append("File path contains '..' (directory traversal)")

    if file_path.startswith("/"):
        issues.append("File path should be relative, not absolute")

    # Windows drive letters
    if re.match(r"^[A-Za-z]:", file_path):
        issues.append("File path should be relative, not absolute")

    # Invalid characters
    invalid_chars = r'[<>:"|?*]'
    if re.search(invalid_chars, file_path):
        issues.append("File path contains invalid characters")

    # Path length
    if len(file_path) > 260:  # Windows MAX_PATH
        issues.append("File path too long (max 260 characters)")

    return issues


def _validate_file_content_security(content: str) -> list[str]:
    """
    Validate file content for basic security issues.

    Args:
        content: File content to validate

    Returns:
        List of security issues
    """
    issues = []

    # Check for potential security issues
    security_patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
        (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret detected"),
        (r"eval\s*\(", "Use of eval() function (potential security risk)"),
        (r"exec\s*\(", "Use of exec() function (potential security risk)"),
    ]

    for pattern, message in security_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(message)

    return issues
