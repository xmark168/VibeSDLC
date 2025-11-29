"""Developer V2 Tools for code operations."""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# =============================================================================
# COCOINDEX SEMANTIC SEARCH (from Developer V1)
# =============================================================================

def search_codebase(
    project_id: str,
    query: str,
    top_k: int = 5,
    task_id: str = None
) -> str:
    """Search codebase using CocoIndex semantic search.
    
    Uses the existing CocoIndex infrastructure from Developer V1 to perform
    semantic search over indexed code. Much more efficient than importing
    all files into context.
    
    Args:
        project_id: Project identifier
        query: Natural language query (e.g., "authentication logic", "user model")
        top_k: Number of results to return (default: 5)
        task_id: Optional task ID for task-specific search
        
    Returns:
        Markdown-formatted code snippets with relevance scores
    """
    try:
        from app.agents.developer.project_manager import project_manager
        
        if task_id:
            results = project_manager.search_task(project_id, task_id, query, top_k=top_k)
        else:
            results = project_manager.search(project_id, query, top_k=top_k)
        
        if not results:
            return "No relevant code found."
        
        # Format results as markdown
        formatted = []
        for r in results:
            score_pct = int(r.get("score", 0) * 100)
            code_type = get_markdown_code_block_type(r['filename'])
            formatted.append(
                f"### {r['filename']} (Relevance: {score_pct}%)\n"
                f"```{code_type}\n{r['code']}\n```\n"
            )
        
        return "\n".join(formatted)
        
    except ImportError as e:
        logger.warning(f"CocoIndex not available, falling back to file import: {e}")
        return "CocoIndex not available. Using fallback."
    except Exception as e:
        logger.error(f"Codebase search error: {e}")
        return f"Search error: {str(e)}"


def index_workspace(project_id: str, workspace_path: str, task_id: str = None) -> bool:
    """Index workspace using CocoIndex.
    
    Creates vector embeddings for all source files in the workspace,
    enabling fast semantic search later.
    
    Args:
        project_id: Project identifier
        workspace_path: Path to workspace directory
        task_id: Optional task ID for task-specific indexing
        
    Returns:
        True if indexing successful, False otherwise
    """
    try:
        from app.agents.developer.project_manager import project_manager
        
        if task_id:
            project_manager.register_task(project_id, task_id, workspace_path)
            logger.info(f"Indexed task workspace: {project_id}/{task_id}")
        else:
            project_manager.register_project(project_id, workspace_path)
            logger.info(f"Indexed project workspace: {project_id}")
        return True
    except ImportError as e:
        logger.warning(f"CocoIndex not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        return False


async def update_workspace_index(project_id: str, task_id: str = None) -> bool:
    """Re-index workspace after code changes.
    
    Should be called after implementing code changes to keep
    the search index up-to-date.
    
    Args:
        project_id: Project identifier
        task_id: Optional task ID for task-specific update
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        from app.agents.developer.project_manager import project_manager
        
        if task_id:
            await project_manager.update_task(project_id, task_id)
            logger.info(f"Updated task index: {project_id}/{task_id}")
        else:
            await project_manager.update_project(project_id)
            logger.info(f"Updated project index: {project_id}")
        return True
    except ImportError as e:
        logger.warning(f"CocoIndex not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Index update error: {e}")
        return False


def get_related_code_indexed(
    project_id: str,
    current_file: str,
    task_description: str,
    top_k: int = 5,
    task_id: str = None
) -> str:
    """Get related code context using CocoIndex semantic search.
    
    Replacement for get_related_code_context() that uses semantic search
    instead of importing all files. Much more efficient for large codebases.
    
    Args:
        project_id: Project identifier
        current_file: File being implemented (for context)
        task_description: Description of what's being implemented
        top_k: Number of relevant chunks to retrieve
        task_id: Optional task ID for task-specific search
        
    Returns:
        Markdown-formatted related code snippets
    """
    # Build semantic query from task context
    query = f"{task_description} related to {current_file}"
    
    return search_codebase(
        project_id=project_id,
        query=query,
        top_k=top_k,
        task_id=task_id
    )


# =============================================================================
# CODE CONTEXT UTILITIES (MetaGPT-inspired) - Fallback when CocoIndex unavailable
# =============================================================================

def get_markdown_code_block_type(filename: str) -> str:
    """Get markdown code block type from filename extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        Markdown code block language identifier
    """
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".sh": "bash",
        ".md": "markdown",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
    }
    ext = Path(filename).suffix.lower()
    return ext_map.get(ext, "")


def get_related_code_context(
    workspace_path: str,
    current_file: str,
    task_files: List[str],
    include_all_src: bool = False
) -> str:
    """Gather related code files for context (MetaGPT-style).
    
    This function collects code from related files to provide context
    when implementing a specific file. It marks the current file as
    "file to rewrite" and other files as "existing files".
    
    Args:
        workspace_path: Path to the workspace directory
        current_file: The file currently being implemented (to exclude from context)
        task_files: List of files related to the current task
        include_all_src: If True, include all source files in workspace
        
    Returns:
        Markdown-formatted code snippets of related files
    """
    context_parts = []
    workspace = Path(workspace_path)
    
    # Collect files to include
    files_to_include = set(task_files)
    
    # Optionally include all source files
    if include_all_src:
        for ext in [".py", ".js", ".ts", ".tsx", ".jsx"]:
            for file_path in workspace.rglob(f"*{ext}"):
                # Skip common non-source directories
                if any(part in file_path.parts for part in 
                       ["node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build"]):
                    continue
                rel_path = str(file_path.relative_to(workspace))
                files_to_include.add(rel_path)
    
    # Process each file
    for file in files_to_include:
        file_path = workspace / file
        
        if not file_path.exists():
            continue
            
        try:
            content = file_path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, PermissionError, IOError):
            continue
            
        code_type = get_markdown_code_block_type(file)
        
        if file == current_file:
            # Mark as file to rewrite (insert at beginning)
            context_parts.insert(
                0,
                f"### File to rewrite: `{file}`\n```{code_type}\n{content}\n```\n"
            )
            logger.info(f"Prepare to rewrite `{file}`")
        else:
            # Include as existing file
            context_parts.append(
                f"### File: `{file}`\n```{code_type}\n{content}\n```\n"
            )
    
    return "\n".join(context_parts) if context_parts else "No related files found."


def get_legacy_code(workspace_path: str, exclude_files: Optional[List[str]] = None) -> str:
    """Get all existing source code from workspace (MetaGPT-style).
    
    Used for incremental development to show all existing code.
    
    Args:
        workspace_path: Path to the workspace directory
        exclude_files: Files to exclude from the output
        
    Returns:
        Markdown-formatted code of all source files
    """
    workspace = Path(workspace_path)
    exclude_files = exclude_files or []
    code_parts = []
    
    source_extensions = [".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go"]
    skip_dirs = {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build", ".pytest_cache"}
    
    for ext in source_extensions:
        for file_path in workspace.rglob(f"*{ext}"):
            # Skip excluded directories
            if any(part in file_path.parts for part in skip_dirs):
                continue
                
            rel_path = str(file_path.relative_to(workspace))
            
            # Skip excluded files
            if rel_path in exclude_files:
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8')
                code_type = get_markdown_code_block_type(rel_path)
                code_parts.append(
                    f"### File: `{rel_path}`\n```{code_type}\n{content}\n```\n"
                )
            except (UnicodeDecodeError, PermissionError, IOError):
                continue
    
    return "\n".join(code_parts) if code_parts else "No existing code found."


def format_code_for_context(file_path: str, content: str, is_target: bool = False) -> str:
    """Format a single file's code for inclusion in context.
    
    Args:
        file_path: Path to the file
        content: File content
        is_target: If True, mark as file to be written/modified
        
    Returns:
        Markdown-formatted code block
    """
    code_type = get_markdown_code_block_type(file_path)
    header = "### File to rewrite:" if is_target else "### File:"
    return f"{header} `{file_path}`\n```{code_type}\n{content}\n```\n"


@tool
def read_file(file_path: str) -> str:
    """Read contents of a file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        File contents as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file.
    
    Args:
        file_path: Path to the file to write
        content: Content to write
        
    Returns:
        Success message or error
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def list_directory(directory_path: str) -> str:
    """List contents of a directory.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        List of files and directories
    """
    import os
    try:
        items = os.listdir(directory_path)
        return "\n".join(items)
    except FileNotFoundError:
        return f"Error: Directory not found: {directory_path}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def search_in_files(directory: str, pattern: str, file_extension: Optional[str] = None) -> str:
    """Search for a pattern in files within a directory.
    
    Args:
        directory: Directory to search in
        pattern: Pattern to search for
        file_extension: Optional file extension filter (e.g., '.py')
        
    Returns:
        Matching files and lines
    """
    import os
    import re
    
    results = []
    try:
        for root, _, files in os.walk(directory):
            for file in files:
                if file_extension and not file.endswith(file_extension):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            if re.search(pattern, line):
                                results.append(f"{file_path}:{i}: {line.strip()}")
                except (UnicodeDecodeError, PermissionError):
                    continue
                    
        return "\n".join(results) if results else "No matches found"
    except Exception as e:
        return f"Error searching: {str(e)}"


@tool
def get_file_info(file_path: str) -> str:
    """Get information about a file (size, modified time, etc.).
    
    Args:
        file_path: Path to the file
        
    Returns:
        File information
    """
    import os
    from datetime import datetime
    
    try:
        stat = os.stat(file_path)
        return f"""File: {file_path}
Size: {stat.st_size} bytes
Modified: {datetime.fromtimestamp(stat.st_mtime).isoformat()}
Created: {datetime.fromtimestamp(stat.st_ctime).isoformat()}"""
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    except Exception as e:
        return f"Error getting file info: {str(e)}"


@tool
def run_command(command: str, cwd: Optional[str] = None) -> str:
    """Run a shell command.
    
    Args:
        command: Command to run
        cwd: Working directory (optional)
        
    Returns:
        Command output
    """
    import subprocess
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout + result.stderr
        return output if output else "Command completed with no output"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds"
    except Exception as e:
        return f"Error running command: {str(e)}"


# =============================================================================
# RUN CODE / TEST EXECUTION (MetaGPT-inspired)
# =============================================================================

class CommandResult:
    """Result of executing a command."""
    def __init__(self, stdout: str, stderr: str, returncode: int):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.success = returncode == 0


def detect_test_command(workspace_path: str) -> List[str]:
    """Detect the appropriate test command for a workspace.
    
    Checks for common test frameworks and returns the command to run.
    
    Args:
        workspace_path: Path to the workspace
        
    Returns:
        List of command arguments (e.g., ["python", "-m", "pytest"])
    """
    workspace = Path(workspace_path)
    
    # Check for Python projects
    if (workspace / "pytest.ini").exists() or (workspace / "pyproject.toml").exists():
        return ["python", "-m", "pytest", "-v"]
    
    if (workspace / "setup.py").exists():
        return ["python", "-m", "pytest", "-v"]
    
    # Check for Node.js projects
    package_json = workspace / "package.json"
    if package_json.exists():
        try:
            import json
            with open(package_json) as f:
                pkg = json.load(f)
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                # Check if using npm or bun
                if (workspace / "bun.lockb").exists():
                    return ["bun", "test"]
                return ["npm", "test"]
        except Exception:
            pass
    
    # Default to pytest for Python files
    py_files = list(workspace.glob("**/*.py"))
    if py_files:
        return ["python", "-m", "pytest", "-v"]
    
    # Default to npm test for JS/TS files
    js_files = list(workspace.glob("**/*.js")) + list(workspace.glob("**/*.ts"))
    if js_files:
        return ["npm", "test"]
    
    return ["echo", "No test framework detected"]


async def execute_command_async(
    command: List[str],
    working_directory: str,
    timeout: int = 60,
    env: Dict[str, str] = None
) -> CommandResult:
    """Execute a command asynchronously.
    
    Args:
        command: Command and arguments as list
        working_directory: Working directory for the command
        timeout: Timeout in seconds
        env: Optional environment variables
        
    Returns:
        CommandResult with stdout, stderr, and returncode
    """
    import asyncio
    import subprocess
    
    try:
        # Merge with current environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # Add workspace to PYTHONPATH for Python projects
        pythonpath = process_env.get("PYTHONPATH", "")
        process_env["PYTHONPATH"] = f"{working_directory}:{pythonpath}"
        
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=working_directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=process_env
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            return CommandResult(
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                returncode=process.returncode or 0
            )
        except asyncio.TimeoutError:
            process.kill()
            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                returncode=-1
            )
            
    except Exception as e:
        return CommandResult(
            stdout="",
            stderr=f"Error executing command: {str(e)}",
            returncode=-1
        )


def execute_command_sync(
    command: List[str],
    working_directory: str,
    timeout: int = 60,
    env: Dict[str, str] = None
) -> CommandResult:
    """Execute a command synchronously.
    
    Args:
        command: Command and arguments as list
        working_directory: Working directory for the command
        timeout: Timeout in seconds
        env: Optional environment variables
        
    Returns:
        CommandResult with stdout, stderr, and returncode
    """
    import subprocess
    
    try:
        # Merge with current environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # Add workspace to PYTHONPATH for Python projects
        pythonpath = process_env.get("PYTHONPATH", "")
        process_env["PYTHONPATH"] = f"{working_directory}:{pythonpath}"
        
        result = subprocess.run(
            command,
            cwd=working_directory,
            capture_output=True,
            timeout=timeout,
            env=process_env
        )
        
        return CommandResult(
            stdout=result.stdout.decode("utf-8", errors="replace"),
            stderr=result.stderr.decode("utf-8", errors="replace"),
            returncode=result.returncode
        )
        
    except subprocess.TimeoutExpired:
        return CommandResult(
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
            returncode=-1
        )
    except Exception as e:
        return CommandResult(
            stdout="",
            stderr=f"Error executing command: {str(e)}",
            returncode=-1
        )


def find_test_file(workspace_path: str, source_file: str) -> Optional[str]:
    """Find the test file for a given source file.
    
    Args:
        workspace_path: Path to workspace
        source_file: Name of the source file
        
    Returns:
        Path to test file if found, None otherwise
    """
    workspace = Path(workspace_path)
    source_name = Path(source_file).stem
    
    # Common test file patterns
    patterns = [
        f"test_{source_name}.py",
        f"{source_name}_test.py",
        f"tests/test_{source_name}.py",
        f"test/test_{source_name}.py",
        f"__tests__/{source_name}.test.js",
        f"__tests__/{source_name}.test.ts",
        f"{source_name}.test.js",
        f"{source_name}.test.ts",
        f"{source_name}.spec.js",
        f"{source_name}.spec.ts",
    ]
    
    for pattern in patterns:
        matches = list(workspace.glob(f"**/{pattern}"))
        if matches:
            return str(matches[0].relative_to(workspace))
    
    return None


def get_developer_tools():
    """Get all developer tools."""
    return [
        read_file,
        write_file,
        list_directory,
        search_in_files,
        get_file_info,
        run_command,
    ]


def get_workspace_tools(workspace_path: str):
    """Get tools configured for a specific workspace.
    
    Uses the Developer v1 filesystem tools which have root_dir support.
    
    Args:
        workspace_path: Path to the workspace directory
        
    Returns:
        List of tools configured for the workspace
    """
    from app.agents.developer.tools.filesystem_tools import (
        SafeFileReadTool,
        SafeFileWriteTool,
        SafeFileEditTool,
        SafeFileListTool,
        SafeFileDeleteTool,
        FileSearchTool,
    )
    from app.agents.developer.tools.git_python_tool import GitPythonTool
    from app.agents.developer.tools.custom_tool import ShellCommandTool
    
    return [
        SafeFileReadTool(root_dir=workspace_path),
        SafeFileWriteTool(root_dir=workspace_path),
        SafeFileEditTool(root_dir=workspace_path),
        SafeFileListTool(root_dir=workspace_path),
        SafeFileDeleteTool(root_dir=workspace_path),
        FileSearchTool(root_dir=workspace_path),
        GitPythonTool(root_dir=workspace_path),
        ShellCommandTool(root_dir=workspace_path),
    ]
