# app/agents/developer/implementor/tools/filesystem_tools.py
"""
Direct Filesystem Tools (OpenSWE-style)

These tools interact directly with the real filesystem, replacing DeepAgents' Virtual FS.
Based on OpenSWE's text-editor, view, grep, and shell tools.
"""

import json
import subprocess
from pathlib import Path

from langchain_core.tools import tool

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
    try:
        # Resolve full path
        full_path = Path(working_directory) / file_path

        # Security check: prevent path traversal
        full_path = full_path.resolve()
        working_dir_resolved = Path(working_directory).resolve()
        if not str(full_path).startswith(str(working_dir_resolved)):
            return "Error: Access denied - path outside working directory"

        # Check file exists
        if not full_path.exists():
            return f"Error: File '{file_path}' does not exist"

        if not full_path.is_file():
            return f"Error: '{file_path}' is not a file"

        # Read file
        with open(full_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # Apply line range
        if start_line is not None or end_line is not None:
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else len(lines)
            lines = lines[start:end]
            line_offset = start + 1
        else:
            line_offset = 1

        # Format with line numbers (cat -n format)
        formatted_lines = [
            f"{i + line_offset:6d}\t{line.rstrip()}" for i, line in enumerate(lines)
        ]

        return "\n".join(formatted_lines)

    except PermissionError:
        return f"Error: Permission denied reading '{file_path}'"
    except Exception as e:
        return f"Error reading file: {str(e)}"


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
    try:
        # Resolve full path
        full_path = Path(working_directory) / directory
        full_path = full_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(full_path).startswith(str(working_dir_resolved)):
            return "Error: Access denied - path outside working directory"

        # Check directory exists
        if not full_path.exists():
            return f"Error: Directory '{directory}' does not exist"

        if not full_path.is_dir():
            return f"Error: '{directory}' is not a directory"

        # List files
        if recursive:
            files = list(full_path.rglob(pattern))
        else:
            files = list(full_path.glob(pattern))

        # Filter only files (not directories)
        files = [f for f in files if f.is_file()]

        # Make paths relative to working_directory
        relative_files = [str(f.relative_to(working_dir_resolved)) for f in files]

        if not relative_files:
            return f"No files found matching pattern '{pattern}' in '{directory}'"

        return "\n".join(sorted(relative_files))

    except Exception as e:
        return f"Error listing files: {str(e)}"


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
    try:
        # Resolve full path
        full_path = Path(working_directory) / file_path
        full_path = full_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(full_path).startswith(str(working_dir_resolved)):
            return json.dumps(
                {
                    "status": "error",
                    "message": "Access denied - path outside working directory",
                }
            )

        # Create parent directories if needed
        if create_dirs:
            full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        full_path.write_text(content, encoding="utf-8")

        lines_count = content.count("\n") + 1
        bytes_count = len(content.encode("utf-8"))

        return json.dumps(
            {
                "status": "success",
                "message": f"Successfully wrote {lines_count} lines ({bytes_count} bytes) to '{file_path}'",
            }
        )

    except PermissionError:
        return json.dumps(
            {
                "status": "error",
                "message": f"Permission denied writing to '{file_path}'",
            }
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error writing file: {str(e)}"}
        )


@tool
def edit_file_tool(
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
        edit_file_tool(
            "app/main.py",
            old_str="from app.routes import users",
            new_str="from app.routes import users, profile"
        )
    """
    try:
        # Resolve full path
        full_path = Path(working_directory) / file_path
        full_path = full_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(full_path).startswith(str(working_dir_resolved)):
            return json.dumps(
                {
                    "status": "error",
                    "message": "Access denied - path outside working directory",
                }
            )

        # Check file exists
        if not full_path.exists():
            return json.dumps(
                {"status": "error", "message": f"File '{file_path}' does not exist"}
            )

        # Read current content
        content = full_path.read_text(encoding="utf-8")

        # Check if old_str exists
        if old_str not in content:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"String not found in file: '{old_str[:100]}...'",
                }
            )

        # Check for multiple occurrences if not replace_all
        occurrences = content.count(old_str)
        if not replace_all and occurrences > 1:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"String appears {occurrences} times in file. "
                    f"Use replace_all=True to replace all instances, or provide a more specific string.",
                }
            )

        # Perform replacement
        if replace_all:
            new_content = content.replace(old_str, new_str)
            result_msg = (
                f"Successfully replaced {occurrences} occurrence(s) in '{file_path}'"
            )
        else:
            new_content = content.replace(old_str, new_str, 1)
            result_msg = f"Successfully replaced 1 occurrence in '{file_path}'"

        # Write back
        full_path.write_text(new_content, encoding="utf-8")

        return json.dumps({"status": "success", "message": result_msg})

    except PermissionError:
        return json.dumps(
            {"status": "error", "message": f"Permission denied editing '{file_path}'"}
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error editing file: {str(e)}"}
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
    try:
        # Resolve full path
        search_path = Path(working_directory) / directory
        search_path = search_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(search_path).startswith(str(working_dir_resolved)):
            return "Error: Access denied - path outside working directory"

        # Try ripgrep first (faster)
        try:
            cmd = ["rg", pattern, str(search_path), "-n", "--color=never"]

            if not case_sensitive:
                cmd.append("-i")

            if context_lines > 0:
                cmd.extend(["-C", str(context_lines)])

            if file_pattern != "*":
                cmd.extend(["-g", file_pattern])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        except FileNotFoundError:
            # Fallback to grep
            cmd = ["grep", "-rn"]

            if not case_sensitive:
                cmd.append("-i")

            if context_lines > 0:
                cmd.extend(["-C", str(context_lines)])

            cmd.append(pattern)
            cmd.append(str(search_path))

            if file_pattern != "*":
                cmd.extend(["--include", file_pattern])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return result.stdout
        elif result.returncode == 1:
            return f"No matches found for pattern '{pattern}'"
        else:
            return f"Error: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "Error: Search timed out after 30 seconds"
    except Exception as e:
        return f"Error executing grep: {str(e)}"


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
    try:
        full_path = Path(working_directory) / directory_path
        full_path = full_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(full_path).startswith(str(working_dir_resolved)):
            return "Error: Access denied - path outside working directory"

        full_path.mkdir(parents=parents, exist_ok=True)
        return f"Successfully created directory: {directory_path}"

    except Exception as e:
        return f"Error creating directory: {str(e)}"


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
        result = edit_file_tool(
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
    "edit_file_tool",
    # Directory Operations
    "create_directory_tool",
    "list_directory_tree_tool",
    # Search
    "grep_search_tool",
    # Batch Operations
    "batch_edit_files_tool",
]
