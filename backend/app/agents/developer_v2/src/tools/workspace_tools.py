"""Workspace management tools for Developer V2."""

import logging
from pathlib import Path
from app.agents.developer.tools.git_python_tool import GitPythonTool

logger = logging.getLogger(__name__)


def setup_git_worktree(
    story_id: str,
    main_workspace: Path | str,
    agent_name: str = "Developer"
) -> dict:
    """
    Setup git worktree for a story task.
    Creates a separate worktree for isolation from main workspace.
    """
    main_workspace = Path(main_workspace)
    short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
    branch_name = f"story_{short_id}"
    
    git_tool = GitPythonTool(root_dir=str(main_workspace))
    
    # 1. Initialize git in main workspace if needed
    status_result = git_tool._run("status")
    if "not a git repository" in status_result.lower() or "fatal" in status_result.lower():
        logger.info(f"[{agent_name}] Initializing git in main workspace")
        git_tool._run("init")
        git_tool._run("commit", message="Initial commit", files=["."])
    
    # 2. Create worktree for this story
    logger.info(f"[{agent_name}] Creating worktree for branch '{branch_name}'")
    worktree_result = git_tool._run("create_worktree", branch_name=branch_name)
    logger.info(f"[{agent_name}] Worktree result: {worktree_result}")
    
    # 3. Determine worktree path (git creates ws_story_{id} next to main)
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
