"""Setup workspace node - Setup git workspace/branch for code modification."""
import asyncio
import hashlib
import logging
import os
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools import (
    setup_git_worktree,
    get_agents_md,
    get_project_context,
)
from app.agents.developer_v2.src.skills import SkillRegistry
from app.agents.developer_v2.src.utils.db_container import (
    start_postgres_container,
    update_env_file,
    get_database_url,
)

logger = logging.getLogger(__name__)

# Thread pool for running blocking operations in parallel
_executor = ThreadPoolExecutor(max_workers=4)


def _should_skip_pnpm_install(workspace_path: str) -> bool:
    """Check if pnpm install can be skipped (lockfile unchanged)."""
    lockfile = Path(workspace_path) / "pnpm-lock.yaml"
    node_modules = Path(workspace_path) / "node_modules"
    cache_file = Path(workspace_path) / ".pnpm_install_cache"
    
    if not node_modules.exists() or not lockfile.exists():
        return False
    
    try:
        current_hash = hashlib.md5(lockfile.read_bytes()).hexdigest()
        if cache_file.exists():
            cached_hash = cache_file.read_text().strip()
            if cached_hash == current_hash:
                return True
    except Exception:
        pass
    
    return False


def _update_pnpm_install_cache(workspace_path: str) -> None:
    """Update pnpm install cache after successful install."""
    lockfile = Path(workspace_path) / "pnpm-lock.yaml"
    cache_file = Path(workspace_path) / ".pnpm_install_cache"
    
    try:
        if lockfile.exists():
            current_hash = hashlib.md5(lockfile.read_bytes()).hexdigest()
            cache_file.write_text(current_hash)
    except Exception:
        pass


def _should_skip_prisma_generate(workspace_path: str) -> bool:
    """Check if prisma generate can be skipped (schema unchanged)."""
    schema_path = Path(workspace_path) / "prisma" / "schema.prisma"
    cache_file = Path(workspace_path) / ".prisma_generate_cache"
    generated_dir = Path(workspace_path) / "node_modules" / ".prisma"
    
    if not schema_path.exists() or not generated_dir.exists():
        return False
    
    try:
        current_hash = hashlib.md5(schema_path.read_bytes()).hexdigest()
        if cache_file.exists():
            cached_hash = cache_file.read_text().strip()
            if cached_hash == current_hash:
                return True
    except Exception:
        pass
    
    return False


def _update_prisma_generate_cache(workspace_path: str) -> None:
    """Update prisma generate cache after successful generate."""
    schema_path = Path(workspace_path) / "prisma" / "schema.prisma"
    cache_file = Path(workspace_path) / ".prisma_generate_cache"
    
    try:
        if schema_path.exists():
            current_hash = hashlib.md5(schema_path.read_bytes()).hexdigest()
            cache_file.write_text(current_hash)
    except Exception:
        pass


def _run_pnpm_install(workspace_path: str) -> bool:
    """Run pnpm install (blocking). Returns True if successful."""
    if _should_skip_pnpm_install(workspace_path):
        logger.info("[setup_workspace] Skipping pnpm install (cached)")
        return True
    
    try:
        logger.info("[setup_workspace] Running pnpm install --frozen-lockfile --prefer-offline...")
        result = subprocess.run(
            "pnpm install --frozen-lockfile --prefer-offline",
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
            _update_pnpm_install_cache(workspace_path)
            return True
        else:
            # Retry without --prefer-offline if it fails
            logger.info("[setup_workspace] Retrying pnpm install without --prefer-offline...")
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
                logger.info("[setup_workspace] pnpm install successful (retry)")
                _update_pnpm_install_cache(workspace_path)
                return True
            logger.warning(f"[setup_workspace] pnpm install failed: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        logger.warning("[setup_workspace] pnpm install timed out")
        return False
    except Exception as e:
        logger.warning(f"[setup_workspace] pnpm install error: {e}")
        return False


def _run_prisma_generate(workspace_path: str) -> bool:
    """Run prisma generate (blocking). Returns True if successful."""
    schema_path = os.path.join(workspace_path, "prisma", "schema.prisma")
    if not os.path.exists(schema_path):
        return True  # No schema, nothing to generate
    
    if _should_skip_prisma_generate(workspace_path):
        logger.info("[setup_workspace] Skipping prisma generate (cached)")
        return True
    
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
            _update_prisma_generate_cache(workspace_path)
            return True
        else:
            logger.warning(f"[setup_workspace] prisma generate failed: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        logger.warning("[setup_workspace] prisma generate timed out")
        return False
    except Exception as e:
        logger.warning(f"[setup_workspace] prisma generate error: {e}")
        return False


def _start_database(workspace_path: str) -> dict:
    """Start postgres container (blocking). Returns db_info dict."""
    try:
        db_info = start_postgres_container()
        if db_info:
            update_env_file(workspace_path)
            database_url = get_database_url()
            logger.info(f"[setup_workspace] Database ready at port {db_info.get('port')}")
            return {"ready": True, "url": database_url, "info": db_info}
    except Exception as db_err:
        logger.warning(f"[setup_workspace] Database setup failed: {db_err}")
    return {"ready": False, "url": "", "info": None}


async def setup_workspace(state: DeveloperState, agent=None) -> DeveloperState:
    """Setup git workspace/branch for code modification."""
    logger.info("[NODE] setup_workspace")
    try:
        story_id = state.get("story_id", state.get("task_id", "unknown"))
        
        if state.get("workspace_ready"):
            logger.info("[setup_workspace] Workspace ready, checking dependencies...")
        
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        branch_name = f"story_{short_id}"
        
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
        
        # Load context (fast, sync)
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
        
        # Load skill registry (fast, sync)
        tech_stack = state.get("tech_stack", "nextjs")
        skill_registry = SkillRegistry.load(tech_stack)
        logger.info(f"[setup_workspace] Loaded SkillRegistry for '{tech_stack}' with {len(skill_registry.skills)} skills")
        
        # Run postgres + pnpm install in PARALLEL
        database_ready = False
        database_url = ""
        pnpm_success = True
        
        pkg_json = os.path.join(workspace_path, "package.json") if workspace_path else ""
        if workspace_path and pkg_json and os.path.exists(pkg_json):
            loop = asyncio.get_event_loop()
            
            # Run both in parallel using thread pool
            logger.info("[setup_workspace] Starting parallel setup (postgres + pnpm)...")
            db_future = loop.run_in_executor(_executor, _start_database, workspace_path)
            pnpm_future = loop.run_in_executor(_executor, _run_pnpm_install, workspace_path)
            
            # Wait for both
            db_result, pnpm_success = await asyncio.gather(db_future, pnpm_future)
            
            database_ready = db_result.get("ready", False)
            database_url = db_result.get("url", "")
            
            # Run prisma generate AFTER pnpm install completes
            if pnpm_success:
                await loop.run_in_executor(_executor, _run_prisma_generate, workspace_path)
        
        return {
            **state,
            "workspace_path": workspace_info["workspace_path"],
            "branch_name": workspace_info["branch_name"],
            "main_workspace": workspace_info["main_workspace"],
            "workspace_ready": workspace_info["workspace_ready"],
            "index_ready": index_ready,
            "agents_md": agents_md,
            "project_context": project_context,
            "tech_stack": tech_stack,
            "skill_registry": skill_registry,
            "available_skills": skill_registry.get_skill_ids(),
        }
        
    except Exception as e:
        logger.error(f"[setup_workspace] Error: {e}", exc_info=True)
        return {
            **state,
            "workspace_ready": False,
            "error": f"Workspace setup failed: {str(e)}",
        }
