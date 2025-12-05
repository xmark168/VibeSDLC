"""Shell Tools using LangChain @tool decorator."""

import json
import os
import re
import subprocess
import time
from typing import List, Dict
from langchain_core.tools import tool

from ._base_context import get_root_dir, get_shell_env, set_tool_context


# Backward compatibility alias
def set_shell_context(root_dir: str = None):
    """Set shell context. Delegates to unified set_tool_context."""
    set_tool_context(root_dir=root_dir)


# Dangerous command patterns to block
DANGEROUS_PATTERNS: List[str] = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r"sudo\s+rm",
    r"mkfs",
    r"dd\s+if=",
    r":\(\)\{.*\};:",  # Fork bomb
    r"chmod\s+-R\s+777",
    r"chown\s+-R",
    r"curl.*\|\s*sh",
    r"wget.*\|\s*sh",
    r"eval\s*\(",
    r"exec\s*\(",
]


def _is_safe_command(command: str) -> tuple:
    """Check if command is safe to execute."""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Dangerous command pattern detected: {pattern}"
    if ".." in command and ("cd" in command.lower() or "pushd" in command.lower()):
        return False, "Directory traversal detected"
    return True, ""


def run_shell(command: str, working_directory: str = ".", timeout: int = 120) -> Dict:
    """Core shell execution - returns dict. Used by both @tool and direct calls."""
    timeout = min(timeout, 600)
    root_dir = get_root_dir()
    start_time = time.time()
    
    is_safe, reason = _is_safe_command(command)
    if not is_safe:
        return {"status": "blocked", "exit_code": -1, "stdout": "", 
                "stderr": f"Command blocked: {reason}", "execution_time": 0, "command": command}
    
    if not os.path.isabs(working_directory):
        work_dir = os.path.join(root_dir, working_directory)
    else:
        work_dir = working_directory
    
    work_dir = os.path.realpath(work_dir)
    if not work_dir.startswith(os.path.realpath(root_dir)):
        work_dir = root_dir
    if not os.path.exists(work_dir):
        work_dir = root_dir
    
    try:
        result = subprocess.run(
            ["cmd", "/c", command], cwd=str(work_dir), shell=False,
            capture_output=True, text=True, timeout=timeout,
            env=get_shell_env(), encoding='utf-8', errors='replace',
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": round(time.time() - start_time, 2),
            "command": command,
            "working_directory": str(work_dir),
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "exit_code": -1, "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "execution_time": round(time.time() - start_time, 2), "command": command}
    except FileNotFoundError as e:
        return {"status": "error", "exit_code": -1, "stdout": "",
                "stderr": f"Command not found: {str(e)}", "command": command}
    except Exception as e:
        return {"status": "error", "exit_code": -1, "stdout": "",
                "stderr": f"Unexpected error: {str(e)}", "command": command}


@tool
def execute_shell(command: str, working_directory: str = ".", timeout: int = 120, description: str = "") -> str:
    """Execute a shell command safely within project root.

    Args:
        command: Shell command to execute (e.g., 'bun install', 'bun test')
        working_directory: Directory to run command in, relative to project root
        timeout: Maximum execution time in seconds (default 120, max 600)
        description: What this command does in 5-10 words (e.g., "Run unit tests")
    
    IMPORTANT:
    - NEVER use grep, find, cat → use glob, grep_files, read_file_safe instead
    - Prefer absolute paths over cd
    - For long builds, set timeout up to 600
    """
    return json.dumps(run_shell(command, working_directory, timeout), indent=2)

