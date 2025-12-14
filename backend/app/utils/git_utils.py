"""Git command utilities for safe subprocess execution."""

import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class GitCommandError(Exception):
    """Exception raised when git command fails."""
    
    def __init__(self, command: List[str], returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Git command failed: {' '.join(command)}\nError: {stderr}")


def run_git_command(
    args: List[str],
    cwd: Optional[Path] = None,
    timeout: int = 30,
    capture_output: bool = True,
    check: bool = False
) -> subprocess.CompletedProcess:
    """Run git command with consistent error handling.
    
    Args:
        args: Git command arguments (e.g., ["worktree", "prune"])
        cwd: Working directory for command execution
        timeout: Command timeout in seconds
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        
    Returns:
        CompletedProcess instance with returncode, stdout, stderr
        
    Raises:
        GitCommandError: If check=True and command fails
        subprocess.TimeoutExpired: If command exceeds timeout
    """
    command = ["git"] + args
    
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        
        if check and result.returncode != 0:
            raise GitCommandError(
                command=command,
                returncode=result.returncode,
                stderr=result.stderr
            )
        
        return result
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Git command timeout: {' '.join(command)}")
        raise
    except Exception as e:
        logger.error(f"Git command error: {' '.join(command)} - {e}")
        raise


def git_worktree_prune(cwd: Path, timeout: int = 10) -> bool:
    """Prune git worktrees (remove stale entries).
    
    Args:
        cwd: Main workspace directory
        timeout: Command timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        result = run_git_command(
            ["worktree", "prune"],
            cwd=cwd,
            timeout=timeout
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Git worktree prune failed: {e}")
        return False


def git_worktree_remove(
    worktree_path: Path,
    cwd: Path,
    force: bool = True,
    timeout: int = 30
) -> bool:
    """Remove git worktree.
    
    Args:
        worktree_path: Path to worktree to remove
        cwd: Main workspace directory
        force: Use --force flag
        timeout: Command timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        args = ["worktree", "remove", str(worktree_path)]
        if force:
            args.append("--force")
        
        result = run_git_command(args, cwd=cwd, timeout=timeout)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Git worktree remove failed: {e}")
        return False


def git_branch_delete(
    branch_name: str,
    cwd: Path,
    force: bool = True,
    timeout: int = 10
) -> Tuple[bool, str]:
    """Delete git branch.
    
    Args:
        branch_name: Name of branch to delete
        cwd: Repository directory
        force: Use -D (force delete) instead of -d
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (success: bool, stderr: str)
    """
    try:
        flag = "-D" if force else "-d"
        result = run_git_command(
            ["branch", flag, branch_name],
            cwd=cwd,
            timeout=timeout
        )
        return result.returncode == 0, result.stderr
    except Exception as e:
        logger.error(f"Git branch delete failed: {e}")
        return False, str(e)


def git_fetch_all(cwd: Path, timeout: int = 60) -> bool:
    """Fetch all remotes.
    
    Args:
        cwd: Repository directory
        timeout: Command timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        result = run_git_command(
            ["fetch", "--all"],
            cwd=cwd,
            timeout=timeout
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Git fetch failed: {e}")
        return False


def git_pull(
    branch: str,
    remote: str = "origin",
    cwd: Optional[Path] = None,
    timeout: int = 60
) -> bool:
    """Pull from remote branch.
    
    Args:
        branch: Branch name to pull
        remote: Remote name (default: origin)
        cwd: Repository directory
        timeout: Command timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        result = run_git_command(
            ["pull", remote, branch],
            cwd=cwd,
            timeout=timeout
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Git pull failed: {e}")
        return False


def git_merge_abort(cwd: Path, timeout: int = 10) -> bool:
    """Abort merge operation.
    
    Args:
        cwd: Repository directory
        timeout: Command timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        result = run_git_command(
            ["merge", "--abort"],
            cwd=cwd,
            timeout=timeout
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Git merge abort failed: {e}")
        return False
