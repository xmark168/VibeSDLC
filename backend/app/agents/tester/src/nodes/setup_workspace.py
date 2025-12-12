"""Setup workspace node - Setup git workspace/branch for test generation."""
import logging
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.skills import SkillRegistry
from app.agents.tester.src.tools.workspace_tools import (
    setup_git_worktree,
    get_agents_md,
    get_project_context,
    get_story_workspace,
)
from app.core.db import engine
from app.models import Project

logger = logging.getLogger(__name__)


def _get_project_path(project_id: str) -> Path | None:
    """Get project path from database."""
    try:
        with Session(engine) as session:
            project = session.get(Project, UUID(project_id))
            if project and project.project_path:
                return Path(project.project_path)
    except Exception as e:
        logger.warning(f"[_get_project_path] Error: {e}")
    return None


def _get_tech_stack(project_id: str) -> str:
    """Get tech stack from project."""
    try:
        with Session(engine) as session:
            project = session.get(Project, UUID(project_id))
            if project:
                return project.tech_stack or "nextjs"
    except Exception as e:
        logger.warning(f"[_get_tech_stack] Error: {e}")
    return "nextjs"


async def setup_workspace(state: TesterState, agent=None) -> dict:
    """Setup git workspace/branch for test generation with interrupt support."""
    from langgraph.types import interrupt
    from app.agents.tester.src.graph import check_interrupt_signal
    
    logger.info("[NODE] setup_workspace")
    
    # Check for pause/cancel signal
    story_id = state.get("story_id", "")
    if story_id:
        signal = check_interrupt_signal(story_id)
        if signal:
            logger.info(f"[setup_workspace] Interrupt signal received: {signal}")
            interrupt({"reason": signal, "story_id": story_id, "node": "setup_workspace"})
    
    try:
        # Get IDs - support both story_id and task_id for compatibility
        story_id = state.get("story_id", state.get("task_id", "unknown"))
        project_id = state.get("project_id", "")
        
        if state.get("workspace_ready"):
            logger.info("[setup_workspace] Workspace already ready, skipping")
            return {}
        
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        branch_name = f"test_{short_id}"
        
        is_reusing_dev_workspace = False
        story_workspace = get_story_workspace(story_id)
        if story_workspace:
            logger.info(f"[setup_workspace] Using developer's workspace from Story: {story_workspace['workspace_path']}")
            workspace_info = {
                "workspace_path": story_workspace["workspace_path"],
                "branch_name": story_workspace["branch_name"],
                "main_workspace": story_workspace["main_workspace"],
                "workspace_ready": True,
            }
            is_reusing_dev_workspace = True
        elif state.get("workspace_path") and Path(state.get("workspace_path", "")).exists():
            existing_workspace = state.get("workspace_path", "")
            logger.info(f"[setup_workspace] Reusing existing workspace from state: {existing_workspace}")
            workspace_info = {
                "workspace_path": existing_workspace,
                "branch_name": branch_name,
                "main_workspace": state.get("main_workspace", existing_workspace),
                "workspace_ready": True,
            }
        else:
            logger.info(f"[setup_workspace] Creating new workspace for branch '{branch_name}'")
            
            main_workspace = None
            if agent:
                if hasattr(agent, 'main_workspace'):
                    main_workspace = agent.main_workspace
                elif hasattr(agent, 'workspace_path'):
                    main_workspace = agent.workspace_path
            
            if not main_workspace:
                project_path = _get_project_path(project_id)
                if project_path:
                    main_workspace = str(project_path)
            
            if not main_workspace:
                logger.warning("[setup_workspace] No workspace path available")
                return {
                    "workspace_ready": False,
                    "index_ready": False,
                    "error": "No workspace path configured",
                }
            
            workspace_info = setup_git_worktree(
                story_id=story_id,
                main_workspace=main_workspace,
                agent_name="Tester"
            )
        
        index_ready = False
        workspace_path = workspace_info.get("workspace_path", "")
        
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
        
        tech_stack = state.get("tech_stack") or _get_tech_stack(project_id)
        skill_registry = SkillRegistry.load(tech_stack)
        logger.info(f"[setup_workspace] Loaded SkillRegistry for '{tech_stack}' with {len(skill_registry.skills)} skills")
        
        if is_reusing_dev_workspace:
            logger.info("[setup_workspace] Skipping setup steps - reusing developer's workspace")
        
        return {
            "workspace_path": workspace_info["workspace_path"],
            "branch_name": workspace_info["branch_name"],
            "main_workspace": workspace_info["main_workspace"],
            "workspace_ready": workspace_info["workspace_ready"],
            "index_ready": index_ready,
            "project_path": workspace_path,
            "agents_md": agents_md,
            "project_context": project_context,
            # Skill registry
            "tech_stack": tech_stack,
            "skill_registry": skill_registry,
            "available_skills": skill_registry.get_skill_ids(),
        }
        
    except Exception as e:
        from langgraph.errors import GraphInterrupt
        if isinstance(e, GraphInterrupt):
            raise
        logger.error(f"[setup_workspace] Error: {e}", exc_info=True)
        return {
            "workspace_ready": False,
            "error": f"Workspace setup failed: {str(e)}",
        }
