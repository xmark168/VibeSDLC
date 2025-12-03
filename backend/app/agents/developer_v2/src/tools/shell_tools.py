"""Shell and Search Tools using LangChain @tool decorator."""

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import List
from langchain_core.tools import tool

# Global context
_shell_context = {
    "root_dir": None,
}

# Shared bun cache directory
_bun_cache_dir = None


def set_shell_context(root_dir: str = None):
    """Set global context for shell tools."""
    if root_dir:
        _shell_context["root_dir"] = root_dir


def _get_root_dir() -> str:
    """Get root directory from context or use cwd."""
    return _shell_context.get("root_dir") or os.getcwd()


def _get_shared_bun_cache() -> str:
    """Get shared bun cache directory path."""
    global _bun_cache_dir
    if _bun_cache_dir is None:
        # backend/projects/.bun-cache
        current_file = Path(__file__).resolve()
        backend_root = current_file.parent.parent.parent.parent.parent
        cache_dir = backend_root / "projects" / ".bun-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        _bun_cache_dir = str(cache_dir)
    return _bun_cache_dir


def _get_shell_env() -> dict:
    """Get environment with shared bun cache."""
    env = os.environ.copy()
    env["BUN_INSTALL_CACHE_DIR"] = _get_shared_bun_cache()
    return env


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


@tool
def execute_shell(command: str, working_directory: str = ".", timeout: int = 60) -> str:
    """Execute a shell command safely within project root.

    Args:
        command: Shell command to execute (e.g., 'npm install', 'python script.py')
        working_directory: Directory to run command in, relative to project root
        timeout: Maximum execution time in seconds
    """
    root_dir = _get_root_dir()
    start_time = time.time()
    
    # Safety check
    is_safe, reason = _is_safe_command(command)
    if not is_safe:
        return json.dumps({
            "status": "blocked",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command blocked: {reason}",
            "execution_time": 0,
            "command": command,
        }, indent=2)
    
    # Normalize working directory
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
        if os.name == "nt":  # Windows
            shell_cmd = ["cmd", "/c", command]
            use_shell = False
        else:  
            shell_cmd = command
            use_shell = True
        
        result = subprocess.run(
            shell_cmd,
            cwd=str(work_dir),
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_get_shell_env(),  # Use shared bun cache
            encoding='utf-8',
            errors='replace',
        )
        
        execution_time = time.time() - start_time
        
        return json.dumps({
            "status": "success" if result.returncode == 0 else "error",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": round(execution_time, 2),
            "command": command,
            "working_directory": str(work_dir),
        }, indent=2)
    
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        return json.dumps({
            "status": "timeout",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "execution_time": round(execution_time, 2),
            "command": command,
        }, indent=2)
    
    except FileNotFoundError as e:
        return json.dumps({
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command not found: {str(e)}",
            "command": command,
        }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
            "command": command,
        }, indent=2)



