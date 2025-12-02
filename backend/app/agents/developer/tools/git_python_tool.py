from typing import List, Optional, Type
from pydantic import BaseModel, Field
from git import Repo, InvalidGitRepositoryError
import os
from datetime import datetime
from pathlib import Path


class GitPythonToolInput(BaseModel):
    """Input for git operations using GitPython"""
    operation: str = Field(..., description="Git operation: 'init', 'create_branch', 'create_worktree', 'remove_worktree', 'checkout_branch', 'commit', 'push', 'status', 'diff', 'merge', 'delete_branch'")
    branch_name: str = Field(default=None, description="Branch name for operations")
    message: str = Field(default="Auto-commit by AI agent", description="Commit message")
    files: List[str] = Field(default=["."], description="List of files to commit, default to all changed files")
    worktree_path: str = Field(default=None, description="Path for worktree operations")


class GitPythonTool:
    """Git operations using GitPython library (standalone, no CrewAI dependency)."""
    
    name: str = "git_python_tool"
    description: str = """Git operations using GitPython library:
    - 'init': Initialize git repository
    - 'create_branch': Create and switch to a new branch with format 'ai-task-<timestamp>' if branch_name not provided
    - 'create_worktree': Create an isolated worktree for a branch
    - 'remove_worktree': Remove a worktree
    - 'list_worktrees': List all worktrees
    - 'checkout_branch': Switch to an existing branch
    - 'commit': Commit current changes with message
    - 'push': Push current branch to remote
    - 'status': Get git status
    - 'diff': Get git diff
    - 'merge': Merge a branch into current branch
    - 'delete_branch': Delete a local branch
    Usage: {'operation': 'create_branch', 'branch_name': 'feature/new-feature', 'message': 'Initial commit'}"""

    def __init__(self, root_dir: str = None, **kwargs):
        self.root_dir = root_dir or os.getcwd()

    def _run(self, operation: str, branch_name: str = None, message: str = "Auto-commit by AI agent", files: List[str] = ["."], worktree_path: str = None) -> str:
        """Execute git operations using GitPython"""

        try:
            original_dir = os.getcwd()
            os.chdir(self.root_dir)

            result = ""

            if operation == "init":
                result = self._init_repo()
            elif operation == "create_branch":
                if not branch_name:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    branch_name = f"ai-task-{timestamp}"
                result = self._create_branch(branch_name)
            elif operation == "create_worktree":
                if not branch_name:
                    return "Error: branch_name is required for create_worktree operation"
                result = self._create_worktree(branch_name)
            elif operation == "remove_worktree":
                if not worktree_path:
                    return "Error: worktree_path is required for remove_worktree operation"
                result = self._remove_worktree(worktree_path)
            elif operation == "checkout_branch":
                if not branch_name:
                    return "Error: branch_name is required for checkout_branch operation"
                result = self._checkout_branch(branch_name)
            elif operation == "commit":
                result = self._commit_changes(message, files)
            elif operation == "push":
                result = self._push_changes()
            elif operation == "status":
                result = self._get_status()
            elif operation == "diff":
                result = self._get_diff()
            elif operation == "list_worktrees":
                result = self._list_worktrees()
            elif operation == "merge":
                if not branch_name:
                    return "Error: branch_name is required for merge operation"
                result = self._merge_branch(branch_name)
            elif operation == "delete_branch":
                if not branch_name:
                    return "Error: branch_name is required for delete_branch operation"
                result = self._delete_branch(branch_name)
            else:
                result = f"Error: Unknown operation '{operation}'. Supported operations: init, create_branch, create_worktree, remove_worktree, list_worktrees, checkout_branch, commit, push, status, diff, merge, delete_branch"

        except Exception as e:
            result = f"Error during git operation: {str(e)}"
        finally:
            os.chdir(original_dir)

        return str(result)

    def _init_repo(self) -> str:
        """Initialize a git repository using GitPython"""
        try:
            try:
                repo = Repo(self.root_dir)
                return f"Git repository already exists at: {self.root_dir}"
            except InvalidGitRepositoryError:
                repo = Repo.init(self.root_dir)
                
                with repo.config_writer() as git_config:
                    git_config.set_value("user", "name", "AI-Agent")
                    git_config.set_value("user", "email", "ai-agent@vibesdlc.com")
                    git_config.release()

                try:
                    repo.head.commit
                    return f"Git repository initialized successfully at: {self.root_dir}"
                except ValueError:
                    gitkeep_path = os.path.join(self.root_dir, ".gitkeep")
                    if not os.path.exists(gitkeep_path):
                        with open(gitkeep_path, "w") as f:
                            f.write("# Initial commit to create main branch\n")
                    
                    repo.index.add([".gitkeep"])
                    commit = repo.index.commit("Initial commit")
                    
                    return f"Git repository initialized successfully with initial commit at: {self.root_dir}"
        
        except Exception as e:
            return f"Git init failed: {str(e)}"

    def _create_branch(self, branch_name: str) -> str:
        """Create and switch to a new branch, or create worktree for multi-agent isolation"""
        try:
            repo = Repo(self.root_dir)

            existing_branch = None
            for ref in repo.branches:
                if ref.name == branch_name:
                    existing_branch = ref
                    break

            if existing_branch:
                return f"Branch '{branch_name}' already exists. Use worktree for isolated workspace."
            else:
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
                return f"Created and switched to new branch '{branch_name}'"

        except Exception as e:
            return f"Failed to create branch '{branch_name}': {str(e)}"

    def _create_worktree(self, branch_name: str) -> str:
        """Create a worktree for isolated development.

        For branch names like 'story_abc123', creates worktree at 'ws_story_abc123'.
        For other branch names, creates worktree at 'ws_{branch_name}'.
        """
        try:
            repo = Repo(self.root_dir)

            # Determine worktree name based on branch_name format
            if branch_name.startswith("story_"):
                # Extract the story ID part and create ws_story_{id}
                story_id = branch_name.replace("story_", "")
                worktree_name = f"ws_story_{story_id}"
            else:
                # For other branches, just use ws_{branch_name}
                worktree_name = f"ws_{branch_name}"

            worktree_path = Path(self.root_dir).parent / worktree_name

            if worktree_path.exists() and any(worktree_path.iterdir()):
                return f"Worktree directory '{worktree_path}' already exists and is not empty. Use a different branch name or remove the existing directory."

            if branch_name not in repo.heads:
                current_branch = repo.active_branch
                new_branch = repo.create_head(branch_name, current_branch.commit)
            else:
                new_branch = repo.heads[branch_name]

            repo.git.worktree('add', str(worktree_path), str(new_branch))

            return f"Created worktree at '{worktree_path}' for branch '{branch_name}'"

        except Exception as e:
            return f"Failed to create worktree for '{branch_name}': {str(e)}"

    def _remove_worktree(self, worktree_path: str) -> str:
        """Remove a worktree"""
        try:
            repo = Repo(self.root_dir)

            repo.git.worktree('remove', worktree_path)

            return f"Removed worktree at '{worktree_path}'"

        except Exception as e:
            return f"Failed to remove worktree at '{worktree_path}': {str(e)}"

    def _list_worktrees(self) -> str:
        """List all worktrees"""
        try:
            repo = Repo(self.root_dir)

            worktrees_output = repo.git.worktree('list')

            return f"Worktrees:\n{worktrees_output}"

        except Exception as e:
            return f"Failed to list worktrees: {str(e)}"

    def _checkout_branch(self, branch_name: str) -> str:
        """Checkout an existing branch"""
        try:
            repo = Repo(self.root_dir)
            
            branch_exists = False
            for ref in repo.branches:
                if ref.name == branch_name:
                    branch_exists = True
                    break
            
            if not branch_exists:
                return f"Error: Branch '{branch_name}' does not exist"
            
            repo.heads[branch_name].checkout()
            return f"Switched to branch '{branch_name}'"
        
        except Exception as e:
            return f"Failed to checkout branch '{branch_name}': {str(e)}"

    def _commit_changes(self, message: str, files: List[str]) -> str:
        """Commit changes to the repository"""
        try:
            repo = Repo(self.root_dir)
            
            if files == ["."]:
                repo.git.add(A=True)  
            else:
                repo.index.add(files)
            
            if repo.is_dirty(untracked_files=True) or repo.index.diff("HEAD"):
                commit = repo.index.commit(message)
                return f"Committed changes: {message}"
            else:
                return "No changes to commit"
        
        except Exception as e:
            return f"Commit failed: {str(e)}"

    def _push_changes(self) -> str:
        """Push changes to remote repository"""
        try:
            repo = Repo(self.root_dir)
            
            if repo.head.is_detached:
                return "Error: Cannot push in detached HEAD state"
            
            current_branch = repo.active_branch
            branch_name = current_branch.name
            
            if len(repo.remotes) == 0:
                return f"No remote configured for branch '{branch_name}'"
            
            origin = repo.remotes.origin
            push_info = origin.push(refspec=f"{branch_name}:{branch_name}")
            
            if len(push_info) > 0 and push_info[0].flags & push_info[0].ERROR:
                return f"Push failed: {push_info[0].summary}"
            else:
                return f"Pushed branch '{branch_name}' to remote"
        
        except Exception as e:
            return f"Push failed: {str(e)}"

    def _get_status(self) -> str:
        """Get git status"""
        try:
            repo = Repo(self.root_dir)
            
            untracked_files = repo.untracked_files
            changed_files = [item.a_path for item in repo.index.diff(None)]
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]
            
            status_output = []
            if changed_files:
                status_output.append("Modified files:")
                status_output.extend([f"  M {file}" for file in changed_files])
            
            if staged_files:
                status_output.append("Staged files:")
                status_output.extend([f"  A {file}" for file in staged_files])
            
            if untracked_files:
                status_output.append("Untracked files:")
                status_output.extend([f"?? {file}" for file in untracked_files])
            
            if not status_output:
                status_output.append("Nothing to commit, working tree clean")
            
            return "\n".join(status_output)
        
        except Exception as e:
            return f"Error getting status: {str(e)}"

    def _get_diff(self) -> str:
        """Get git diff"""
        try:
            repo = Repo(self.root_dir)
            
            changed_files = [item.a_path for item in repo.index.diff(None)]
            untracked_files = repo.untracked_files
            
            all_files = changed_files + untracked_files
            
            if all_files:
                return "Changed files:\n" + "\n".join(all_files)
            else:
                return "Changed files:\n"
        
        except Exception as e:
            return f"Error getting diff: {str(e)}"

    def _merge_branch(self, branch_name: str) -> str:
        """Merge a branch into the current branch using GitPython."""
        try:
            repo = Repo(self.root_dir)
            current_branch = repo.active_branch.name
            
            # Check if branch exists
            if branch_name not in [h.name for h in repo.heads]:
                return f"Error: Branch '{branch_name}' does not exist"
            
            # Perform merge
            repo.git.merge(branch_name, m=f"Merge branch '{branch_name}' into {current_branch}")
            
            return f"Merged '{branch_name}' into '{current_branch}'"
        
        except Exception as e:
            error_msg = str(e)
            if "conflict" in error_msg.lower():
                return f"Merge conflict when merging '{branch_name}': {error_msg}"
            return f"Merge failed: {error_msg}"

    def _delete_branch(self, branch_name: str, force: bool = False) -> str:
        """Delete a local branch using GitPython."""
        try:
            repo = Repo(self.root_dir)
            
            # Check if branch exists
            if branch_name not in [h.name for h in repo.heads]:
                return f"Error: Branch '{branch_name}' does not exist"
            
            # Cannot delete current branch
            if repo.active_branch.name == branch_name:
                return f"Error: Cannot delete current branch '{branch_name}'. Checkout another branch first."
            
            # Delete branch
            repo.delete_head(branch_name, force=force)
            
            return f"Deleted branch '{branch_name}'"
        
        except Exception as e:
            return f"Delete branch failed: {str(e)}"