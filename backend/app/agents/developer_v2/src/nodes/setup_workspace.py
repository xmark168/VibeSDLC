"""Setup workspace node - Setup git workspace/branch for code modification."""
import hashlib
import logging
import os
import subprocess
import sys
from pathlib import Path


def _use_shell() -> bool:
    """Use shell=True on Windows to find commands in PATH."""
    return sys.platform == 'win32'

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools import (
    setup_git_worktree,
    index_workspace,
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


def _get_package_hash(workspace_path: str) -> str:
    """Get hash of package.json content."""
    pkg_path = os.path.join(workspace_path, "package.json")
    if not os.path.exists(pkg_path):
        return ""
    with open(pkg_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def _should_run_bun_install(workspace_path: str) -> bool:
    """Check if bun install should run based on package.json hash."""
    hash_file = os.path.join(workspace_path, ".bun-install-hash")
    current_hash = _get_package_hash(workspace_path)
    
    if not current_hash:
        return False  # No package.json
    
    # Check cached hash
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            cached_hash = f.read().strip()
        if cached_hash == current_hash:
            return False  # Same hash, skip install
    
    return True


def _save_package_hash(workspace_path: str):
    """Save current package.json hash."""
    hash_file = os.path.join(workspace_path, ".bun-install-hash")
    current_hash = _get_package_hash(workspace_path)
    if current_hash:
        with open(hash_file, 'w') as f:
            f.write(current_hash)


def _get_schema_hash(workspace_path: str) -> str:
    """Get hash of prisma schema content."""
    schema_path = os.path.join(workspace_path, "prisma", "schema.prisma")
    if not os.path.exists(schema_path):
        return ""
    with open(schema_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def _should_run_prisma_generate(workspace_path: str) -> bool:
    """Check if prisma generate should run based on schema hash."""
    hash_file = os.path.join(workspace_path, ".prisma-schema-hash")
    current_hash = _get_schema_hash(workspace_path)
    
    if not current_hash:
        return False  # No schema
    
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            if f.read().strip() == current_hash:
                return False  # Same hash, skip
    return True


def _save_schema_hash(workspace_path: str):
    """Save current schema hash."""
    hash_file = os.path.join(workspace_path, ".prisma-schema-hash")
    current_hash = _get_schema_hash(workspace_path)
    if current_hash:
        with open(hash_file, 'w') as f:
            f.write(current_hash)


def _get_shared_bun_cache() -> str:
    """Get shared bun cache directory path."""
    # backend/projects/.bun-cache
    current_file = Path(__file__).resolve()
    backend_root = current_file.parent.parent.parent.parent.parent.parent
    cache_dir = backend_root / "projects" / ".bun-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return str(cache_dir)


def _get_bun_env() -> dict:
    """Get environment with shared bun cache."""
    env = os.environ.copy()
    env["BUN_INSTALL_CACHE_DIR"] = _get_shared_bun_cache()
    return env


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
        
        # Load skill registry based on tech stack
        tech_stack = state.get("tech_stack", "nextjs")  # Default to nextjs
        skill_registry = SkillRegistry.load(tech_stack)
        logger.info(f"[setup_workspace] Loaded SkillRegistry for '{tech_stack}' with {len(skill_registry.skills)} skills")
        
        # Start postgres container for database operations
        # Note: testcontainers auto-assigns random available port for each container
        database_ready = False
        database_url = ""
        if workspace_path:
            try:
                db_info = start_postgres_container()
                if db_info:
                    update_env_file(workspace_path)
                    database_url = get_database_url()
                    database_ready = True
                    logger.info(f"[setup_workspace] Database ready at port {db_info.get('port')}")
            except Exception as db_err:
                logger.warning(f"[setup_workspace] Database setup failed: {db_err}")
        
        # Smart bun install - only if package.json changed
        if workspace_path and _should_run_bun_install(workspace_path):
            try:
                cache_dir = _get_shared_bun_cache()
                logger.info(f"[setup_workspace] Running bun install (cache: {cache_dir})...")
                result = subprocess.run(
                    "bun install --frozen-lockfile",
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    shell=_use_shell(),
                    env=_get_bun_env()
                )
                if result.returncode == 0:
                    _save_package_hash(workspace_path)
                    logger.info("[setup_workspace] bun install successful")
                else:
                    logger.warning(f"[setup_workspace] bun install failed: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                logger.warning("[setup_workspace] bun install timed out")
            except Exception as e:
                logger.warning(f"[setup_workspace] bun install error: {e}")
        else:
            if workspace_path:
                logger.info("[setup_workspace] Skipping bun install (package.json unchanged)")
        
        # Smart prisma generate - only if schema changed
        if workspace_path and _should_run_prisma_generate(workspace_path):
            try:
                logger.info("[setup_workspace] Running prisma generate...")
                result = subprocess.run(
                    "bunx prisma generate",
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    shell=_use_shell()
                )
                if result.returncode == 0:
                    _save_schema_hash(workspace_path)
                    logger.info("[setup_workspace] prisma generate successful")
                else:
                    logger.warning(f"[setup_workspace] prisma generate failed: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                logger.warning("[setup_workspace] prisma generate timed out")
            except Exception as e:
                logger.warning(f"[setup_workspace] prisma generate error: {e}")
        else:
            if workspace_path and _get_schema_hash(workspace_path):
                logger.info("[setup_workspace] Skipping prisma generate (schema unchanged)")
        
        return {
            **state,
            "workspace_path": workspace_info["workspace_path"],
            "branch_name": workspace_info["branch_name"],
            "main_workspace": workspace_info["main_workspace"],
            "workspace_ready": workspace_info["workspace_ready"],
            "index_ready": index_ready,
            "agents_md": agents_md,
            "project_context": project_context,
            # Skill registry
            "tech_stack": tech_stack,
            "skill_registry": skill_registry,
            "available_skills": skill_registry.get_skill_ids(),
            # Database
            "database_ready": database_ready,
            "database_url": database_url,
        }
        
    except Exception as e:
        logger.error(f"[setup_workspace] Error: {e}", exc_info=True)
        return {
            **state,
            "workspace_ready": False,
            "error": f"Workspace setup failed: {str(e)}",
        }
