# app/agents/developer/implementor/tools/git_tools_gitpython.py
"""
Git workflow tools using GitPython library
Refactored from subprocess-based implementation for better performance and maintainability

REFACTORED: Now uses Adapter Pattern to support both local and Daytona sandbox modes.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# GitPython imports
from git import GitCommandError, InvalidGitRepositoryError, Repo
from langchain_core.tools import tool

# Import git adapter for local/Daytona mode switching


def create_initial_commit(repo: Repo, working_dir: Path) -> dict[str, Any]:
    """
    Create initial commit with all existing untracked files and ensure 'main' branch exists.

    This function stages all untracked files in the repository, creates an initial commit,
    and ensures the 'main' branch is created and checked out. It does NOT generate
    .gitignore or filter files.

    Args:
        repo: GitPython Repo object (already initialized)
        working_dir: Path to working directory

    Returns:
        Dict containing:
            - commit_hash: Full commit SHA
            - commit_short_hash: Short commit SHA (8 chars)
            - files_committed: List of files included in commit
            - message: Commit message
            - author: Commit author
            - timestamp: Commit timestamp
            - branch_created: Name of the branch created/checked out ('main')

    Raises:
        Exception: If no untracked files exist to commit
        GitCommandError: If commit operation fails

    Example:
        >>> repo = Repo.init("/path/to/project")
        >>> info = create_initial_commit(repo, Path("/path/to/project"))
        >>> print(info["commit_short_hash"])
        'abc12345'
        >>> print(info["branch_created"])
        'main'
    """
    # Get all untracked files
    untracked_files = repo.untracked_files

    # Check if there are files to commit
    if not untracked_files:
        # Create a README.md file for initial commit if no files exist
        readme_path = working_dir / "README.md"
        readme_content = "# Project Repository\n\nThis repository was initialized by Developer Agent.\n"

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        # Refresh untracked files list
        untracked_files = repo.untracked_files

        if not untracked_files:
            raise Exception(
                "Failed to create initial files for commit. Repository state is inconsistent."
            )

    # Stage all untracked files
    repo.index.add(untracked_files)

    # Create initial commit
    commit = repo.index.commit("Initial commit")

    # Ensure 'main' branch exists and is checked out
    # After the first commit, the branch should exist, but we need to ensure it
    if "main" not in [head.name for head in repo.heads]:
        # Create 'main' branch pointing to the commit we just created
        main_branch = repo.create_head("main", commit)
        main_branch.checkout()
    else:
        # Branch exists, just checkout to ensure we're on it
        repo.heads.main.checkout()

    # Return commit information
    return {
        "commit_hash": commit.hexsha,
        "commit_short_hash": commit.hexsha[:8],
        "files_committed": untracked_files,
        "message": "Initial commit",
        "author": f"{commit.author.name} <{commit.author.email}>",
        "timestamp": commit.committed_datetime.isoformat(),
        "branch_created": "main",
    }


@tool
def create_feature_branch_tool(
    branch_name: str,
    base_branch: str = "main",
    working_directory: str = ".",
    source_branch: str = None,  # New parameter for sequential branching
) -> str:
    """
    Create a new feature branch for implementation using GitPython.

    Supports two branching strategies:
    1. Independent branching: Create from base_branch (default)
    2. Sequential branching: Create from source_branch (preserves files from previous task)

    This tool creates a new Git branch from the specified base branch or source branch
    and switches to it for development work.

    Args:
        branch_name: Name of the new feature branch (e.g., "feature/add-auth")
        base_branch: Base branch to create from (default: "main")
        working_directory: Git repository directory
        source_branch: Source branch for sequential branching (optional)

    Returns:
        JSON string with branch creation status

    Examples:
        # Independent branching (default)
        create_feature_branch_tool("feature/add-user-auth", "main")

        # Sequential branching (preserve files from previous task)
        create_feature_branch_tool("feature/task-2", "main", ".", "feature/task-1")
    """
    # REFACTORED: Use adapter pattern for local/Daytona mode switching
    from ...daytona.adapters import get_git_adapter

    adapter = get_git_adapter()
    result = adapter.create_branch(
        branch_name, base_branch, source_branch, working_directory
    )
    return json.dumps(result, indent=2)


@tool
def commit_changes_tool(
    message: str, files: list[str] | None = None, working_directory: str = "."
) -> str:
    """
    Commit changes to the current Git branch using GitPython.

    This tool stages and commits changes with a descriptive message.
    If no files are specified, it commits all modified files.

    Args:
        message: Commit message describing the changes
        files: List of specific files to commit (optional, commits all if None)
        working_directory: Git repository directory

    Returns:
        JSON string with commit information

    Example:
        commit_changes_tool("Add user authentication endpoints", ["auth.py", "routes.py"])
    """
    # REFACTORED: Use adapter pattern for local/Daytona mode switching
    from ...daytona.adapters import get_git_adapter

    adapter = get_git_adapter()
    result = adapter.commit(message, files, working_directory)
    return json.dumps(result, indent=2)


@tool
def create_pull_request_tool(
    title: str,
    description: str,
    base_branch: str = "main",
    working_directory: str = ".",
    draft: bool = False,
) -> str:
    """
    Create a pull request for code review using GitPython.

    This tool pushes the current branch and provides PR creation information.
    Note: Actual PR creation requires GitHub/GitLab API integration.

    Args:
        title: Pull request title
        description: Pull request description
        base_branch: Target branch for the PR (default: "main")
        working_directory: Git repository directory
        draft: Whether to create as draft PR

    Returns:
        JSON string with PR information

    Example:
        create_pull_request_tool(
            "Add user authentication",
            "Implements JWT-based authentication with login/logout endpoints"
        )
    """
    try:
        working_dir = Path(working_directory)

        # Convert to absolute path if needed
        if not working_dir.is_absolute():
            working_dir = working_dir.resolve()

        if not working_dir.exists():
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Directory '{working_directory}' does not exist",
                }
            )

        # Initialize repository
        try:
            repo = Repo(working_dir)
        except InvalidGitRepositoryError:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"'{working_directory}' is not a Git repository",
                }
            )

        # Get current branch
        current_branch = repo.active_branch.name

        # Check if on base branch
        if current_branch == base_branch:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Cannot create PR from base branch '{base_branch}'",
                }
            )

        # Check for uncommitted changes
        if repo.is_dirty(untracked_files=True):
            return json.dumps(
                {
                    "status": "error",
                    "message": "You have uncommitted changes. Please commit them first.",
                }
            )

        # Get origin remote
        try:
            origin = repo.remote("origin")
        except ValueError:
            return json.dumps(
                {"status": "error", "message": "No 'origin' remote found"}
            )

        # Push current branch to origin
        try:
            push_info = origin.push(current_branch)
            push_status = "success"

            # Check if push was successful
            if push_info and push_info[0].flags & push_info[0].ERROR:
                push_status = "error"
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Push failed: {push_info[0].summary}",
                    }
                )
        except GitCommandError:
            # Try to set upstream and push
            try:
                push_info = origin.push(
                    f"{current_branch}:{current_branch}", set_upstream=True
                )
                push_status = "success_with_upstream"
            except GitCommandError as e2:
                return json.dumps(
                    {"status": "error", "message": f"Push failed: {str(e2)}"}
                )

        # Get commit count between branches
        try:
            base_head = repo.heads[base_branch]
            commits = list(repo.iter_commits(f"{base_head}..{current_branch}"))
            commit_count = len(commits)
        except Exception:
            commit_count = 0

        # Get changed files
        try:
            base_head = repo.heads[base_branch]
            diffs = base_head.commit.diff(repo.active_branch.commit)
            changed_files = [diff.a_path or diff.b_path for diff in diffs]
        except Exception:
            changed_files = []

        # Get remote URL
        remote_url = origin.url if hasattr(origin, "url") else "unknown"

        pr_info = {
            "status": "branch_pushed",
            "message": f"Branch '{current_branch}' pushed successfully",
            "title": title,
            "description": description,
            "source_branch": current_branch,
            "target_branch": base_branch,
            "commit_count": commit_count,
            "changed_files": changed_files,
            "draft": draft,
            "remote_url": remote_url,
            "timestamp": datetime.now().isoformat(),
            "next_steps": [
                "Visit your Git hosting platform (GitHub/GitLab) to create the PR",
                f"Create PR from '{current_branch}' to '{base_branch}'",
                "Use the provided title and description",
            ],
        }

        # Generate GitHub PR URL if it's a GitHub repo
        if "github.com" in remote_url:
            # Extract owner/repo from URL
            if remote_url.endswith(".git"):
                remote_url = remote_url[:-4]
            if remote_url.startswith("git@github.com:"):
                repo_path = remote_url.replace("git@github.com:", "")
            elif "github.com/" in remote_url:
                repo_path = remote_url.split("github.com/")[-1]
            else:
                repo_path = None

            if repo_path:
                pr_url = f"https://github.com/{repo_path}/compare/{base_branch}...{current_branch}"
                pr_info["pr_url"] = pr_url
                pr_info["next_steps"] = [f"Visit: {pr_url}"]

        return json.dumps(pr_info, indent=2)

    except GitCommandError as e:
        return json.dumps({"status": "error", "message": f"Git error: {str(e)}"})
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error creating pull request: {str(e)}"}
        )
