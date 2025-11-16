# app/agents/developer/implementor/tools/shell_tools.py
"""
Safe shell command execution with proper security checks.
Based on OpenSWE's shell tool.
"""

import shlex
import subprocess
from pathlib import Path

from langchain_core.tools import tool

# ============================================================================
# SHELL EXECUTION TOOL
# ============================================================================


@tool
def shell_execute_tool(
    command: str,
    working_directory: str = ".",
    timeout: int = 60,
    allow_dangerous: bool = False,
) -> str:
    """
    Execute a shell command in the working directory.

    SAFETY: By default, blocks dangerous commands (rm, mv, chmod, etc.)
    Set allow_dangerous=True to bypass (use with caution!)

    Args:
        command: Shell command to execute
        working_directory: Directory to execute command in
        timeout: Command timeout in seconds (default: 60)
        allow_dangerous: Whether to allow potentially dangerous commands

    Returns:
        Command output (stdout + stderr)

    Example:
        shell_execute_tool("npm install", working_directory="./frontend")
        shell_execute_tool("pytest tests/", timeout=120)
    """
    try:
        # Resolve working directory
        work_dir = Path(working_directory).resolve()

        if not work_dir.exists():
            return f"Error: Working directory '{working_directory}' does not exist"

        if not work_dir.is_dir():
            return f"Error: '{working_directory}' is not a directory"

        # Safety check: block dangerous commands unless explicitly allowed
        if not allow_dangerous:
            dangerous_patterns = [
                "rm ",
                "rm\t",
                "rm\n",
                "mv ",
                "mv\t",
                "cp ",
                "cp\t",
                "dd ",
                "dd\t",
                "mkfs",
                "format",
                "del ",
                "deltree",
                "chmod ",
                "chown ",
                "sudo ",
                "su ",
                ">",
                ">>",
                "|",  # Redirection and pipes
            ]

            command_lower = command.lower()
            for pattern in dangerous_patterns:
                if pattern in command_lower:
                    return (
                        f"Error: Command contains potentially dangerous operation '{pattern.strip()}'. "
                        f"If you're sure this is safe, set allow_dangerous=True."
                    )

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **subprocess.os.environ,
                # Prevent interactive prompts
                "DEBIAN_FRONTEND": "noninteractive",
                "COREPACK_ENABLE_DOWNLOAD_PROMPT": "0",
            },
        )

        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"

        # Add exit code info
        if result.returncode != 0:
            output = f"Command failed with exit code {result.returncode}\n\n{output}"
        else:
            output = f"Command succeeded (exit code 0)\n\n{output}"

        return output

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


@tool
def shell_execute_safe_tool(
    command: str, working_directory: str = ".", timeout: int = 30
) -> str:
    """
    Execute a READ-ONLY shell command (safe mode).

    Only allows safe, read-only commands like:
    - ls, pwd, cat, head, tail, find
    - git status, git log, git diff
    - npm list, pip list
    - grep, awk, sed (read-only)

    Blocks all write operations.

    Args:
        command: Shell command to execute
        working_directory: Directory to execute command in
        timeout: Command timeout in seconds (default: 30)

    Returns:
        Command output

    Example:
        shell_execute_safe_tool("ls -la", working_directory="./app")
        shell_execute_safe_tool("git status")
    """
    try:
        # Resolve working directory
        work_dir = Path(working_directory).resolve()

        if not work_dir.exists():
            return f"Error: Working directory '{working_directory}' does not exist"

        # Whitelist of safe commands
        safe_commands = [
            "ls",
            "pwd",
            "cat",
            "head",
            "tail",
            "find",
            "tree",
            "git status",
            "git log",
            "git diff",
            "git branch",
            "git show",
            "npm list",
            "npm ls",
            "pip list",
            "pip show",
            "grep",
            "awk",
            "sed",
            "cut",
            "sort",
            "uniq",
            "wc",
            "echo",
            "printf",
            "which",
            "whereis",
            "file",
            "stat",
            "python --version",
            "node --version",
            "npm --version",
        ]

        # Check if command starts with a safe command
        command_parts = shlex.split(command)
        if not command_parts:
            return "Error: Empty command"

        base_command = command_parts[0]

        # Check against whitelist
        is_safe = False
        for safe_cmd in safe_commands:
            if command.startswith(safe_cmd):
                is_safe = True
                break

        if not is_safe:
            return (
                f"Error: Command '{base_command}' is not in the safe commands whitelist. "
                f"Use shell_execute_tool() with allow_dangerous=True if needed."
            )

        # Check for dangerous patterns
        dangerous_patterns = [">", ">>", "|", "&&", "||", ";"]
        for pattern in dangerous_patterns:
            if pattern in command:
                return f"Error: Command contains potentially dangerous operator '{pattern}'"

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"

        if result.returncode != 0:
            output = f"Command failed with exit code {result.returncode}\n\n{output}"

        return output

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def is_command_safe(command: str) -> tuple[bool, str]:
    """
    Check if a command is safe to execute.

    Returns:
        (is_safe, reason)
    """
    dangerous_commands = [
        "rm",
        "mv",
        "cp",
        "dd",
        "mkfs",
        "format",
        "del",
        "deltree",
        "chmod",
        "chown",
        "sudo",
        "su",
        "kill",
        "killall",
    ]

    command_parts = shlex.split(command)
    if not command_parts:
        return False, "Empty command"

    base_command = command_parts[0]

    if base_command in dangerous_commands:
        return False, f"Dangerous command: {base_command}"

    # Check for redirection
    if any(op in command for op in [">", ">>", "|"]):
        return False, "Contains redirection or pipe"

    return True, "Safe"


__all__ = [
    "shell_execute_tool",
    "shell_execute_safe_tool",
    "is_command_safe",
]
