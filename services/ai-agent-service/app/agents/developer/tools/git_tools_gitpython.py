# app/agents/developer/implementor/tools/git_tools_gitpython.py
"""
Git workflow tools using GitPython library
Refactored from subprocess-based implementation for better performance and maintainability
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# GitPython imports
from git import GitCommandError, InvalidGitRepositoryError, Repo
from langchain_core.tools import tool


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
    branch_name: str, base_branch: str = "main", working_directory: str = "."
) -> str:
    """
    Create a new feature branch for implementation using GitPython.

    This tool creates a new Git branch from the specified base branch
    and switches to it for development work.

    Args:
        branch_name: Name of the new feature branch (e.g., "feature/add-auth")
        base_branch: Base branch to create from (default: "main")
        working_directory: Git repository directory

    Returns:
        JSON string with branch creation status

    Example:
        create_feature_branch_tool("feature/add-user-auth", "main")
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

        is_new_repo = False
        try:
            repo = Repo(working_dir)
        except InvalidGitRepositoryError:
            # Auto-initialize Git repository
            try:
                repo = Repo.init(working_dir, initial_branch="main")
                is_new_repo = True
            except Exception as init_error:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Failed to initialize Git repository: {str(init_error)}",
                    }
                )

        # Sanitize branch name
        safe_branch_name = branch_name.replace(" ", "-").replace("_", "-").lower()
        if not safe_branch_name.startswith(("feature/", "fix/", "hotfix/", "chore/")):
            safe_branch_name = f"feature/{safe_branch_name}"

        # Check if repository has commits
        has_commits = False
        initial_commit_created = False
        initial_commit_info = None

        try:
            current_branch = repo.active_branch.name
            has_commits = True
        except (TypeError, ValueError):
            # Repository has no commits yet
            has_commits = False

        # Create initial commit if needed
        if not has_commits:
            try:
                initial_commit_info = create_initial_commit(repo, working_dir)
                initial_commit_created = True
                current_branch = "main"  # Default branch name

                # Reload repo object to refresh heads list after creating initial commit
                # GitPython caches repo.heads, so we need to reload to see the new 'main' branch
                repo = Repo(working_dir)

                # Verify that 'main' branch now exists
                if "main" not in [head.name for head in repo.heads]:
                    return json.dumps(
                        {
                            "status": "error",
                            "message": "Failed to create 'main' branch after initial commit. Repository state is inconsistent.",
                        }
                    )

            except Exception as e:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Cannot create initial commit: {str(e)}",
                    }
                )

        # Check if branch already exists
        if safe_branch_name in [head.name for head in repo.heads]:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Branch '{safe_branch_name}' already exists",
                }
            )

        # Conditional branch creation based on whether initial commit was created
        if initial_commit_created:
            # Simple branch creation for new repository (skip base branch operations)
            new_branch = repo.create_head(safe_branch_name)
            new_branch.checkout()

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Created initial commit and branch '{safe_branch_name}'",
                    "branch_name": safe_branch_name,
                    "base_branch": current_branch,
                    "initial_commit_created": True,
                    "initial_commit": initial_commit_info,
                    "timestamp": datetime.now().isoformat(),
                },
                indent=2,
            )
        else:
            # Normal flow with base branch operations for existing repository
            # Fetch latest changes from origin
            try:
                origin = repo.remote("origin")
                origin.fetch()
            except Exception:
                # Continue even if fetch fails (might be offline or no remote)
                pass

            # Check if working tree is dirty (has uncommitted changes)
            stash_created = False
            stash_message = f"Auto-stash before creating branch '{safe_branch_name}'"

            if repo.is_dirty(untracked_files=True):
                try:
                    # Stash uncommitted changes including untracked files
                    repo.git.stash("push", "-u", "-m", stash_message)
                    stash_created = True
                    print(f"📦 Stashed uncommitted changes: {stash_message}")
                except GitCommandError as e:
                    return json.dumps(
                        {
                            "status": "error",
                            "message": f"Failed to stash uncommitted changes: {str(e)}",
                        }
                    )

            # Check if we should preserve current working directory
            # If there are uncommitted files from previous tasks, create branch from current HEAD
            # instead of switching to base branch (which would lose uncommitted changes)
            preserve_working_dir = (
                repo.is_dirty(untracked_files=True) and not stash_created
            )

            if preserve_working_dir:
                print(
                    "🔄 Preserving working directory with uncommitted changes from previous task"
                )
                # Create new branch from current HEAD without switching to base branch
                new_branch = repo.create_head(safe_branch_name)
                new_branch.checkout()

                # Get current commit info
                current_commit = repo.head.commit
                commit_info = f"{current_commit.hexsha[:8]} {current_commit.summary}"

                response_data = {
                    "status": "success",
                    "message": f"Created branch '{safe_branch_name}' preserving working directory",
                    "branch_name": safe_branch_name,
                    "base_branch": current_branch,  # Use current branch as base
                    "previous_branch": current_branch,
                    "base_commit": commit_info,
                    "commit_hash": current_commit.hexsha,
                    "timestamp": datetime.now().isoformat(),
                    "preserved_working_dir": True,
                }
            else:
                # Normal flow: switch to base branch first
                try:
                    base_head = repo.heads[base_branch]
                    base_head.checkout()
                except IndexError:
                    return json.dumps(
                        {
                            "status": "error",
                            "message": f"Base branch '{base_branch}' does not exist",
                        }
                    )
                except GitCommandError as e:
                    # If stash was created, try to restore it
                    if stash_created:
                        try:
                            repo.git.stash("pop")
                            print("🔄 Restored stashed changes due to checkout failure")
                        except Exception:
                            print(
                                "⚠️ Failed to restore stash - please check 'git stash list'"
                            )

                    return json.dumps(
                        {
                            "status": "error",
                            "message": f"Failed to checkout base branch '{base_branch}': {str(e)}",
                        }
                    )

                # Pull latest changes from base branch
                try:
                    origin = repo.remote("origin")
                    origin.pull(base_branch)
                except Exception:
                    # Continue even if pull fails
                    pass

                # Create new branch from current HEAD
                new_branch = repo.create_head(safe_branch_name)
                new_branch.checkout()

                # Get base commit info
                base_commit = repo.head.commit
                commit_info = f"{base_commit.hexsha[:8]} {base_commit.summary}"

                response_data = {
                    "status": "success",
                    "message": f"Created and switched to branch '{safe_branch_name}'",
                    "branch_name": safe_branch_name,
                    "base_branch": base_branch,
                    "previous_branch": current_branch,
                    "base_commit": commit_info,
                    "commit_hash": base_commit.hexsha,
                    "timestamp": datetime.now().isoformat(),
                    "preserved_working_dir": False,
                }

            # Add stash information to response
            if "stash_created" not in response_data:
                response_data["stash_created"] = stash_created

            if stash_created:
                response_data["stash_message"] = stash_message
                response_data["note"] = (
                    "Uncommitted changes were stashed. Use 'git stash pop' to restore them."
                )

            return json.dumps(response_data, indent=2)

    except GitCommandError as e:
        return json.dumps({"status": "error", "message": f"Git error: {str(e)}"})
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error creating branch: {str(e)}"}
        )


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

        # Initialize repository (auto-init if not exists)
        is_new_repo = False
        try:
            repo = Repo(working_dir)
        except InvalidGitRepositoryError:
            # Auto-initialize Git repository
            try:
                repo = Repo.init(working_dir, initial_branch="main")
                is_new_repo = True
            except Exception as init_error:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Failed to initialize Git repository: {str(init_error)}",
                    }
                )

        # Get current branch (handle new repo with no commits)
        try:
            current_branch = repo.active_branch.name
        except TypeError:
            # New repo with no commits yet - HEAD is not valid
            current_branch = "main"  # Default branch name

        # Check if there are any changes
        if not repo.is_dirty(untracked_files=True):
            return json.dumps(
                {
                    "status": "no_changes",
                    "message": "No changes to commit",
                    "branch": current_branch,
                },
                indent=2,
            )

        # Stage files
        if files:
            # Stage specific files
            for file in files:
                file_path = working_dir / file
                if not file_path.exists():
                    return json.dumps(
                        {"status": "error", "message": f"File '{file}' does not exist"}
                    )
                repo.index.add([str(file_path)])
        else:
            # Stage all changes (modified, new, deleted)
            repo.index.add("*")  # Add all tracked files
            repo.index.add(repo.untracked_files)  # Add untracked files

        # Check if there are staged changes
        if not repo.index.diff("HEAD"):
            return json.dumps(
                {
                    "status": "no_staged_changes",
                    "message": "No staged changes to commit",
                    "branch": current_branch,
                },
                indent=2,
            )

        # Get list of staged files before commit (handle new repo)
        try:
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]
        except Exception:
            # New repo with no HEAD yet
            staged_files = list(repo.untracked_files)

        # Commit changes
        commit = repo.index.commit(message)

        # Get commit stats
        stats_lines = []
        for file_path, stats in commit.stats.files.items():
            stats_lines.append(
                f"{file_path} | {stats['insertions']}+ {stats['deletions']}-"
            )
        commit_stats = "\n".join(stats_lines)

        # Build success message
        success_message = "Successfully committed changes"
        if is_new_repo:
            success_message = "Initialized Git repository and committed changes"

        return json.dumps(
            {
                "status": "success",
                "message": success_message,
                "commit_hash": commit.hexsha,
                "commit_short_hash": commit.hexsha[:8],
                "commit_message": message,
                "branch": current_branch,
                "files_committed": staged_files,
                "stats": commit_stats,
                "insertions": commit.stats.total["insertions"],
                "deletions": commit.stats.total["deletions"],
                "files_changed": commit.stats.total["files"],
                "author": f"{commit.author.name} <{commit.author.email}>",
                "timestamp": datetime.now().isoformat(),
                "repository_initialized": is_new_repo,
            },
            indent=2,
        )

    except GitCommandError as e:
        return json.dumps({"status": "error", "message": f"Git error: {str(e)}"})
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Error committing changes: {str(e)}"}
        )


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
