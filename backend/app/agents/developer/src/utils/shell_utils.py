"""Shell execution utilities."""

import os
import re
import subprocess
import time
from typing import List, Dict

DANGEROUS_PATTERNS: List[str] = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r"sudo\s+rm",
    r"mkfs",
    r"dd\s+if=",
    r":\(\)\{.*\};:",
    r"chmod\s+-R\s+777",
    r"chown\s+-R",
    r"curl.*\|\s*sh",
    r"wget.*\|\s*sh",
    r"eval\s*\(",
    r"exec\s*\(",
]


def _is_safe_command(command: str) -> tuple:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Dangerous pattern: {pattern}"
    if ".." in command and ("cd" in command.lower() or "pushd" in command.lower()):
        return False, "Directory traversal detected"
    return True, ""


def run_shell(command: str, working_directory: str, timeout: int = 120) -> Dict:
    """Execute shell command safely."""
    timeout = min(timeout, 600)
    start_time = time.time()
    
    is_safe, reason = _is_safe_command(command)
    if not is_safe:
        return {"status": "blocked", "exit_code": -1, "stdout": "", 
                "stderr": f"Command blocked: {reason}", "execution_time": 0}
    
    work_dir = os.path.realpath(working_directory)
    if not os.path.exists(work_dir):
        return {"status": "error", "exit_code": -1, "stdout": "",
                "stderr": f"Directory not found: {work_dir}"}
    
    try:
        result = subprocess.run(
            ["cmd", "/c", command], cwd=str(work_dir), shell=False,
            capture_output=True, text=True, timeout=timeout,
            encoding='utf-8', errors='replace',
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": round(time.time() - start_time, 2),
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "exit_code": -1, "stdout": "",
                "stderr": f"Timed out after {timeout}s",
                "execution_time": round(time.time() - start_time, 2)}
    except Exception as e:
        return {"status": "error", "exit_code": -1, "stdout": "",
                "stderr": str(e)}
