# app/agents/developer/implementor/tools/filesystem_tools.py
"""
Direct Filesystem Tools (OpenSWE-style)

These tools interact directly with the real filesystem, replacing DeepAgents' Virtual FS.
Based on OpenSWE's text-editor, view, grep, and shell tools.

REFACTORED: Now uses Adapter Pattern to support both local and Daytona sandbox modes.
"""

import json
from pathlib import Path

from langchain_core.tools import tool

# Import filesystem adapter for local/Daytona mode switching

# ============================================================================
# FILE READING TOOLS
# ============================================================================


@tool
def read_file_tool(
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
    working_directory: str = ".",
) -> str:
    """
    Read a file from disk with optional line range.

    Args:
        file_path: Path to file (relative to working_directory)
        start_line: Starting line number (1-based, inclusive)
        end_line: Ending line number (1-based, inclusive)
        working_directory: Base directory for relative paths

    Returns:
        File contents with line numbers (cat -n format)

    Example:
        read_file_tool("app/main.py", start_line=10, end_line=20)
    """
    # REFACTORED: Use adapter pattern for local/Daytona mode switching
    from ...daytona_integration.adapters import get_filesystem_adapter

    adapter = get_filesystem_adapter()
    return adapter.read_file(file_path, start_line, end_line, working_directory)


@tool
def list_files_tool(
    directory: str = ".",
    pattern: str = "*",
    recursive: bool = False,
    working_directory: str = ".",
) -> str:
    """
    List files in a directory with optional glob pattern.

    Args:
        directory: Directory to list (relative to working_directory)
        pattern: Glob pattern (e.g., "*.py", "**/*.ts")
        recursive: Whether to search recursively
        working_directory: Base directory for relative paths

    Returns:
        List of files matching pattern

    Example:
        list_files_tool("app", pattern="*.py", recursive=True)
    """
    # REFACTORED: Use adapter pattern for local/Daytona mode switching
    from ...daytona_integration.adapters import get_filesystem_adapter

    adapter = get_filesystem_adapter()
    return adapter.list_files(directory, pattern, recursive, working_directory)


# ============================================================================
# FILE WRITING TOOLS
# ============================================================================


@tool
def write_file_tool(
    file_path: str, content: str, working_directory: str = ".", create_dirs: bool = True
) -> str:
    """
    Write content to a file on disk (creates new file or overwrites existing).

    Args:
        file_path: Path to file (relative to working_directory)
        content: Content to write
        working_directory: Base directory for relative paths
        create_dirs: Whether to create parent directories if they don't exist

    Returns:
        Success message or error

    Example:
        write_file_tool("app/routes/profile.py", "from fastapi import APIRouter\\n...")
    """
    # REFACTORED: Use adapter pattern for local/Daytona mode switching
    from ...daytona_integration.adapters import get_filesystem_adapter

    adapter = get_filesystem_adapter()
    return adapter.write_file(file_path, content, working_directory, create_dirs)


@tool
def str_replace_tool(
    file_path: str,
    old_str: str,
    new_str: str,
    working_directory: str = ".",
    replace_all: bool = False,
) -> str:
    """
    Edit a file by replacing old_str with new_str (str_replace pattern).

    Args:
        file_path: Path to file (relative to working_directory)
        old_str: String to search for (must match exactly)
        new_str: String to replace with
        working_directory: Base directory for relative paths
        replace_all: Whether to replace all occurrences (default: first only)

    Returns:
        Success message or error

    Example:
        str_replace_tool(
            "app/main.py",
            old_str="from app.routes import users",
            new_str="from app.routes import users, profile"
        )
    """
    # REFACTORED: Use adapter pattern for local/Daytona mode switching
    from ...daytona_integration.adapters import get_filesystem_adapter

    adapter = get_filesystem_adapter()
    return adapter.edit_file(
        file_path, old_str, new_str, working_directory, replace_all
    )


# ============================================================================
# SEARCH TOOLS
# ============================================================================


@tool
def grep_search_tool(
    pattern: str,
    directory: str = ".",
    file_pattern: str = "*",
    case_sensitive: bool = False,
    context_lines: int = 0,
    working_directory: str = ".",
) -> str:
    """
    Search for a pattern in files using grep/ripgrep.

    Args:
        pattern: Pattern to search for (regex supported)
        directory: Directory to search in (relative to working_directory)
        file_pattern: File glob pattern (e.g., "*.py", "*.ts")
        case_sensitive: Whether search is case-sensitive
        context_lines: Number of context lines before/after match
        working_directory: Base directory for relative paths

    Returns:
        Search results with file paths and line numbers

    Example:
        grep_search_tool("def authenticate", directory="app", file_pattern="*.py")
    """
    # REFACTORED: Use adapter pattern for local/Daytona mode switching
    from ...daytona_integration.adapters import get_filesystem_adapter

    adapter = get_filesystem_adapter()
    return adapter.grep_search(
        pattern,
        directory,
        file_pattern,
        case_sensitive,
        context_lines,
        working_directory,
    )


@tool
def create_directory_tool(
    directory_path: str, working_directory: str = ".", parents: bool = True
) -> str:
    """
    Create a directory (and parent directories if needed).

    Args:
        directory_path: Directory to create
        working_directory: Base directory
        parents: Create parent directories

    Example:
        create_directory_tool("app/routes/v1")
    """
    # REFACTORED: Use adapter pattern for local/Daytona mode switching
    from ...daytona_integration.adapters import get_filesystem_adapter

    adapter = get_filesystem_adapter()
    # Note: adapter.create_directory returns JSON, but this tool returns plain text
    # So we need to parse and format the response
    result = adapter.create_directory(directory_path, working_directory, mode="755")

    # Parse JSON result and return plain text for backward compatibility
    try:
        result_dict = json.loads(result)
        if result_dict.get("status") == "success":
            return f"Successfully created directory: {directory_path}"
        else:
            return f"Error creating directory: {result_dict.get('message', 'Unknown error')}"
    except:
        # If result is already plain text, return as is
        return result


@tool
def list_directory_tree_tool(
    directory: str = ".", max_depth: int = 3, working_directory: str = "."
) -> str:
    """
    Show directory tree structure.

    Args:
        directory: Directory to show
        max_depth: Maximum depth to display
        working_directory: Base directory

    Example:
        list_directory_tree_tool("app", max_depth=2)
    """
    try:
        base_path = Path(working_directory) / directory
        base_path = base_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(base_path).startswith(str(working_dir_resolved)):
            return "Error: Access denied - path outside working directory"

        if not base_path.exists():
            return f"Directory not found: {directory}"

        def build_tree(path: Path, current_depth: int = 0, prefix: str = ""):
            if current_depth > max_depth:
                return ""

            tree_str = ""
            if path.is_dir():
                # Add directory entry
                tree_str += f"{prefix}{path.name}/\n"

                # Get contents (directories first, then files)
                try:
                    items = sorted(
                        path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
                    )

                    for i, item in enumerate(items):
                        is_last = i == len(items) - 1
                        new_prefix = prefix + ("└── " if is_last else "├── ")

                        if item.is_dir():
                            tree_str += build_tree(item, current_depth + 1, new_prefix)
                        else:
                            tree_str += f"{new_prefix}{item.name}\n"
                except PermissionError:
                    tree_str += f"{prefix}└── [Permission denied]\n"

            return tree_str

        return f"Directory tree for {directory}:\n" + build_tree(base_path)

    except Exception as e:
        return f"Error building directory tree: {str(e)}"


@tool
def batch_edit_files_tool(file_edits: list[dict], working_directory: str = ".") -> str:
    """
    Apply multiple file edits in one operation.

    Args:
        file_edits: List of edit operations
        working_directory: Base directory

    Example:
        batch_edit_files_tool([
            {
                "file_path": "app/main.py",
                "old_str": "from fastapi import FastAPI",
                "new_str": "from fastapi import FastAPI, Depends"
            },
            {
                "file_path": "requirements.txt",
                "old_str": "fastapi==0.68.0",
                "new_str": "fastapi==0.100.0"
            }
        ])
    """
    results = []
    for i, edit in enumerate(file_edits):
        result = str_replace_tool(
            file_path=edit["file_path"],
            old_str=edit["old_str"],
            new_str=edit["new_str"],
            working_directory=working_directory,
            replace_all=edit.get("replace_all", False),
        )
        results.append(f"Edit {i + 1}: {result}")

    return "\n".join(results)


__all__ = [
    # File Reading
    "read_file_tool",
    "list_files_tool",
    # File Writing
    "write_file_tool",
    "str_replace_tool",
    # Directory Operations
    "create_directory_tool",
    "list_directory_tree_tool",
    # Search
    "grep_search_tool",
    # Batch Operations
    "batch_edit_files_tool",
]
