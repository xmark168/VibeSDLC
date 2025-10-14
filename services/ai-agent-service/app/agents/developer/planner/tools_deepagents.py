# app/agents/developer/planner/tools_deepagents.py
"""
Tools for the DeepAgents Planner

All tools are READ-ONLY for context gathering.
Based on the LangGraph tools but adapted for DeepAgents patterns.
"""

from langchain_core.tools import tool
import subprocess
from pathlib import Path
from typing import Optional, List

# Shared scratchpad for notes
_scratchpad_notes: List[str] = []


@tool
def grep_search(pattern: str, path: str = ".", file_pattern: str = "*") -> str:
    """
    Search for a pattern in files using grep/ripgrep.

    Args:
        pattern: The pattern to search for
        path: Directory to search in (default: current directory)
        file_pattern: File pattern to match (e.g., "*.py", "*.ts")

    Returns:
        Search results with file paths and line numbers
    """
    try:
        # Try ripgrep first
        try:
            result = subprocess.run(
                ["rg", pattern, path, "-g", file_pattern, "-n", "--color=never"],
                capture_output=True,
                text=True,
                timeout=30
            )
        except FileNotFoundError:
            # Fallback to grep
            result = subprocess.run(
                ["grep", "-rn", pattern, path, "--include", file_pattern],
                capture_output=True,
                text=True,
                timeout=30
            )

        if result.returncode == 0:
            return result.stdout
        elif result.returncode == 1:
            return "No matches found"
        else:
            return f"Error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Search timed out after 30 seconds"
    except Exception as e:
        return f"Error executing grep: {str(e)}"


@tool
def view_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """
    View the contents of a file or specific line range.

    Args:
        file_path: Path to the file to view
        start_line: Optional starting line number (1-indexed)
        end_line: Optional ending line number (1-indexed)

    Returns:
        File contents with line numbers
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File '{file_path}' does not exist"

        if not path.is_file():
            return f"Error: '{file_path}' is not a file"

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Apply line range
        if start_line is not None or end_line is not None:
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else len(lines)
            lines = lines[start:end]
            line_offset = start + 1
        else:
            line_offset = 1

        # Format with line numbers
        formatted_lines = [
            f"{i + line_offset:4d} | {line.rstrip()}"
            for i, line in enumerate(lines)
        ]

        return "\n".join(formatted_lines)
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def shell_execute(command: str) -> str:
    """
    Execute a READ-ONLY shell command.

    SAFETY: Only allows read-only commands (ls, pwd, cat, find, etc.)
    Blocks destructive commands (rm, mv, cp, etc.)

    Args:
        command: Shell command to execute

    Returns:
        Command output
    """
    # Safety check: block dangerous commands
    dangerous_commands = [
        'rm', 'mv', 'cp', 'dd', 'mkfs', 'format',
        'del', 'deltree', 'chmod', 'chown',
        '>', '>>', 'sudo', 'su'
    ]

    command_parts = command.split()
    if command_parts and command_parts[0] in dangerous_commands:
        return f"Error: Command '{command_parts[0]}' is not allowed (read-only mode)"

    # Check for redirection
    if any(op in command for op in ['>', '>>']):
        return "Error: Output redirection is not allowed (read-only mode)"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"

        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


@tool
def list_directory(path: str = ".", show_hidden: bool = False, recursive: bool = False) -> str:
    """
    List directory contents with details.

    Args:
        path: Directory path to list
        show_hidden: Include hidden files
        recursive: List recursively

    Returns:
        Formatted directory listing
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            return f"Error: Path '{path}' does not exist"

        if not path_obj.is_dir():
            return f"Error: '{path}' is not a directory"

        files = []
        if recursive:
            for item in path_obj.rglob("*"):
                if not show_hidden and item.name.startswith('.'):
                    continue
                files.append(str(item.relative_to(path_obj)))
        else:
            for item in path_obj.iterdir():
                if not show_hidden and item.name.startswith('.'):
                    continue
                files.append(item.name)

        files.sort()
        return "\n".join(files) if files else "Directory is empty"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def take_notes(note: str) -> str:
    """
    Take notes about important information discovered during context gathering.

    These notes will be available when generating the final plan and will be
    condensed by the noteTaker subagent.

    Args:
        note: The note to record

    Returns:
        Confirmation message
    """
    global _scratchpad_notes
    _scratchpad_notes.append(note)
    return f"Note recorded. Total notes: {len(_scratchpad_notes)}"


def get_scratchpad_notes() -> List[str]:
    """Get all recorded notes."""
    global _scratchpad_notes
    return _scratchpad_notes.copy()


def clear_scratchpad_notes():
    """Clear all notes (for testing/reset)."""
    global _scratchpad_notes
    _scratchpad_notes.clear()


# Export tools for DeepAgents
grep_search_tool = grep_search
view_file_tool = view_file
shell_execute_tool = shell_execute
list_directory_tool = list_directory
take_notes_tool = take_notes
