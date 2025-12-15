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


def git_with_retry(
    cmd: List[str],
    cwd: str,
    retries: int = 3,
    timeout: int = 30
) -> subprocess.CompletedProcess:
    """Execute git command with retry logic.
    
    Args:
        cmd: Git command as list (e.g., ["git", "add", "file.txt"])
        cwd: Working directory
        retries: Number of retry attempts
        timeout: Command timeout in seconds
        
    Returns:
        CompletedProcess instance
        
    Raises:
        Exception: If all retries fail
    """
    import time
    
    for attempt in range(retries):
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode == 0:
                return result
            
            # If failed but not last attempt, retry
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            
            # Last attempt failed
            raise Exception(f"Command failed: {' '.join(cmd)}, stderr: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
    
    raise Exception(f"All {retries} attempts failed for: {' '.join(cmd)}")


def git_commit_step(
    workspace_path: str,
    step_num: int,
    description: str,
    files: Optional[List[str]] = None
) -> bool:
    """Commit changes after a successful implement step.
    
    Args:
        workspace_path: Path to git repository
        step_num: Step number for commit message
        description: Description of changes
        files: Optional list of specific files to commit (None = all changes)
        
    Returns:
        True if successful, False otherwise
    """
    import os
    
    if not workspace_path:
        logger.warning("[git_commit_step] workspace_path is empty")
        return False
    
    workspace = Path(workspace_path)
    if not workspace.exists():
        logger.warning(f"[git_commit_step] workspace does not exist: {workspace_path}")
        return False
    
    workspace_path = str(workspace.resolve())
    
    try:
        # Stage files with retry
        if files:
            for f in files:
                try:
                    file_path = str((workspace / f).resolve()) if not os.path.isabs(f) else f
                    git_with_retry(["git", "add", file_path], cwd=workspace_path)
                except Exception:
                    pass  # Individual file add failure is OK
        else:
            git_with_retry(["git", "add", "-A"], cwd=workspace_path)
        
        # Check if there are staged changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=workspace_path,
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0:
            logger.debug(f"[git_commit_step] No changes to commit for step {step_num}")
            return True
        
        # Commit with WIP message
        msg = f"wip: step {step_num} - {description}"
        git_with_retry(["git", "commit", "-m", msg, "--no-verify"], cwd=workspace_path)
        logger.info(f"[git_commit_step] Committed step {step_num}: {description}")
        return True
        
    except Exception as e:
        logger.warning(f"[git_commit_step] Commit error: {e}")
        return False


def git_revert_uncommitted(workspace_path: str) -> bool:
    """Revert uncommitted changes (discard unstaged + remove untracked).
    
    Args:
        workspace_path: Path to git repository
        
    Returns:
        True if successful, False otherwise
    """
    if not workspace_path:
        logger.warning("[git_revert_uncommitted] workspace_path is empty")
        return False
    
    workspace = Path(workspace_path)
    if not workspace.exists():
        logger.warning(f"[git_revert_uncommitted] workspace does not exist: {workspace_path}")
        return False
    
    workspace_path = str(workspace.resolve())
    
    try:
        # Discard unstaged changes
        git_with_retry(["git", "checkout", "."], cwd=workspace_path)
        # Remove untracked files
        git_with_retry(["git", "clean", "-fd"], cwd=workspace_path)
        logger.info("[git_revert_uncommitted] Reverted uncommitted changes")
        return True
    except Exception as e:
        logger.warning(f"[git_revert_uncommitted] Revert error: {e}")
        return False


def git_reset_all(workspace_path: str, base_branch: str = "main") -> bool:
    """Reset all changes to base branch (hard reset to merge-base).
    
    Args:
        workspace_path: Path to git repository
        base_branch: Base branch name (default: main)
        
    Returns:
        True if successful, False otherwise
    """
    if not workspace_path:
        logger.warning("[git_reset_all] workspace_path is empty")
        return False
    
    workspace = Path(workspace_path)
    if not workspace.exists():
        logger.warning(f"[git_reset_all] workspace does not exist: {workspace_path}")
        return False
    
    workspace_path = str(workspace.resolve())
    
    try:
        # Get merge-base with origin
        result = subprocess.run(
            ["git", "merge-base", f"origin/{base_branch}", "HEAD"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            base_commit = result.stdout.strip()
            git_with_retry(["git", "reset", "--hard", base_commit], cwd=workspace_path)
            logger.info(f"[git_reset_all] Reset to {base_commit[:8]}")
        else:
            # Fallback: reset to origin/base_branch
            git_with_retry(["git", "reset", "--hard", f"origin/{base_branch}"], cwd=workspace_path)
            logger.info(f"[git_reset_all] Reset to origin/{base_branch}")
        
        return True
    except Exception as e:
        logger.warning(f"[git_reset_all] Reset error: {e}")
        return False


def git_squash_wip_commits(
    workspace_path: str,
    base_branch: str = "main",
    final_message: Optional[str] = None
) -> bool:
    """Squash all WIP commits into a single commit.
    
    Args:
        workspace_path: Path to git repository
        base_branch: Base branch name (default: main)
        final_message: Final commit message (default: "feat: implement story")
        
    Returns:
        True if successful, False otherwise
    """
    if not workspace_path:
        logger.warning("[git_squash_wip_commits] workspace_path is empty")
        return False
    
    workspace = Path(workspace_path)
    if not workspace.exists():
        logger.warning(f"[git_squash_wip_commits] workspace does not exist: {workspace_path}")
        return False
    
    workspace_path = str(workspace.resolve())
    
    try:
        # Get merge-base
        result = subprocess.run(
            ["git", "merge-base", f"origin/{base_branch}", "HEAD"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.warning("[git_squash_wip_commits] Could not find merge-base")
            return False
        
        base_commit = result.stdout.strip()
        
        # Soft reset to base
        git_with_retry(["git", "reset", "--soft", base_commit], cwd=workspace_path)
        
        # Commit with final message
        msg = final_message or "feat: implement story"
        git_with_retry(["git", "commit", "-m", msg, "--no-verify"], cwd=workspace_path)
        logger.info(f"[git_squash_wip_commits] Squashed commits: {msg}")
        return True
        
    except Exception as e:
        logger.warning(f"[git_squash_wip_commits] Squash error: {e}")
        return False
