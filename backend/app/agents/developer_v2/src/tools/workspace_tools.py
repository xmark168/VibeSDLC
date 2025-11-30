"""Workspace management tools for Developer V2."""

import logging
import shutil
from pathlib import Path
from app.agents.developer.tools.git_python_tool import GitPythonTool

logger = logging.getLogger(__name__)


def cleanup_old_worktree(main_workspace: Path, branch_name: str, agent_name: str = "Developer"):
    """
    Clean up existing worktree directory and branch before creating a new one.
    Also unregisters the old CocoIndex task if exists.
    """
    short_id = branch_name.replace("story_", "")
    worktree_path = main_workspace.parent / f"ws_story_{short_id}"
    
    # Remove worktree directory if exists
    if worktree_path.exists():
        logger.info(f"[{agent_name}] Removing existing worktree directory: {worktree_path}")
        try:
            # First try to remove git worktree properly
            git_tool = GitPythonTool(root_dir=str(main_workspace))
            git_tool._run("remove_worktree", worktree_path=str(worktree_path))
        except Exception as e:
            logger.warning(f"[{agent_name}] Git worktree remove failed: {e}")
        
        # Force remove directory if still exists
        if worktree_path.exists():
            try:
                shutil.rmtree(worktree_path)
                logger.info(f"[{agent_name}] Removed directory: {worktree_path}")
            except Exception as e:
                logger.error(f"[{agent_name}] Failed to remove directory: {e}")
    
    # Try to delete the old branch if exists
    try:
        git_tool = GitPythonTool(root_dir=str(main_workspace))
        git_tool._run("delete_branch", branch_name=branch_name)
        logger.info(f"[{agent_name}] Deleted old branch: {branch_name}")
    except Exception as e:
        logger.debug(f"[{agent_name}] Branch delete (may not exist): {e}")
    
    # Unregister old CocoIndex task
    try:
        from app.agents.developer.project_manager import project_manager
        # Use branch_name as task_id approximation
        project_manager.unregister_task("", branch_name)
        logger.info(f"[{agent_name}] Unregistered old CocoIndex task: {branch_name}")
    except Exception as e:
        logger.debug(f"[{agent_name}] CocoIndex unregister (may not exist): {e}")


def setup_git_worktree(
    story_id: str,
    main_workspace: Path | str,
    agent_name: str = "Developer"
) -> dict:
    """
    Setup git worktree for a story task.
    Creates a separate worktree for isolation from main workspace.
    
    NOTE: Git should already be initialized in the workspace (copied from template).
    If not, worktree creation will fail and we fallback to main workspace.
    
    Auto-cleans up existing worktree directory if it exists.
    """
    main_workspace = Path(main_workspace)
    short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
    branch_name = f"story_{short_id}"
    
    # Check if workspace exists
    if not main_workspace.exists():
        logger.error(f"[{agent_name}] Workspace does not exist: {main_workspace}")
        return {
            "workspace_path": str(main_workspace),
            "branch_name": branch_name,
            "main_workspace": str(main_workspace),
            "workspace_ready": False,
        }
    
    git_tool = GitPythonTool(root_dir=str(main_workspace))
    
    # Verify git is ready (should exist from template copy)
    status_result = git_tool._run("status")
    if "not a git repository" in status_result.lower() or "fatal" in status_result.lower():
        logger.error(f"[{agent_name}] Workspace not a git repo (template issue?): {main_workspace}")
        return {
            "workspace_path": str(main_workspace),
            "branch_name": branch_name,
            "main_workspace": str(main_workspace),
            "workspace_ready": False,
        }
    
    # Clean up existing worktree/branch before creating new one
    cleanup_old_worktree(main_workspace, branch_name, agent_name)
    
    # Create worktree for this story
    logger.info(f"[{agent_name}] Creating worktree for branch '{branch_name}'")
    worktree_result = git_tool._run("create_worktree", branch_name=branch_name)
    logger.info(f"[{agent_name}] Worktree result: {worktree_result}")
    
    # Determine worktree path (git creates ws_story_{id} next to main)
    worktree_path = main_workspace.parent / f"ws_story_{short_id}"
    workspace_ready = worktree_path.exists() and worktree_path.is_dir()
    
    if workspace_ready:
        logger.info(f"[{agent_name}] Workspace ready: {worktree_path}")
    else:
        logger.warning(f"[{agent_name}] Worktree not created, using main workspace")
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
    agent_name: str = "Developer"
) -> str:
    """Commit changes in a workspace (worktree or main).
    
    Args:
        workspace_path: Path to workspace to commit
        title: Commit title (will be truncated to 50 chars)
        branch_name: Branch name for logging (optional)
        agent_name: Agent name for logging (optional)
        
    Returns:
        Commit result message
    """
    if not workspace_path:
        return "No workspace to commit"
    
    workspace_path = Path(workspace_path)
    git_tool = GitPythonTool(root_dir=str(workspace_path))
    
    # Check for changes
    status = git_tool._run("status")
    if "nothing to commit" in status.lower():
        return "No changes to commit"
    
    # Commit changes
    commit_msg = f"feat: {title[:50]}"
    result = git_tool._run("commit", message=commit_msg, files=["."])
    logger.info(f"[{agent_name}] Committed changes on branch '{branch_name}': {result}")
    
    return result
