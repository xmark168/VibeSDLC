"""Tester-specific workspace tools.

Common workspace utilities (setup_git_worktree, get_agents_md, etc.) 
have been moved to app.utils.workspace_utils for sharing across all agents.

This module contains only tester-specific tools like cleanup_worktree, 
merge_to_main, and revert_test_changes.
"""

import logging
import shutil
import subprocess
from pathlib import Path

# Import shared utilities from central location
from app.utils.workspace_utils import (
    setup_git_worktree,
    commit_workspace_changes,
    get_agents_md,
    get_project_context,
    get_story_workspace,
)

logger = logging.getLogger(__name__)

# Re-export shared functions for backward compatibility
__all__ = [
    "setup_git_worktree",
    "commit_workspace_changes",
    "get_agents_md",
    "get_project_context",
    "get_story_workspace",
    "cleanup_worktree",
    "merge_to_main",
    "revert_test_changes",
]


# =============================================================================
# Additional tester-specific tools
# =============================================================================

def cleanup_worktree(main_workspace: str, branch_name: str) -> bool:
    """Cleanup git worktree after task completion."""
    if not main_workspace or not branch_name:
        return False
    
    try:
        short_id = branch_name.replace("test_", "")
        # Use absolute path to ensure correct location
        worktree_path = (Path(main_workspace).parent / f"ws_test_{short_id}").resolve()
        
        if not worktree_path.exists():
            return True  # Already cleaned up
        
        # Remove worktree
        result = subprocess.run(
            ["git", "worktree", "remove", str(worktree_path), "--force"],
            cwd=main_workspace,
            capture_output=True,
            timeout=60,
        )
        
        if result.returncode == 0:
            logger.info(f"[cleanup_worktree] Removed worktree: {worktree_path}")
            
            # Delete branch
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=main_workspace,
                capture_output=True,
                timeout=30,
            )
            return True
        else:
            logger.warning(f"[cleanup_worktree] Failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"[cleanup_worktree] Error: {e}")
        return False


def merge_to_main(workspace_path: str, branch_name: str, main_branch: str = "main") -> dict:
    """Merge test branch to main branch."""
    if not workspace_path or not branch_name:
        return {"success": False, "message": "Invalid parameters"}
    
    try:
        # Checkout main
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=workspace_path,
            capture_output=True,
            timeout=30,
        )
        
        # Merge branch
        result = subprocess.run(
            ["git", "merge", branch_name, "--no-edit"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode == 0:
            logger.info(f"[merge_to_main] Merged {branch_name} to {main_branch}")
            return {"success": True, "message": f"Merged {branch_name} to {main_branch}"}
        else:
            logger.warning(f"[merge_to_main] Merge failed: {result.stderr}")
            return {"success": False, "message": result.stderr[:200]}
            
    except Exception as e:
        logger.error(f"[merge_to_main] Error: {e}")
        return {"success": False, "message": str(e)}


def revert_test_changes(workspace_path: str | Path) -> bool:
    """Revert all uncommitted changes in test workspace.
    
    Used when tests fail to clean up generated test files.
    """
    if not workspace_path:
        return False
    
    workspace_path = Path(workspace_path)
    if not workspace_path.exists():
        return False
    
    try:
        # Discard all staged and unstaged changes
        subprocess.run(
            ["git", "checkout", "."],
            cwd=str(workspace_path),
            capture_output=True,
            timeout=30,
        )
        # Remove untracked files (generated test files)
        subprocess.run(
            ["git", "clean", "-fd"],
            cwd=str(workspace_path),
            capture_output=True,
            timeout=30,
        )
        logger.info(f"[revert_test_changes] Reverted all changes in {workspace_path}")
        return True
    except Exception as e:
        logger.warning(f"[revert_test_changes] Error: {e}")
        return False
