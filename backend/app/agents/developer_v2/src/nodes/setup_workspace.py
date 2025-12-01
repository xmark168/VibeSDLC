"""Setup workspace node - Setup git workspace/branch for code modification."""
import logging

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools import (
    setup_git_worktree,
    index_workspace,
    get_agents_md,
    get_project_context,
)

logger = logging.getLogger(__name__)


async def setup_workspace(state: DeveloperState, agent=None) -> DeveloperState:
    """Setup git workspace/branch for code modification."""
    print("[NODE] setup_workspace")
    try:
        story_id = state.get("story_id", state.get("task_id", "unknown"))
        
        if state.get("workspace_ready"):
            logger.info("[setup_workspace] Workspace already ready, skipping")
            return state
        
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        branch_name = f"story_{short_id}"
        
        logger.info(f"[setup_workspace] Setting up workspace for branch '{branch_name}'")
        
        if hasattr(agent, 'main_workspace'):
            main_workspace = agent.main_workspace
        elif hasattr(agent, 'workspace_path'):
            main_workspace = agent.workspace_path
        else:
            logger.warning("[setup_workspace] Agent has no workspace path attribute")
            return {**state, "workspace_ready": False, "index_ready": False}
        
        workspace_info = setup_git_worktree(
            story_id=story_id,
            main_workspace=main_workspace,
            agent_name=agent.name
        )
        
        index_ready = False
        workspace_path = workspace_info.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or story_id
        
        if workspace_path:
            index_ready = index_workspace(project_id, workspace_path, task_id)
            if not index_ready:
                # Soft fail - continue without semantic search instead of crashing
                logger.warning(f"[setup_workspace] CocoIndex indexing failed, continuing without semantic search")
                index_ready = False
            else:
                logger.info(f"[setup_workspace] Indexed workspace with CocoIndex")
        
        project_context = ""
        agents_md = ""
        if workspace_path:
            try:
                agents_md = get_agents_md(workspace_path)
                project_context = get_project_context(workspace_path)
                if agents_md:
                    logger.info(f"[setup_workspace] Loaded AGENTS.md: {len(agents_md)} chars")
            except Exception as ctx_err:
                logger.warning(f"[setup_workspace] Failed to load project context: {ctx_err}")
        
        return {
            **state,
            "workspace_path": workspace_info["workspace_path"],
            "branch_name": workspace_info["branch_name"],
            "main_workspace": workspace_info["main_workspace"],
            "workspace_ready": workspace_info["workspace_ready"],
            "index_ready": index_ready,
            "agents_md": agents_md,
            "project_context": project_context,
        }
        
    except Exception as e:
        logger.error(f"[setup_workspace] Error: {e}", exc_info=True)
        return {
            **state,
            "workspace_ready": False,
            "error": f"Workspace setup failed: {str(e)}",
        }
