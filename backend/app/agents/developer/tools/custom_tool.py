import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import ClassVar, List, Type
from datetime import datetime
from crewai.tools import BaseTool
from langfuse import observe
from pydantic import BaseModel, Field


class MyCustomToolInput(BaseModel):
    """Input schema for MyCustomTool."""

    argument: str = Field(..., description="Description of the argument.")


class MyCustomTool(BaseTool):
    name: str = "Name of my tool"
    description: str = "Clear description for what this tool is useful for, your agent will need this information to use it."
    args_schema: type[BaseModel] = MyCustomToolInput

    def _run(self, argument: str) -> str:
        # Implementation goes here
        return "this is an example of a tool output, ignore it and move along."


# Web Search Tools
class WebSearchInput(BaseModel):
    """Input schema for web search."""

    query: str = Field(..., description="The search query to look up on the web.")


class DuckDuckGoSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web using DuckDuckGo. Useful for finding current information, "
        "documentation, best practices, or solutions to technical problems. "
        "Returns a list of search results with titles, URLs, and snippets."
    )
    args_schema: type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        """Execute web search using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))

            if not results:
                return f"No results found for query: {query}"

            # Format results
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"{i}. {result.get('title', 'No title')}\n"
                    f"   URL: {result.get('href', 'No URL')}\n"
                    f"   Snippet: {result.get('body', 'No description')}\n"
                )

            return "\n".join(formatted_results)

        except ImportError:
            return "Error: duckduckgo-search package not installed. Please install it with: pip install duckduckgo-search"
        except Exception as e:
            return f"Error performing web search: {str(e)}"


# Shell Command Execution Tool
class ShellCommandInput(BaseModel):
    """Input schema for shell command execution."""

    command: str = Field(
        ...,
        description="The shell command to execute (e.g., 'npm install', 'python script.py')",
    )
    working_directory: str | None = Field(
        default=".",
        description="The directory where the command should run. Defaults to current directory.",
    )
    timeout: int | None = Field(
        default=60,
        description="Maximum execution time in seconds. Defaults to 60 seconds.",
    )
    capture_output: bool | None = Field(
        default=True, description="Whether to capture stdout/stderr. Defaults to True."
    )


class ShellCommandTool(BaseTool):
    name: str = "execute_shell_command"
    description: str = (
        "Execute shell commands within the project's root directory. "
        "Useful for running build commands (pnpm install, pnpm run build), "
        "package managers (pip install, yarn add), testing (npm test, pytest), "
        "and other development tasks. The working directory is fixed to the project root."
        "\n\nSecurity: Dangerous commands (rm -rf /, sudo, etc.) are blocked. "
        "Commands are executed with a timeout. "
        "\n\nReturns JSON with: status, exit_code, stdout, stderr, execution_time."
    )
    args_schema: type[BaseModel] = ShellCommandInput
    root_dir: str = Field(default_factory=os.getcwd)

    # Dangerous command patterns to block
    DANGEROUS_PATTERNS: ClassVar[list[str]] = [
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

    def _is_safe_command(self, command: str) -> tuple[bool, str]:
        """
        Check if a command is safe to execute.

        Returns:
            tuple: (is_safe: bool, reason: str)
        """
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Dangerous command pattern detected: {pattern}"

        # Block commands that try to escape the working directory
        if ".." in command and ("cd" in command.lower() or "pushd" in command.lower()):
            return False, "Directory traversal detected"

        return True, ""

    def _normalize_path(self, working_directory: str) -> Path:
        """
        Normalize and validate the working directory path.

        Args:
            working_directory: The requested working directory

        Returns:
            Path: Normalized absolute path within root_dir
        """
        root = Path(self.root_dir).resolve()

        # If working_directory is relative, join with root_dir
        if not os.path.isabs(working_directory):
            target = (root / working_directory).resolve()
        else:
            target = Path(working_directory).resolve()

        # Ensure the target is within root_dir
        try:
            target.relative_to(root)
        except ValueError:
            # If target is not within root, use root instead
            return root

        # Create directory if it doesn't exist
        if not target.exists():
            return root

        return target

    @observe(name="shell_command_execution")
    def _run(
        self,
        command: str,
        working_directory: str = ".",
        timeout: int = 60,
        capture_output: bool = True,
    ) -> str:
        """
        Execute a shell command with safety checks and timeout.

        Args:
            command: The shell command to execute
            working_directory: Directory where command should run
            timeout: Maximum execution time in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            JSON string with execution results
        """
        start_time = time.time()

        # Safety check
        is_safe, reason = self._is_safe_command(command)
        if not is_safe:
            return json.dumps(
                {
                    "status": "blocked",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command blocked for security reasons: {reason}",
                    "execution_time": 0,
                    "command": command,
                },
                indent=2,
            )

        # Normalize working directory
        work_dir = self._normalize_path(working_directory)

        try:
            # Determine shell based on OS
            if os.name == "nt":  # Windows
                shell_cmd = ["cmd", "/c", command]
                use_shell = False
            else:  # Unix/Linux/Mac
                shell_cmd = command
                use_shell = True

            # Execute command
            result = subprocess.run(
                shell_cmd,
                cwd=str(work_dir),
                shell=use_shell,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                env=os.environ.copy(),
            )

            execution_time = time.time() - start_time

            return json.dumps(
                {
                    "status": "success" if result.returncode == 0 else "error",
                    "exit_code": result.returncode,
                    "stdout": result.stdout if capture_output else "",
                    "stderr": result.stderr if capture_output else "",
                    "execution_time": round(execution_time, 2),
                    "command": command,
                    "working_directory": str(work_dir),
                },
                indent=2,
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return json.dumps(
                {
                    "status": "timeout",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds",
                    "execution_time": round(execution_time, 2),
                    "command": command,
                    "working_directory": str(work_dir),
                },
                indent=2,
            )

        except FileNotFoundError as e:
            execution_time = time.time() - start_time
            return json.dumps(
                {
                    "status": "error",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command not found: {str(e)}",
                    "execution_time": round(execution_time, 2),
                    "command": command,
                    "working_directory": str(work_dir),
                },
                indent=2,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return json.dumps(
                {
                    "status": "error",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Unexpected error: {str(e)}",
                    "execution_time": round(execution_time, 2),
                    "command": command,
                    "working_directory": str(work_dir),
                },
                indent=2,
            )


# ============================================================================
# CocoIndex Semantic Code Search Tool
# ============================================================================

from pydantic import field_validator

from app.agents.developer.project_manager import project_manager


class CodebaseSearchInput(BaseModel):
    """Input schema for semantic codebase search."""

    query: str = Field(
        ...,
        description="Natural language or code search query. Examples: 'authentication logic', 'React components', 'database models', 'user validation', 'error handling'",
    )
    top_k: int = Field(
        default=5, description="Number of top results to return (default: 5, max: 10)"
    )

    @field_validator("query", mode="before")
    @classmethod
    def clean_query(cls, v):
        """Cleans the query input by extracting the string from a dict if necessary."""
        if isinstance(v, dict):
            # If the input is a dict like {'description': '...', 'type': '...'}, extract the description.
            return v.get("description", "")
        return v


class CodebaseSearchTool(BaseTool):
    name: str = "codebase_search"
    description: str = (
        "**Semantic Codebase Search**: Finds semantically relevant code snippets using natural language."
        "\n\n**When to Use:**"
        "\n- To find where a specific feature or logic is implemented when you don't know the file path."
        "\n- To discover code patterns or examples related to a concept (e.g., 'error handling patterns', 'React hook examples')."
        "\n\n**When NOT to Use:**"
        "\n- **If you already know the file path:** Use the `SafeFileReadTool` to read the file directly."
        "\n- **To explore the project structure:** Use the `SafeFileListTool` to list files and directories."
        "\n\n**Effective Queries:**"
        "\n- Be specific. Instead of `'user'`, try `'user model schema'` or `'user authentication API'`."
        "\n- Combine concepts: `'React component for user profile page'`."
    )
    args_schema: type[BaseModel] = CodebaseSearchInput
    project_id: str = None

    def __init__(self, project_id: str, **kwargs):
        super().__init__(**kwargs)
        self.project_id = project_id

    def _run(self, query: str, top_k: int = 5) -> str:
        """
        Execute semantic code search across the codebase.

        Args:
            query: Search query describing what code to find
            top_k: Number of results to return (clamped to 10 max)

        Returns:
            Formatted string with search results and code snippets
        """
        if not self.project_id:
            return "Error: project_id was not provided to CodebaseSearchTool."

        try:
            results = project_manager.search(self.project_id, query, top_k=top_k)

            if not results:
                return f"No results found in project '{self.project_id}' for query: '{query}'"

            # Format results
            formatted_output = [
                f"Code search results for '{query}' in project '{self.project_id}':\n"
            ]
            for i, result in enumerate(results, 1):
                score_pct = int(result.get("score", 0) * 100)
                formatted_output.append(
                    f"{i}. {result['filename']} (Relevance: {score_pct}%)\n"
                    f"---\n{result['code']}\n---"
                )
            return "\n".join(formatted_output)

        except Exception as e:
            return f"Error performing semantic search in project '{self.project_id}': {str(e)}"


class CocoIndexSearchInput(BaseModel):
    """Input schema for CocoIndex semantic code search (deprecated - use CodebaseSearchTool)."""

    query: str = Field(
        ...,
        description="Natural language or code search query. Examples: 'authentication logic', 'React components', 'database models'",
    )
    top_k: int = Field(
        default=5, description="Number of top results to return (default: 5)"
    )


class CocoIndexSearchTool(BaseTool):
    """Deprecated: Use CodebaseSearchTool instead for better results."""

    name: str = "cocoindex_search"
    description: str = (
        "**[DEPRECATED] Use 'codebase_search' tool instead for better results.**\n\n"
        "Semantic Code Search using CocoIndex: Search the indexed codebase using natural language or code queries. "
        "This tool uses vector embeddings to find semantically similar code across the entire project."
    )
    args_schema: type[BaseModel] = CocoIndexSearchInput

    def _run(self, query: str, top_k: int = 5) -> str:
        """Execute semantic code search using CocoIndex."""
        try:
            # Use the new CodebaseSearchTool implementation
            from dev.flows import search

            query_output = search(query)

            if not query_output or not query_output.results:
                return f"No results found for query: '{query}'"

            # Format results simply
            results = query_output.results[:top_k]
            formatted_results = [
                f"🔍 Search Results for: '{query}' ({len(results)} found)\n"
            ]

            for i, result in enumerate(results, 1):
                formatted_results.append(
                    f"{i}. [{result['score']:.3f}] {result['filename']}"
                )
                formatted_results.append(f"   {result['code'][:200]}")
                formatted_results.append("")

            return "\n".join(formatted_results)

        except Exception as e:
            return f"Error: {str(e)}"


# ============================================================================
# Git Branch Management Tool
# ============================================================================

from typing import List

class GitBranchToolInput(BaseModel):
    """Input for git branch operations"""
    operation: str = Field(..., description="Git operation: 'init', 'create_branch', 'checkout_branch', 'commit', 'push', 'status', 'diff'")
    branch_name: str = Field(default=None, description="Branch name for operations")
    message: str = Field(default="Auto-commit by AI agent", description="Commit message")
    files: List[str] = Field(default=["."], description="List of files to commit, default to all changed files")


class GitBranchTool(BaseTool):
    name: str = "git_branch_tool"
    description: str = """Git operations for branch management:
    - 'init': Initialize git repository
    - 'create_branch': Create and switch to a new branch with format 'ai-task-<timestamp>' if branch_name not provided
    - 'checkout_branch': Switch to an existing branch
    - 'commit': Commit current changes with message
    - 'push': Push current branch to remote
    - 'status': Get git status
    - 'diff': Get git diff
    Usage: {'operation': 'create_branch', 'branch_name': 'feature/new-feature', 'message': 'Initial commit'}"""
    args_schema: Type[BaseModel] = GitBranchToolInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for git operations")

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir or os.getcwd()

    def _run(self, operation: str, branch_name: str = None, message: str = "Auto-commit by AI agent", files: List[str] = ["."]) -> str:
        

        try:
            # Change to the project directory
            original_dir = os.getcwd()
            os.chdir(self.root_dir)

            result = ""

            if operation == "create_branch":
                if not branch_name:
                    # Generate a unique branch name based on timestamp if not provided
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    branch_name = f"ai-task-{timestamp}"

                # Check if branch exists
                check_cmd = ["git", "branch", "--list", branch_name]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True)
                if branch_name in check_result.stdout:
                    # Branch already exists, switch to it
                    cmd = ["git", "checkout", branch_name]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    result = f"Switched to existing branch '{branch_name}':\n{result.stdout}"
                else:
                    # Create and switch to new branch
                    cmd = ["git", "checkout", "-b", branch_name]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    result = f"Created and switched to new branch '{branch_name}':\n{result.stdout}"

            elif operation == "checkout_branch":
                if not branch_name:
                    return "Error: branch_name is required for checkout_branch operation"
                # Switch to existing branch
                cmd = ["git", "checkout", branch_name]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                result = f"Switched to branch '{branch_name}':\n{result.stdout}"

            elif operation == "commit":
                # If files list contains just ["."] (meaning all), replace with actual changed files
                if files == ["."]:
                    # Get list of changed files only
                    diff_cmd = ["git", "diff", "--name-only"]
                    diff_result = subprocess.run(diff_cmd, capture_output=True, text=True)
                    if diff_result.returncode == 0:
                        changed_files = diff_result.stdout.strip().split('\n')
                        changed_files = [f for f in changed_files if f.strip()]  # Remove empty strings
                        files = changed_files or ["."]  # Use changed files or ["."] if none found

                # Add files
                add_cmd = ["git", "add"] + files
                add_result = subprocess.run(add_cmd, capture_output=True, text=True)

                if add_result.returncode != 0:
                    result = f"Add failed: {add_result.stderr}"
                else:
                    # Commit changes
                    commit_cmd = ["git", "commit", "-m", message]
                    commit_result = subprocess.run(commit_cmd, capture_output=True, text=True)

                    if commit_result.returncode == 0:
                        result = f"Committed {len(files)} file(s): {message}\n{commit_result.stdout}"
                    else:
                        # If no changes to commit, that's OK
                        if "nothing to commit" in commit_result.stdout.lower() or "no changes added to commit" in commit_result.stdout.lower():
                            result = f"No changes to commit: {commit_result.stdout}"
                        else:
                            result = f"Commit failed: {commit_result.stderr}"

            elif operation == "push":
                # Get current branch name
                branch_result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
                current_branch = branch_result.stdout.strip()

                if current_branch == "HEAD":
                    # Detached HEAD state
                    result = "Error: Cannot push in detached HEAD state"
                else:
                    # Push current branch to remote
                    cmd = ["git", "push", "--set-upstream", "origin", current_branch]
                    push_result = subprocess.run(cmd, capture_output=True, text=True)
                    if push_result.returncode == 0:
                        result = f"Pushed branch '{current_branch}' to remote:\n{push_result.stdout}"
                    else:
                        result = f"Push failed:\n{push_result.stderr}"

            elif operation == "status":
                # Get git status
                cmd = ["git", "status", "--short"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                result = f"Git status:\n{result.stdout}"

            elif operation == "init":
                # Initialize git repository
                init_cmd = ["git", "init"]
                init_result = subprocess.run(init_cmd, capture_output=True, text=True)
                if init_result.returncode == 0:
                    # Also set up initial configuration
                    subprocess.run(["git", "config", "user.name", "AI-Agent"], capture_output=True)
                    subprocess.run(["git", "config", "user.email", "ai-agent@vibesdlc.com"], capture_output=True)

                    # Check if there are any commits (repository is empty)
                    # Use symbolic-ref to check current branch - this will fail if no commits exist
                    rev_parse_cmd = ["git", "rev-parse", "--verify", "HEAD"]
                    rev_result = subprocess.run(rev_parse_cmd, capture_output=True, text=True)

                    if rev_result.returncode != 0:  # No commits exist (HEAD doesn't exist)
                        # Create an initial commit
                        # First, make sure we have at least one file to commit
                        gitkeep_path = os.path.join(self.root_dir, ".gitkeep")
                        if not os.path.exists(gitkeep_path):
                            with open(gitkeep_path, "w") as f:
                                f.write("# Initial commit to create main branch\n")

                        # Add files and commit
                        subprocess.run(["git", "add", "."], capture_output=True)
                        init_commit_result = subprocess.run(["git", "commit", "-m", "Initial commit"], capture_output=True, text=True)

                        if init_commit_result.returncode == 0:
                            result = f"Git repository initialized successfully with initial commit:\n{init_result.stdout}\n{init_commit_result.stdout}"
                        else:
                            result = f"Git repository initialized but initial commit failed:\n{init_result.stdout}\n{init_commit_result.stderr}"
                    else:
                        result = f"Git repository initialized successfully:\n{init_result.stdout}"
                else:
                    # If repo already exists, that's OK
                    if "reinitialized existing" in init_result.stdout:
                        result = f"Git repository reinitialized (already existed):\n{init_result.stdout}"
                    else:
                        result = f"Git init failed:\n{init_result.stderr}"

            elif operation == "diff":
                # Get git diff
                cmd = ["git", "diff", "--name-only"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                result = f"Changed files:\n{result.stdout}"

            else:
                result = f"Error: Unknown operation '{operation}'. Supported operations: init, create_branch, checkout_branch, commit, push, status, diff"

        except subprocess.CalledProcessError as e:
            result = f"Git operation failed: {e.stderr if e.stderr else str(e)}"
        except Exception as e:
            result = f"Error during git operation: {str(e)}"
        finally:
            # Restore original directory
            os.chdir(original_dir)

        return str(result)
