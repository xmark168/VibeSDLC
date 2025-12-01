"""Shell and Search Tools using LangChain @tool decorator."""

import json
import os
import re
import subprocess
import time
from typing import  List
from langchain_core.tools import tool

# Global context
_shell_context = {
    "root_dir": None,
}


def set_shell_context(root_dir: str = None):
    """Set global context for shell tools."""
    if root_dir:
        _shell_context["root_dir"] = root_dir


def _get_root_dir() -> str:
    """Get root directory from context or use cwd."""
    return _shell_context.get("root_dir") or os.getcwd()


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
            env=os.environ.copy(),
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


@tool
def web_search_ddg(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo.

    Args:
        query: Search query
        max_results: Maximum number of results to return
    """
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        if not results:
            return f"No results found for query: {query}"
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"{i}. {result.get('title', 'No title')}\n"
                f"   URL: {result.get('href', 'No URL')}\n"
                f"   Snippet: {result.get('body', 'No description')}\n"
            )
        
        return "\n".join(formatted_results)
    
    except ImportError:
        return "Error: duckduckgo-search not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"Error performing web search: {str(e)}"


@tool
def semantic_code_search(query: str, top_k: int = 5) -> str:
    """Search codebase using semantic search via CocoIndex.

    Args:
        query: Natural language query (e.g., 'authentication logic', 'React components')
        top_k: Number of results to return
    """
    try:
        from app.agents.developer.project_manager import project_manager
        from app.agents.developer_v2.src.tools.cocoindex_tools import _tool_context
        
        project_id = _tool_context.get("project_id")
        task_id = _tool_context.get("task_id")
        
        if not project_id:
            return "Error: project_id not set in tool context"
        
        if task_id:
            results = project_manager.search_task(project_id, task_id, query, top_k=top_k)
            context = f"task '{task_id}' in project '{project_id}'"
        else:
            results = project_manager.search(project_id, query, top_k=top_k)
            context = f"project '{project_id}'"
        
        if not results:
            return f"No results found in {context} for query: '{query}'"
        
        formatted_output = [f"Code search results for '{query}' in {context}:\n"]
        for i, result in enumerate(results, 1):
            score_pct = int(result.get("score", 0) * 100)
            formatted_output.append(
                f"{i}. {result['filename']} (Relevance: {score_pct}%)\n"
                f"---\n{result['code']}\n---"
            )
        return "\n".join(formatted_output)
    
    except ImportError as e:
        return f"Error: Required module not available: {str(e)}"
    except Exception as e:
        return f"Error performing semantic search: {str(e)}"
