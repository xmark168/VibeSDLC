"""Workspace management tools for Tester Agent.

Mirrored from developer_v2's workspace_tools for consistency.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

logger = logging.getLogger(__name__)


# =============================================================================
# Story workspace helper - Get developer's workspace from Story model
# =============================================================================

def get_story_workspace(story_id: str) -> dict | None:
    """Get workspace path from Story model (created by Developer V2).
    
    Returns dict with workspace_path and branch_name if found, None otherwise.
    """
    from app.core.db import engine
    from app.models import Story
    
    try:
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id))
            if story and story.worktree_path:
                workspace_path = Path(story.worktree_path)
                if workspace_path.exists():
                    logger.info(f"[get_story_workspace] Found developer workspace: {workspace_path}")
                    return {
                        "workspace_path": str(workspace_path),
                        "branch_name": story.branch_name or f"story_{story_id.split('-')[-1][:8]}",
                        "main_workspace": str(workspace_path.parent.parent) if ".worktrees" in str(workspace_path) else str(workspace_path),
                    }
                else:
                    logger.warning(f"[get_story_workspace] Workspace path not found: {workspace_path}")
    except Exception as e:
        logger.warning(f"[get_story_workspace] Error: {e}")
    return None


# =============================================================================
# Git worktree management (mirrored from developer_v2)
# =============================================================================

def cleanup_old_worktree(main_workspace: Path, branch_name: str, agent_name: str = "Tester"):
    """Clean up existing worktree directory and branch.
    
    Mirrored from developer_v2's cleanup_old_worktree().
    """
    short_id = branch_name.replace("test_", "")
    # Use absolute path to ensure correct location
    worktree_path = (main_workspace.parent / f"ws_test_{short_id}").resolve()
    
    if worktree_path.exists():
        logger.info(f"[{agent_name}] Removing worktree: {worktree_path}")
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=str(main_workspace),
                capture_output=True,
                timeout=30,
            )
        except Exception as e:
            logger.warning(f"[{agent_name}] Git worktree remove failed: {e}")
        
        if worktree_path.exists():
            try:
                shutil.rmtree(worktree_path)
            except Exception as e:
                logger.error(f"[{agent_name}] Failed to remove directory: {e}")
    
    try:
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=str(main_workspace),
            capture_output=True,
            timeout=10,
        )
        logger.info(f"[{agent_name}] Deleted branch: {branch_name}")
    except Exception as e:
        logger.debug(f"[{agent_name}] Branch delete (may not exist): {e}")


def setup_git_worktree(
    story_id: str,
    main_workspace: Path | str,
    agent_name: str = "Tester"
) -> dict:
    """Setup git worktree for a test task.
    
    Mirrored from developer_v2's setup_git_worktree().
    """
    # Ensure absolute path for correct worktree location
    main_workspace = Path(main_workspace).resolve()
    short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
    branch_name = f"test_{short_id}"
    
    if not main_workspace.exists():
        logger.error(f"[{agent_name}] Workspace does not exist: {main_workspace}")
        return {
            "workspace_path": str(main_workspace),
            "branch_name": branch_name,
            "main_workspace": str(main_workspace),
            "workspace_ready": False,
        }
    
    # Check if it's a valid git repo
    status_result = subprocess.run(
        ["git", "status"],
        cwd=str(main_workspace),
        capture_output=True,
        text=True,
        timeout=10,
    )
    
    if status_result.returncode != 0:
        logger.error(f"[{agent_name}] Not a git repo: {main_workspace}")
        return {
            "workspace_path": str(main_workspace),
            "branch_name": branch_name,
            "main_workspace": str(main_workspace),
            "workspace_ready": False,
        }
    
    # Clean up old worktree (like developer_v2)
    cleanup_old_worktree(main_workspace, branch_name, agent_name)
    
    logger.info(f"[{agent_name}] Creating worktree for '{branch_name}'")
    
    # Get current branch
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(main_workspace),
        capture_output=True,
        text=True,
        timeout=10,
    )
    current_branch = result.stdout.strip() if result.returncode == 0 else "main"
    
    # Create new branch from current
    subprocess.run(
        ["git", "branch", branch_name, current_branch],
        cwd=str(main_workspace),
        capture_output=True,
        timeout=30,
    )
    
    # Create worktree with absolute path
    worktree_path = (main_workspace.parent / f"ws_test_{short_id}").resolve()
    logger.info(f"[{agent_name}] Worktree path: {worktree_path}")
    worktree_result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch_name],
        cwd=str(main_workspace),
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    logger.info(f"[{agent_name}] Result: {worktree_result.stdout or worktree_result.stderr}")
    
    workspace_ready = worktree_path.exists() and worktree_path.is_dir()
    
    if not workspace_ready:
        logger.warning(f"[{agent_name}] Worktree not created, using main")
        worktree_path = main_workspace
    
    return {
        "workspace_path": str(worktree_path),
        "branch_name": branch_name,
        "main_workspace": str(main_workspace),
        "workspace_ready": workspace_ready,
    }


def commit_workspace_changes(
    workspace_path: str | Path,
    title: str,
    branch_name: str = "unknown",
    agent_name: str = "Tester"
) -> dict:
    """Commit changes in a workspace.
    
    Mirrored from developer_v2's commit_workspace_changes().
    """
    if not workspace_path:
        return {"success": True, "message": "No workspace to commit"}
    
    workspace_path = Path(workspace_path)
    
    # Check status
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(workspace_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    
    if not status_result.stdout.strip():
        return {"success": True, "message": "No changes to commit"}
    
    # Stage all changes
    subprocess.run(
        ["git", "add", "-A"],
        cwd=str(workspace_path),
        capture_output=True,
        timeout=30,
    )
    
    # Commit
    commit_msg = f"test: {title[:50]}"
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=str(workspace_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    logger.info(f"[{agent_name}] Committed on '{branch_name}': {commit_result.stdout or commit_result.stderr}")
    
    if commit_result.returncode == 0:
        return {"success": True, "message": f"Committed: {commit_msg}"}
    return {"success": False, "message": commit_result.stderr[:200]}


# =============================================================================
# Context helpers (mirrored from developer_v2)
# =============================================================================

def get_agents_md(workspace_path: str | Path) -> str:
    """Read AGENTS.md from workspace root.
    
    Mirrored from developer_v2's get_agents_md().
    """
    if not workspace_path:
        return ""
    agents_path = Path(workspace_path) / "AGENTS.md"
    if agents_path.exists():
        try:
            return agents_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read AGENTS.md: {e}")
    return ""


def get_project_context(workspace_path: str | Path) -> str:
    """Read project context files (README.md, package.json summary).
    
    Mirrored from developer_v2's get_project_context().
    """
    if not workspace_path:
        return ""
    
    workspace_path = Path(workspace_path)
    parts = []
    
    readme_path = workspace_path / "README.md"
    if readme_path.exists():
        try:
            content = readme_path.read_text(encoding="utf-8")[:2000]
            parts.append(f"## README.md\n{content}")
        except Exception:
            pass
    
    pkg_path = workspace_path / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            parts.append(
                f"## package.json\n"
                f"name: {pkg.get('name', 'unknown')}\n"
                f"dependencies: {list(pkg.get('dependencies', {}).keys())[:10]}"
            )
        except Exception:
            pass
    
    return "\n\n".join(parts)


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
