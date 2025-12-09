"""Setup workspace node - Setup git workspace/branch for test generation.

Exactly mirrored from developer_v2's setup_workspace.
"""
import logging
import os
import subprocess
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.skills import SkillRegistry
from app.agents.tester.src.tools.workspace_tools import (
    setup_git_worktree,
    get_agents_md,
    get_project_context,
)
from app.core.db import engine
from app.models import Project

logger = logging.getLogger(__name__)

# Import database container utilities (local copy to avoid developer_v2 import chain)
try:
    from app.agents.tester.src.utils.db_container import (
        start_postgres_container,
        update_env_file,
        get_database_url,
    )
    DB_CONTAINER_AVAILABLE = True
    logger.info("[setup_workspace] db_container module loaded successfully")
except ImportError as e:
    logger.warning(f"[setup_workspace] db_container import failed: {e}")
    DB_CONTAINER_AVAILABLE = False


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
    """Setup git workspace/branch for test generation.
    
    Exactly mirrored from developer_v2's setup_workspace.
    """
    logger.info("[NODE] setup_workspace")
    
    try:
        # Get IDs - support both story_id and task_id for compatibility
        story_id = state.get("story_id", state.get("task_id", "unknown"))
        project_id = state.get("project_id", "")
        
        if state.get("workspace_ready"):
            logger.info("[setup_workspace] Workspace already ready, skipping")
            return {}
        
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        branch_name = f"test_{short_id}"
        
        # Check if workspace_path already exists and is valid (reuse mode)
        existing_workspace = state.get("workspace_path", "")
        if existing_workspace and Path(existing_workspace).exists():
            logger.info(f"[setup_workspace] Reusing existing workspace: {existing_workspace}")
            workspace_info = {
                "workspace_path": existing_workspace,
                "branch_name": branch_name,
                "main_workspace": state.get("main_workspace", existing_workspace),
                "workspace_ready": True,
            }
        else:
            logger.info(f"[setup_workspace] Setting up workspace for branch '{branch_name}'")
            
            # Get main workspace - try multiple sources
            main_workspace = None
            
            # 1. From agent attributes (like developer_v2)
            if agent:
                if hasattr(agent, 'main_workspace'):
                    main_workspace = agent.main_workspace
                elif hasattr(agent, 'workspace_path'):
                    main_workspace = agent.workspace_path
            
            # 2. From database if not found
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
            
            # Setup git worktree (uses shared workspace_tools)
            workspace_info = setup_git_worktree(
                story_id=story_id,
                main_workspace=main_workspace,
                agent_name="Tester"
            )
        
        index_ready = False
        workspace_path = workspace_info.get("workspace_path", "")
        
        # Load project context
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
        
        # Load skill registry based on tech stack
        tech_stack = state.get("tech_stack") or _get_tech_stack(project_id)
        skill_registry = SkillRegistry.load(tech_stack)
        logger.info(f"[setup_workspace] Loaded SkillRegistry for '{tech_stack}' with {len(skill_registry.skills)} skills")
        
        # Start postgres container for database operations (like developer_v2)
        database_ready = False
        database_url = ""
        if workspace_path and DB_CONTAINER_AVAILABLE:
            try:
                db_info = start_postgres_container()
                if db_info:
                    update_env_file(workspace_path)
                    database_url = get_database_url()
                    database_ready = True
                    logger.info(f"[setup_workspace] Database ready at port {db_info.get('port')}")
            except Exception as db_err:
                logger.warning(f"[setup_workspace] Database setup failed: {db_err}")
        
        # Run pnpm install if package.json exists
        pkg_json = os.path.join(workspace_path, "package.json") if workspace_path else ""
        if pkg_json and os.path.exists(pkg_json):
            try:
                logger.info("[setup_workspace] Running pnpm install...")
                result = subprocess.run(
                    "pnpm install --frozen-lockfile",
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120,
                    shell=True,
                )
                if result.returncode == 0:
                    logger.info("[setup_workspace] pnpm install successful")
                else:
                    logger.warning(f"[setup_workspace] pnpm install failed: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                logger.warning("[setup_workspace] pnpm install timed out")
            except Exception as e:
                logger.warning(f"[setup_workspace] pnpm install error: {e}")
        
        # Run prisma generate if schema exists
        schema_path = os.path.join(workspace_path, "prisma", "schema.prisma") if workspace_path else ""
        if schema_path and os.path.exists(schema_path):
            try:
                logger.info("[setup_workspace] Running prisma generate...")
                result = subprocess.run(
                    "pnpm exec prisma generate",
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=60,
                    shell=True,
                )
                if result.returncode == 0:
                    logger.info("[setup_workspace] prisma generate successful")
                else:
                    logger.warning(f"[setup_workspace] prisma generate failed: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                logger.warning("[setup_workspace] prisma generate timed out")
            except Exception as e:
                logger.warning(f"[setup_workspace] prisma generate error: {e}")
            
            # Run prisma db push to create tables
            try:
                logger.info("[setup_workspace] Running prisma db push...")
                result = subprocess.run(
                    "pnpm exec prisma db push --skip-generate --accept-data-loss",
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120,
                    shell=True,
                )
                if result.returncode == 0:
                    logger.info("[setup_workspace] prisma db push successful")
                else:
                    logger.warning(f"[setup_workspace] prisma db push failed: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                logger.warning("[setup_workspace] prisma db push timed out")
            except Exception as e:
                logger.warning(f"[setup_workspace] prisma db push error: {e}")
        
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
        logger.error(f"[setup_workspace] Error: {e}", exc_info=True)
        return {
            "workspace_ready": False,
            "error": f"Workspace setup failed: {str(e)}",
        }
