from typing import List, Optional, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from git import Repo, InvalidGitRepositoryError
import os
from datetime import datetime


# Tool 1: Git Init
class GitInitToolInput(BaseModel):
    """Input for git init"""
    message: str = Field(default="Initial commit", description="Commit message for initial commit")


class GitInitTool(BaseTool):
    name: str = "git_init_tool"
    description: str = "Initialize a git repository with initial commit"
    args_schema: Type[BaseModel] = GitInitToolInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for git operations")

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir or os.getcwd()

    def _run(self, message: str = "Initial commit") -> str:
        """Initialize git repository"""
        original_dir = os.getcwd()
        os.chdir(self.root_dir)
        
        try:
            # Check if already a git repo
            try:
                repo = Repo(self.root_dir)
                return "Git repository already exists"
            except InvalidGitRepositoryError:
                # Initialize new repo
                repo = Repo.init(self.root_dir)
                
                # Set config
                with repo.config_writer() as git_config:
                    git_config.set_value("user", "name", "AI-Agent")
                    git_config.set_value("user", "email", "ai-agent@vibesdlc.com")
                
                # If no commits exist, create initial commit
                if not repo.heads:
                    gitkeep_path = os.path.join(self.root_dir, ".gitkeep")
                    with open(gitkeep_path, "w") as f:
                        f.write("# Initial commit by AI agent\n")
                    
                    repo.index.add([".gitkeep"])
                    repo.index.commit(message)
                
                return "Git repository initialized successfully"
        except Exception as e:
            return f"Git init failed: {str(e)}"
        finally:
            os.chdir(original_dir)


# Tool 2: Git Commit
class GitCommitToolInput(BaseModel):
    """Input for git commit"""
    message: str = Field(default="Auto-commit by AI agent", description="Commit message")
    files: List[str] = Field(default=["."], description="Files to commit, use ['.'] for all changes")


class GitCommitTool(BaseTool):
    name: str = "git_commit_tool"
    description: str = "Commit changes to git repository"
    args_schema: Type[BaseModel] = GitCommitToolInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for git operations")

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir or os.getcwd()

    def _run(self, message: str = "Auto-commit by AI agent", files: List[str] = ["."]) -> str:
        """Commit changes"""
        original_dir = os.getcwd()
        os.chdir(self.root_dir)
        
        try:
            repo = Repo(self.root_dir)
            
            # Add files
            if files == ["."]:
                repo.git.add(A=True)  # Add all changed files
            else:
                repo.index.add(files)
            
            # Commit
            if repo.is_dirty(untracked_files=True) or repo.index.diff("HEAD"):
                repo.index.commit(message)
                return f"Committed changes: {message}"
            else:
                return "No changes to commit"
        except Exception as e:
            return f"Git commit failed: {str(e)}"
        finally:
            os.chdir(original_dir)


# Tool 3: Git Create Branch
class GitCreateBranchToolInput(BaseModel):
    """Input for git create branch"""
    branch_name: str = Field(..., description="Name of the branch to create")


class GitCreateBranchTool(BaseTool):
    name: str = "git_create_branch_tool"
    description: str = "Create a new git branch"
    args_schema: Type[BaseModel] = GitCreateBranchToolInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for git operations")

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir or os.getcwd()

    def _run(self, branch_name: str) -> str:
        """Create a new branch"""
        original_dir = os.getcwd()
        os.chdir(self.root_dir)
        
        try:
            repo = Repo(self.root_dir)
            
            # Check if branch exists
            if branch_name in repo.heads:
                repo.heads[branch_name].checkout()
                return f"Switched to existing branch: {branch_name}"
            else:
                # Create new branch
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
                return f"Created and switched to branch: {branch_name}"
        except Exception as e:
            return f"Git create branch failed: {str(e)}"
        finally:
            os.chdir(original_dir)


# Tool 4: Git Checkout Branch
class GitCheckoutBranchToolInput(BaseModel):
    """Input for git checkout branch"""
    branch_name: str = Field(..., description="Name of the branch to checkout")


class GitCheckoutBranchTool(BaseTool):
    name: str = "git_checkout_branch_tool"
    description: str = "Checkout an existing git branch"
    args_schema: Type[BaseModel] = GitCheckoutBranchToolInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for git operations")

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir or os.getcwd()

    def _run(self, branch_name: str) -> str:
        """Checkout branch"""
        original_dir = os.getcwd()
        os.chdir(self.root_dir)
        
        try:
            repo = Repo(self.root_dir)
            
            if branch_name not in repo.heads:
                return f"Branch {branch_name} does not exist"
            
            repo.heads[branch_name].checkout()
            return f"Checked out branch: {branch_name}"
        except Exception as e:
            return f"Git checkout failed: {str(e)}"
        finally:
            os.chdir(original_dir)


# Tool 5: Git Status
class GitStatusTool(BaseTool):
    name: str = "git_status_tool"
    description: str = "Get git status of the repository"
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for git operations")

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir or os.getcwd()

    def _run(self) -> str:
        """Get git status"""
        original_dir = os.getcwd()
        os.chdir(self.root_dir)
        
        try:
            repo = Repo(self.root_dir)
            
            # Get different types of files
            untracked = repo.untracked_files
            modified = [item.a_path for item in repo.index.diff(None)]
            staged = [item.a_path for item in repo.index.diff("HEAD")]
            
            status_lines = []
            if staged:
                status_lines.append("Staged files:")
                status_lines.extend([f"  A {f}" for f in staged])
            
            if modified:
                status_lines.append("Modified files:")
                status_lines.extend([f"  M {f}" for f in modified])
            
            if untracked:
                status_lines.append("Untracked files:")
                status_lines.extend([f"  ?? {f}" for f in untracked])
            
            if not (staged or modified or untracked):
                status_lines.append("Working directory clean")
            
            return "\n".join(status_lines)
        except Exception as e:
            return f"Git status failed: {str(e)}"
        finally:
            os.chdir(original_dir)


# Tool 6: Git Push
class GitPushTool(BaseTool):
    name: str = "git_push_tool"
    description: str = "Push current branch to remote repository"
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for git operations")

    def __init__(self, root_dir: str = None, **kwargs):
        super().__init__(**kwargs)
        self.root_dir = root_dir or os.getcwd()

    def _run(self) -> str:
        """Push to remote"""
        original_dir = os.getcwd()
        os.chdir(self.root_dir)
        
        try:
            repo = Repo(self.root_dir)
            
            if repo.head.is_detached:
                return "Cannot push in detached HEAD state"
            
            current_branch = repo.active_branch
            branch_name = current_branch.name
            
            if len(repo.remotes) == 0:
                return f"No remote found for branch {branch_name}"
            
            origin = repo.remotes.origin
            push_info = origin.push(refspec=f"{branch_name}:{branch_name}")
            
            if push_info and push_info[0].flags & push_info[0].ERROR:
                return f"Push failed: {push_info[0].summary}"
            else:
                return f"Pushed branch {branch_name} successfully"
        except Exception as e:
            return f"Git push failed: {str(e)}"
        finally:
            os.chdir(original_dir)