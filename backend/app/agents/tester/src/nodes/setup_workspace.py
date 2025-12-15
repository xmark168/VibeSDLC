"""Setup workspace node - Setup git workspace/branch for test generation."""
import logging
from pathlib import Path

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.skills import SkillRegistry

logger = logging.getLogger(__name__)


async def setup_workspace(state: TesterState, agent=None) -> dict:
    """Setup workspace for test generation - reuses Developer's workspace only."""
    from langgraph.types import interrupt
    from app.agents.tester.src.utils.interrupt import check_interrupt_signal
    
    logger.info("[NODE] setup_workspace")
    
    # Check for pause/cancel signal
    story_id = state.get("story_id", "")
    if story_id:
        signal = check_interrupt_signal(story_id)
        if signal:
            logger.info(f"[setup_workspace] Interrupt signal received: {signal}")
            interrupt({"reason": signal, "story_id": story_id, "node": "setup_workspace"})
    
    try:
        story_id = state.get("story_id", state.get("task_id", "unknown"))
        project_id = state.get("project_id", "")
        
        if state.get("workspace_ready"):
            logger.info("[setup_workspace] Workspace already ready, skipping")
            return {}
        
        # Get workspace_path from state (passed from router via Story.worktree_path)
        workspace_path = state.get("workspace_path", "")
        branch_name = state.get("branch_name", "")
        
        # Validate workspace exists
        if not workspace_path or not Path(workspace_path).exists():
            error_msg = (
                "No workspace available. Tester requires Developer to create workspace first. "
                f"workspace_path={workspace_path}"
            )
            logger.error(f"[setup_workspace] {error_msg}")
            return {
                "workspace_ready": False,
                "error": error_msg,
            }
        
        logger.info(f"[setup_workspace] Using Developer's workspace: {workspace_path}")
        
        # Get tech_stack from state (passed from tester.py) or agent
        tech_stack = state.get("tech_stack")
        if not tech_stack and agent:
            tech_stack = getattr(agent, 'tech_stack', 'nextjs')
        if not tech_stack:
            tech_stack = 'nextjs'  # Final fallback
        
        skill_registry = SkillRegistry.load(tech_stack)
        
        return {
            "workspace_path": workspace_path,
            "branch_name": branch_name,
            "workspace_ready": True,
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
