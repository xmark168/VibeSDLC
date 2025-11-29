"""Git Tools using LangChain @tool decorator."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from langchain_core.tools import tool
from git import Repo, InvalidGitRepositoryError


# Global context for git operations
_git_context = {
    "root_dir": None,
}


def set_git_context(root_dir: str = None):
    """Set global context for git tools."""
    if root_dir:
        _git_context["root_dir"] = root_dir


def _get_root_dir() -> str:
    """Get root directory from context or use cwd."""
    return _git_context.get("root_dir") or os.getcwd()


@tool
def git_init(message: str = "Initial commit") -> str:
    """
    Initialize a git repository with initial commit.
    """
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        try:
            repo = Repo(root_dir)
            return "Git repository already exists"
        except InvalidGitRepositoryError:
            repo = Repo.init(root_dir)
            
            with repo.config_writer() as git_config:
                git_config.set_value("user", "name", "AI-Agent")
                git_config.set_value("user", "email", "ai-agent@vibesdlc.com")
            
            if not repo.heads:
                gitkeep_path = os.path.join(root_dir, ".gitkeep")
                with open(gitkeep_path, "w") as f:
                    f.write("# Initial commit by AI agent\n")
                repo.index.add([".gitkeep"])
                repo.index.commit(message)
            
            return "Git repository initialized successfully"
    except Exception as e:
        return f"Git init failed: {str(e)}"
    finally:
        os.chdir(original_dir)


@tool
def git_status() -> str:
    """Get git status of the repository showing modified, staged, and untracked files."""
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        
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


@tool
def git_commit(message: str = "Auto-commit by AI agent", files: str = ".") -> str:
    """Commit changes to git repository.

    Args:
        message: Commit message
        files: Files to commit, comma-separated or '.' for all changes
    """
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        
        file_list = [f.strip() for f in files.split(",")] if files != "." else ["."]
        
        if file_list == ["."]:
            repo.git.add(A=True)
        else:
            repo.index.add(file_list)
        
        if repo.is_dirty(untracked_files=True) or repo.index.diff("HEAD"):
            repo.index.commit(message)
            return f"Committed changes: {message}"
        return "No changes to commit"
    except Exception as e:
        return f"Git commit failed: {str(e)}"
    finally:
        os.chdir(original_dir)


@tool
def git_create_branch(branch_name: Optional[str] = None) -> str:
    """Create and switch to a new git branch.

    Args:
        branch_name: Name of branch to create. Auto-generates if not provided.
    """
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        
        if not branch_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            branch_name = f"ai-task-{timestamp}"
        
        if branch_name in repo.heads:
            repo.heads[branch_name].checkout()
            return f"Switched to existing branch: {branch_name}"
        
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        return f"Created and switched to branch: {branch_name}"
    except Exception as e:
        return f"Git create branch failed: {str(e)}"
    finally:
        os.chdir(original_dir)


@tool
def git_checkout(branch_name: str) -> str:
    """Switch to an existing git branch.

    Args:
        branch_name: Name of branch to checkout
    """
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        
        if branch_name not in repo.heads:
            return f"Branch {branch_name} does not exist"
        
        repo.heads[branch_name].checkout()
        return f"Checked out branch: {branch_name}"
    except Exception as e:
        return f"Git checkout failed: {str(e)}"
    finally:
        os.chdir(original_dir)


@tool
def git_push() -> str:
    """Push current branch to remote repository."""
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        
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
        return f"Pushed branch {branch_name} successfully"
    except Exception as e:
        return f"Git push failed: {str(e)}"
    finally:
        os.chdir(original_dir)


@tool
def git_diff() -> str:
    """Get list of changed files in the repository."""
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        
        changed_files = [item.a_path for item in repo.index.diff(None)]
        untracked_files = repo.untracked_files
        
        all_files = changed_files + untracked_files
        
        if all_files:
            return "Changed files:\n" + "\n".join(all_files)
        return "No changes detected"
    except Exception as e:
        return f"Git diff failed: {str(e)}"
    finally:
        os.chdir(original_dir)


@tool
def git_merge(branch_name: str) -> str:
    """Merge a branch into the current branch.

    Args:
        branch_name: Name of branch to merge
    """
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        current_branch = repo.active_branch.name
        
        if branch_name not in [h.name for h in repo.heads]:
            return f"Error: Branch '{branch_name}' does not exist"
        
        repo.git.merge(branch_name, m=f"Merge branch '{branch_name}' into {current_branch}")
        return f"Merged '{branch_name}' into '{current_branch}'"
    except Exception as e:
        error_msg = str(e)
        if "conflict" in error_msg.lower():
            return f"Merge conflict when merging '{branch_name}': {error_msg}"
        return f"Merge failed: {error_msg}"
    finally:
        os.chdir(original_dir)


@tool
def git_delete_branch(branch_name: str, force: bool = False) -> str:
    """Delete a local git branch.

    Args:
        branch_name: Name of branch to delete
        force: Force delete even if not merged
    """
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        
        if branch_name not in [h.name for h in repo.heads]:
            return f"Error: Branch '{branch_name}' does not exist"
        
        if repo.active_branch.name == branch_name:
            return f"Error: Cannot delete current branch '{branch_name}'"
        
        repo.delete_head(branch_name, force=force)
        return f"Deleted branch '{branch_name}'"
    except Exception as e:
        return f"Delete branch failed: {str(e)}"
    finally:
        os.chdir(original_dir)


@tool
def git_create_worktree(branch_name: str) -> str:
    """Create a worktree for isolated development on a branch.

    Args:
        branch_name: Name of branch for worktree
    """
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        
        if branch_name.startswith("story_"):
            story_id = branch_name.replace("story_", "")
            worktree_name = f"ws_story_{story_id}"
        else:
            worktree_name = f"ws_{branch_name}"
        
        worktree_path = Path(root_dir).parent / worktree_name
        
        if worktree_path.exists() and any(worktree_path.iterdir()):
            return f"Worktree directory '{worktree_path}' already exists"
        
        if branch_name not in repo.heads:
            current_branch = repo.active_branch
            new_branch = repo.create_head(branch_name, current_branch.commit)
        else:
            new_branch = repo.heads[branch_name]
        
        repo.git.worktree('add', str(worktree_path), str(new_branch))
        return f"Created worktree at '{worktree_path}' for branch '{branch_name}'"
    except Exception as e:
        return f"Failed to create worktree: {str(e)}"
    finally:
        os.chdir(original_dir)


@tool
def git_remove_worktree(worktree_path: str) -> str:
    """Remove a git worktree.

    Args:
        worktree_path: Path to the worktree to remove
    """
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        repo.git.worktree('remove', worktree_path)
        return f"Removed worktree at '{worktree_path}'"
    except Exception as e:
        return f"Failed to remove worktree: {str(e)}"
    finally:
        os.chdir(original_dir)


@tool
def git_list_worktrees() -> str:
    """List all git worktrees."""
    if not GIT_AVAILABLE:
        return "Error: GitPython not installed"
    
    root_dir = _get_root_dir()
    original_dir = os.getcwd()
    os.chdir(root_dir)
    
    try:
        repo = Repo(root_dir)
        worktrees_output = repo.git.worktree('list')
        return f"Worktrees:\n{worktrees_output}"
    except Exception as e:
        return f"Failed to list worktrees: {str(e)}"
    finally:
        os.chdir(original_dir)
