"""
Git Adapter Implementations

Provides abstraction layer cho Git operations với 2 implementations:
- LocalGitAdapter: Local git operations using GitPython
- DaytonaGitAdapter: Daytona sandbox git operations
"""

from datetime import datetime
from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo

from ..config import DaytonaConfig
from ..sandbox_manager import SandboxManager, get_sandbox_manager
from .base import GitAdapter


class LocalGitAdapter(GitAdapter):
    """
    Local git operations using GitPython.

    Copy logic từ git_tools_gitpython.py để maintain backward compatibility.
    """

    def clone(self, url: str, path: str, working_directory: str = ".") -> dict:
        """Clone repository using GitPython."""
        try:
            # Resolve full path
            full_path = Path(working_directory) / path
            full_path = full_path.resolve()

            # Clone repository
            repo = Repo.clone_from(url, full_path)

            return {
                "status": "success",
                "message": f"Successfully cloned repository to '{path}'",
                "path": str(full_path),
                "url": url,
            }

        except GitCommandError as e:
            return {"status": "error", "message": f"Git clone error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Error cloning repository: {str(e)}"}

    def create_branch(
        self,
        branch_name: str,
        base_branch: str = "main",
        source_branch: str | None = None,
        working_directory: str = ".",
    ) -> dict:
        """Create and checkout new branch using GitPython."""
        try:
            working_dir = Path(working_directory)

            # Convert to absolute path if needed
            if not working_dir.is_absolute():
                working_dir = working_dir.resolve()

            if not working_dir.exists():
                return {
                    "status": "error",
                    "message": f"Directory '{working_directory}' does not exist",
                }

            # Initialize or open repository
            is_new_repo = False
            try:
                repo = Repo(working_dir)
            except InvalidGitRepositoryError:
                # Auto-initialize Git repository
                try:
                    repo = Repo.init(working_dir, initial_branch="main")
                    is_new_repo = True
                except Exception as init_error:
                    return {
                        "status": "error",
                        "message": f"Failed to initialize Git repository: {str(init_error)}",
                    }

            # Sanitize branch name
            safe_branch_name = branch_name.replace(" ", "-").replace("_", "-").lower()
            if not safe_branch_name.startswith(
                ("feature/", "fix/", "hotfix/", "chore/")
            ):
                safe_branch_name = f"feature/{safe_branch_name}"

            # Check if repository has commits
            has_commits = False
            try:
                current_branch = repo.active_branch.name
                has_commits = True
            except (TypeError, ValueError):
                has_commits = False

            # Create initial commit if needed
            if not has_commits:
                # Import helper function
                from ...implementor.tool.git_tools_gitpython import (
                    create_initial_commit,
                )

                try:
                    initial_commit_info = create_initial_commit(repo, working_dir)
                    repo = Repo(working_dir)  # Reload repo
                    current_branch = "main"
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Cannot create initial commit: {str(e)}",
                    }

                # Create branch
                new_branch = repo.create_head(safe_branch_name)
                new_branch.checkout()

                return {
                    "status": "success",
                    "message": f"Created initial commit and branch '{safe_branch_name}'",
                    "branch_name": safe_branch_name,
                    "base_branch": current_branch,
                    "initial_commit_created": True,
                    "timestamp": datetime.now().isoformat(),
                }

            # Check if branch already exists
            if safe_branch_name in [head.name for head in repo.heads]:
                return {
                    "status": "error",
                    "message": f"Branch '{safe_branch_name}' already exists",
                }

            # Determine source branch for branching
            if source_branch:
                # Sequential branching: branch from source_branch
                try:
                    repo.git.checkout(source_branch)
                    new_branch = repo.create_head(safe_branch_name)
                    new_branch.checkout()

                    return {
                        "status": "success",
                        "message": f"Created branch '{safe_branch_name}' from '{source_branch}'",
                        "branch_name": safe_branch_name,
                        "source_branch": source_branch,
                        "timestamp": datetime.now().isoformat(),
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Failed to create branch from '{source_branch}': {str(e)}",
                    }
            else:
                # Independent branching: branch from base_branch
                try:
                    repo.git.checkout(base_branch)
                    new_branch = repo.create_head(safe_branch_name)
                    new_branch.checkout()

                    return {
                        "status": "success",
                        "message": f"Created branch '{safe_branch_name}' from '{base_branch}'",
                        "branch_name": safe_branch_name,
                        "base_branch": base_branch,
                        "timestamp": datetime.now().isoformat(),
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Failed to create branch from '{base_branch}': {str(e)}",
                    }

        except GitCommandError as e:
            return {"status": "error", "message": f"Git error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Error creating branch: {str(e)}"}

    def commit(
        self,
        message: str,
        files: list[str] | None = None,
        working_directory: str = ".",
    ) -> dict:
        """Commit changes using GitPython."""
        try:
            working_dir = Path(working_directory)

            # Convert to absolute path if needed
            if not working_dir.is_absolute():
                working_dir = working_dir.resolve()

            if not working_dir.exists():
                return {
                    "status": "error",
                    "message": f"Directory '{working_directory}' does not exist",
                }

            # Initialize or open repository
            try:
                repo = Repo(working_dir)
            except InvalidGitRepositoryError:
                repo = Repo.init(working_dir, initial_branch="main")

            # Get current branch
            try:
                current_branch = repo.active_branch.name
            except TypeError:
                current_branch = "main"

            # Check if there are any changes
            if not repo.is_dirty(untracked_files=True):
                return {
                    "status": "no_changes",
                    "message": "No changes to commit",
                    "branch": current_branch,
                }

            # Stage files
            if files:
                for file in files:
                    file_path = working_dir / file
                    if not file_path.exists():
                        return {
                            "status": "error",
                            "message": f"File '{file}' does not exist",
                        }
                    repo.index.add([str(file_path)])
            else:
                # Stage all changes
                repo.index.add("*")
                repo.index.add(repo.untracked_files)

            # Commit changes
            commit = repo.index.commit(message)

            # Get commit stats
            stats_lines = []
            for file_path, stats in commit.stats.files.items():
                stats_lines.append(
                    f"{file_path} | {stats['insertions']}+ {stats['deletions']}-"
                )
            commit_stats = "\n".join(stats_lines)

            return {
                "status": "success",
                "message": "Successfully committed changes",
                "commit_hash": commit.hexsha,
                "commit_short_hash": commit.hexsha[:8],
                "commit_message": message,
                "branch": current_branch,
                "stats": commit_stats,
                "insertions": commit.stats.total["insertions"],
                "deletions": commit.stats.total["deletions"],
                "files_changed": commit.stats.total["files"],
                "timestamp": datetime.now().isoformat(),
            }

        except GitCommandError as e:
            return {"status": "error", "message": f"Git error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Error committing changes: {str(e)}"}

    def push(
        self,
        branch: str | None = None,
        remote: str = "origin",
        working_directory: str = ".",
    ) -> dict:
        """Push changes to remote using GitPython."""
        try:
            working_dir = Path(working_directory)

            if not working_dir.is_absolute():
                working_dir = working_dir.resolve()

            if not working_dir.exists():
                return {
                    "status": "error",
                    "message": f"Directory '{working_directory}' does not exist",
                }

            # Open repository
            try:
                repo = Repo(working_dir)
            except InvalidGitRepositoryError:
                return {
                    "status": "error",
                    "message": f"'{working_directory}' is not a Git repository",
                }

            # Get current branch if not specified
            if not branch:
                branch = repo.active_branch.name

            # Get remote
            try:
                origin = repo.remote(remote)
            except ValueError:
                return {"status": "error", "message": f"No '{remote}' remote found"}

            # Push branch
            origin.push(branch)

            return {
                "status": "success",
                "message": f"Successfully pushed branch '{branch}' to '{remote}'",
                "branch": branch,
                "remote": remote,
                "timestamp": datetime.now().isoformat(),
            }

        except GitCommandError as e:
            return {"status": "error", "message": f"Git push error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Error pushing changes: {str(e)}"}

    def status(self, working_directory: str = ".") -> dict:
        """Get git status using GitPython."""
        try:
            working_dir = Path(working_directory)

            if not working_dir.is_absolute():
                working_dir = working_dir.resolve()

            if not working_dir.exists():
                return {
                    "status": "error",
                    "message": f"Directory '{working_directory}' does not exist",
                }

            # Open repository
            try:
                repo = Repo(working_dir)
            except InvalidGitRepositoryError:
                return {
                    "status": "error",
                    "message": f"'{working_directory}' is not a Git repository",
                }

            # Get current branch
            try:
                current_branch = repo.active_branch.name
            except TypeError:
                current_branch = "HEAD (no commits yet)"

            # Get status
            is_dirty = repo.is_dirty(untracked_files=True)
            untracked_files = repo.untracked_files
            modified_files = [item.a_path for item in repo.index.diff(None)]
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]

            return {
                "status": "success",
                "branch": current_branch,
                "is_dirty": is_dirty,
                "untracked_files": untracked_files,
                "modified_files": modified_files,
                "staged_files": staged_files,
            }

        except Exception as e:
            return {"status": "error", "message": f"Error getting git status: {str(e)}"}

    def checkout(self, branch: str, working_directory: str = ".") -> dict:
        """Checkout branch using GitPython."""
        try:
            working_dir = Path(working_directory)

            if not working_dir.is_absolute():
                working_dir = working_dir.resolve()

            if not working_dir.exists():
                return {
                    "status": "error",
                    "message": f"Directory '{working_directory}' does not exist",
                }

            # Open repository
            try:
                repo = Repo(working_dir)
            except InvalidGitRepositoryError:
                return {
                    "status": "error",
                    "message": f"'{working_directory}' is not a Git repository",
                }

            # Checkout branch
            repo.git.checkout(branch)

            return {
                "status": "success",
                "message": f"Successfully checked out branch '{branch}'",
                "branch": branch,
                "timestamp": datetime.now().isoformat(),
            }

        except GitCommandError as e:
            return {"status": "error", "message": f"Git checkout error: {str(e)}"}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error checking out branch: {str(e)}",
            }


class DaytonaGitAdapter(GitAdapter):
    """
    Daytona sandbox git operations.

    Uses Daytona Sandbox Git API (sandbox.git.*).
    """

    def __init__(self, sandbox_manager: SandboxManager):
        """
        Initialize DaytonaGitAdapter.

        Args:
            sandbox_manager: SandboxManager instance
        """
        self.sandbox_manager = sandbox_manager
        self.sandbox = sandbox_manager.get_sandbox()

    def _resolve_sandbox_path(self, working_directory: str) -> str:
        """
        Resolve working directory to sandbox path.

        Args:
            working_directory: Working directory (e.g., "." or "/root/workspace/repo")

        Returns:
            Absolute path in sandbox
        """
        if working_directory.startswith("/"):
            return working_directory
        else:
            return self.sandbox_manager.get_workspace_path("repo")

    def clone(self, url: str, path: str, working_directory: str = ".") -> dict:
        """Clone repository in Daytona sandbox."""
        try:
            # Resolve sandbox path
            sandbox_path = self._resolve_sandbox_path(working_directory)
            full_path = f"{sandbox_path}/{path}" if path != "." else sandbox_path

            # Clone repository using Daytona Git API
            self.sandbox.git.clone(url, full_path)

            return {
                "status": "success",
                "message": f"Successfully cloned repository to '{path}'",
                "path": full_path,
                "url": url,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error cloning repository in sandbox: {str(e)}",
            }

    def create_branch(
        self,
        branch_name: str,
        base_branch: str = "main",
        source_branch: str | None = None,
        working_directory: str = ".",
    ) -> dict:
        """Create and checkout new branch in Daytona sandbox."""
        try:
            # Resolve sandbox path
            sandbox_path = self._resolve_sandbox_path(working_directory)

            # Sanitize branch name
            safe_branch_name = branch_name.replace(" ", "-").replace("_", "-").lower()
            if not safe_branch_name.startswith(
                ("feature/", "fix/", "hotfix/", "chore/")
            ):
                safe_branch_name = f"feature/{safe_branch_name}"

            # Determine source branch
            source = source_branch if source_branch else base_branch

            # Checkout source branch first
            self.sandbox.git.checkout(source, path=sandbox_path)

            # Create and checkout new branch
            self.sandbox.git.checkout(safe_branch_name, create=True, path=sandbox_path)

            return {
                "status": "success",
                "message": f"Created branch '{safe_branch_name}' from '{source}'",
                "branch_name": safe_branch_name,
                "base_branch": base_branch,
                "source_branch": source_branch,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error creating branch in sandbox: {str(e)}",
            }

    def commit(
        self,
        message: str,
        files: list[str] | None = None,
        working_directory: str = ".",
    ) -> dict:
        """Commit changes in Daytona sandbox."""
        try:
            # Resolve sandbox path
            sandbox_path = self._resolve_sandbox_path(working_directory)

            # Commit changes using Daytona Git API
            # Note: Daytona git.commit() might auto-stage all changes
            self.sandbox.git.commit(message, path=sandbox_path)

            return {
                "status": "success",
                "message": "Successfully committed changes",
                "commit_message": message,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error committing changes in sandbox: {str(e)}",
            }

    def push(
        self,
        branch: str | None = None,
        remote: str = "origin",
        working_directory: str = ".",
    ) -> dict:
        """Push changes to remote from Daytona sandbox."""
        try:
            # Resolve sandbox path
            sandbox_path = self._resolve_sandbox_path(working_directory)

            # Push changes using Daytona Git API
            self.sandbox.git.push(path=sandbox_path, remote=remote)

            return {
                "status": "success",
                "message": f"Successfully pushed changes to '{remote}'",
                "remote": remote,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error pushing changes from sandbox: {str(e)}",
            }

    def status(self, working_directory: str = ".") -> dict:
        """Get git status from Daytona sandbox."""
        try:
            # Resolve sandbox path
            sandbox_path = self._resolve_sandbox_path(working_directory)

            # Get status using Daytona Git API
            status_info = self.sandbox.git.status(path=sandbox_path)

            return {
                "status": "success",
                "git_status": status_info,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error getting git status from sandbox: {str(e)}",
            }

    def checkout(self, branch: str, working_directory: str = ".") -> dict:
        """Checkout branch in Daytona sandbox."""
        try:
            # Resolve sandbox path
            sandbox_path = self._resolve_sandbox_path(working_directory)

            # Checkout branch using Daytona Git API
            self.sandbox.git.checkout(branch, path=sandbox_path)

            return {
                "status": "success",
                "message": f"Successfully checked out branch '{branch}'",
                "branch": branch,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error checking out branch in sandbox: {str(e)}",
            }


# ============================================================================
# ADAPTER FACTORY FUNCTION
# ============================================================================


def get_git_adapter() -> GitAdapter:
    """
    Get git adapter based on configuration.

    Returns:
        DaytonaGitAdapter if Daytona is enabled, LocalGitAdapter otherwise
    """
    config = DaytonaConfig.from_env()

    if config and config.enabled:
        # Daytona mode: use sandbox git
        sandbox_manager = get_sandbox_manager(config)
        if sandbox_manager and sandbox_manager.is_sandbox_active():
            return DaytonaGitAdapter(sandbox_manager)
        else:
            print("⚠️ Daytona enabled but no active sandbox. Falling back to local git.")
            return LocalGitAdapter()

    # Local mode: use local git
    return LocalGitAdapter()
