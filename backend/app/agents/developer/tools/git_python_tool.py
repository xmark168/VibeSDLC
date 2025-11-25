from typing import List, Optional, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from git import Repo, InvalidGitRepositoryError
import os
from datetime import datetime


class GitPythonToolInput(BaseModel):
    """Input for git operations using GitPython"""
    operation: str = Field(..., description="Git operation: 'init', 'create_branch', 'checkout_branch', 'commit', 'push', 'status', 'diff'")
    branch_name: str = Field(default=None, description="Branch name for operations")
    message: str = Field(default="Auto-commit by AI agent", description="Commit message")
    files: List[str] = Field(default=["."], description="List of files to commit, default to all changed files")


class GitPythonTool(BaseTool):
    name: str = "git_python_tool"
    description: str = """Git operations using GitPython library:
    - 'init': Initialize git repository
    - 'create_branch': Create and switch to a new branch with format 'ai-task-<timestamp>' if branch_name not provided
    - 'checkout_branch': Switch to an existing branch
    - 'commit': Commit current changes with message
    - 'push': Push current branch to remote
    - 'status': Get git status
    - 'diff': Get git diff
    Usage: {'operation': 'create_branch', 'branch_name': 'feature/new-feature', 'message': 'Initial commit'}"""
    args_schema: Type[BaseModel] = GitPythonToolInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for git operations")

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir or os.getcwd()

    def _run(self, operation: str, branch_name: str = None, message: str = "Auto-commit by AI agent", files: List[str] = ["."]) -> str:
        """Execute git operations using GitPython"""
        
        try:
            # Change to the project directory
            original_dir = os.getcwd()
            os.chdir(self.root_dir)

            result = ""

            if operation == "init":
                result = self._init_repo()
            elif operation == "create_branch":
                if not branch_name:
                    # Generate a unique branch name based on timestamp if not provided
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    branch_name = f"ai-task-{timestamp}"
                result = self._create_branch(branch_name)
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
            else:
                result = f"Error: Unknown operation '{operation}'. Supported operations: init, create_branch, checkout_branch, commit, push, status, diff"

        except Exception as e:
            result = f"Error during git operation: {str(e)}"
        finally:
            # Restore original directory
            os.chdir(original_dir)

        return str(result)

    def _init_repo(self) -> str:
        """Initialize a git repository using GitPython"""
        try:
            # Check if repo already exists
            try:
                repo = Repo(self.root_dir)
                return f"Git repository already exists at: {self.root_dir}"
            except InvalidGitRepositoryError:
                # Repository doesn't exist, initialize it
                repo = Repo.init(self.root_dir)
                
                # Configure git user
                with repo.config_writer() as git_config:
                    git_config.set_value("user", "name", "AI-Agent")
                    git_config.set_value("user", "email", "ai-agent@vibesdlc.com")
                    git_config.release()

                # Check if there are any commits
                try:
                    # If there are commits, return success
                    repo.head.commit
                    return f"Git repository initialized successfully at: {self.root_dir}"
                except ValueError:
                    # No commits exist, create an initial commit
                    gitkeep_path = os.path.join(self.root_dir, ".gitkeep")
                    if not os.path.exists(gitkeep_path):
                        with open(gitkeep_path, "w") as f:
                            f.write("# Initial commit to create main branch\n")
                    
                    # Add and commit the file
                    repo.index.add([".gitkeep"])
                    commit = repo.index.commit("Initial commit")
                    
                    return f"Git repository initialized successfully with initial commit at: {self.root_dir}"
        
        except Exception as e:
            return f"Git init failed: {str(e)}"

    def _create_branch(self, branch_name: str) -> str:
        """Create and switch to a new branch"""
        try:
            repo = Repo(self.root_dir)

            # Check if branch already exists
            existing_branch = None
            for ref in repo.branches:
                if ref.name == branch_name:
                    existing_branch = ref
                    break

            if existing_branch:
                # Checkout existing branch
                repo.heads[branch_name].checkout()
                return f"Switched to existing branch '{branch_name}'"
            else:
                # Create and checkout new branch
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
                return f"Created and switched to new branch '{branch_name}'"

        except Exception as e:
            return f"Failed to create branch '{branch_name}': {str(e)}"

    def _checkout_branch(self, branch_name: str) -> str:
        """Checkout an existing branch"""
        try:
            repo = Repo(self.root_dir)
            
            # Check if branch exists
            branch_exists = False
            for ref in repo.branches:
                if ref.name == branch_name:
                    branch_exists = True
                    break
            
            if not branch_exists:
                return f"Error: Branch '{branch_name}' does not exist"
            
            # Checkout the branch
            repo.heads[branch_name].checkout()
            return f"Switched to branch '{branch_name}'"
        
        except Exception as e:
            return f"Failed to checkout branch '{branch_name}': {str(e)}"

    def _commit_changes(self, message: str, files: List[str]) -> str:
        """Commit changes to the repository"""
        try:
            repo = Repo(self.root_dir)
            
            # If files list contains just ["."] (meaning all), add all changes
            if files == ["."]:
                # Add all changes
                repo.git.add(A=True)  # equivalent to git add .
            else:
                # Add specific files
                repo.index.add(files)
            
            # Check if there are any changes to commit
            if repo.is_dirty(untracked_files=True) or repo.index.diff("HEAD"):
                # Create commit
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
            
            # Get current branch
            if repo.head.is_detached:
                return "Error: Cannot push in detached HEAD state"
            
            current_branch = repo.active_branch
            branch_name = current_branch.name
            
            # Check if remote exists
            if len(repo.remotes) == 0:
                return f"No remote configured for branch '{branch_name}'"
            
            # Push the current branch
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
            
            # Get status using GitPython
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
            
            # Get list of changed files
            changed_files = [item.a_path for item in repo.index.diff(None)]
            untracked_files = repo.untracked_files
            
            all_files = changed_files + untracked_files
            
            if all_files:
                return "Changed files:\n" + "\n".join(all_files)
            else:
                return "Changed files:\n"
        
        except Exception as e:
            return f"Error getting diff: {str(e)}"