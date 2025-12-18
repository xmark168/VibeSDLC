"""Setup workspace node - Setup git workspace/branch for code modification."""
import asyncio
import hashlib
import logging
import os
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from app.agents.developer.src.state import DeveloperState
from app.agents.developer.src.skills import SkillRegistry
from app.agents.developer.src.utils.db_container import (
    start_postgres_container,
    update_env_file,
    get_database_url,
)
from app.utils.workspace_utils import (
    setup_git_worktree,
    get_agents_md,
    get_project_context,
    _should_skip_pnpm_install,
    _update_pnpm_install_cache,
    _should_skip_prisma_generate,
    _update_prisma_generate_cache,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Git worktree management - now using shared utilities from app.utils.workspace_utils
# =============================================================================

# Thread pool for running blocking operations in parallel
_executor = ThreadPoolExecutor(max_workers=4)

# Note: Caching helper functions (_should_skip_pnpm_install, etc.) 
# are now imported from app.utils.workspace_utils


def _run_pnpm_install(workspace_path: str) -> bool:
    """Run pnpm install. Try --frozen-lockfile (60s), fallback to regular (120s)."""
    if _should_skip_pnpm_install(workspace_path):
        return True
    
    lockfile = Path(workspace_path) / "pnpm-lock.yaml"
    try:
        if lockfile.exists():
            result = subprocess.run("pnpm install --frozen-lockfile", cwd=workspace_path, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60, shell=True)
            if result.returncode == 0:
                _update_pnpm_install_cache(workspace_path)
                return True
            logger.warning(f"[setup_workspace] --frozen-lockfile failed: {result.stderr[:200] if result.stderr else ''}")
        
        result = subprocess.run("pnpm install", cwd=workspace_path, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120, shell=True)
        if result.returncode == 0:
            _update_pnpm_install_cache(workspace_path)
            return True
        logger.warning(f"[setup_workspace] pnpm install FAILED: {result.stderr[:200] if result.stderr else ''}")
        return False
    except subprocess.TimeoutExpired as e:
        logger.warning(f"[setup_workspace] pnpm install TIMEOUT after {e.timeout}s")
        return False
    except Exception as e:
        logger.warning(f"[setup_workspace] pnpm install ERROR: {e}")
        return False


def _run_prisma_generate(workspace_path: str) -> bool:
    """Run prisma generate (blocking). Returns True if successful."""
    schema_path = os.path.join(workspace_path, "prisma", "schema.prisma")
    if not os.path.exists(schema_path):
        return True  # No schema, nothing to generate
    
    if _should_skip_prisma_generate(workspace_path):
        return True
    
    try:
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
            _update_prisma_generate_cache(workspace_path)
            return True
        else:
            logger.warning(f"[setup_workspace] prisma generate failed")
            return False
    except subprocess.TimeoutExpired:
        logger.warning("[setup_workspace] prisma generate timed out")
        return False
    except Exception as e:
        logger.warning(f"[setup_workspace] prisma generate error: {e}")
        return False


def _run_prisma_db_push(workspace_path: str) -> bool:
    """Run prisma db push (blocking). Returns True if successful."""
    schema_path = os.path.join(workspace_path, "prisma", "schema.prisma")
    if not os.path.exists(schema_path):
        return True  # No schema, nothing to push
    
    try:
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
            logger.debug("[setup_workspace] prisma db push successful")
            return True
        else:
            logger.warning(f"[setup_workspace] prisma db push failed: {result.stderr[:200] if result.stderr else 'unknown'}")
            return False
    except subprocess.TimeoutExpired:
        logger.warning("[setup_workspace] prisma db push timed out")
        return False
    except Exception as e:
        logger.warning(f"[setup_workspace] prisma db push error: {e}")
        return False





async def _setup_prisma(workspace_path: str, database_ready: bool, story_logger) -> bool:
    """Setup Prisma: generate client, push schema, and seed database.
    
    Returns True if all steps succeeded, False otherwise.
    """
    schema_path = os.path.join(workspace_path, "prisma", "schema.prisma")
    if not os.path.exists(schema_path):
        return True
    
    loop = asyncio.get_event_loop()
    
    # Generate Prisma client
    await story_logger.info("🗄️ Generating Prisma client...")
    gen_success = await loop.run_in_executor(_executor, _run_prisma_generate, workspace_path)
    
    if not gen_success:
        await story_logger.warning("prisma generate failed")
        return False
    
    # Push schema to database
    if database_ready:
        await story_logger.info("🗄️ Syncing database schema (prisma db push)...")
        push_success = await loop.run_in_executor(_executor, _run_prisma_db_push, workspace_path)
        if not push_success:
            await story_logger.warning("prisma db push failed, tables may not be created")
            return False
        
        # Skip seeding in setup - will be done in build step
        # This avoids duplicate seed and early failures
    
    return True


def _start_database(workspace_path: str, story_id: str = None) -> dict:
    """Start postgres container (blocking). Returns db_info dict."""
    try:
        db_info = start_postgres_container(story_id)
        if db_info:
            update_env_file(workspace_path, story_id)
            database_url = get_database_url(story_id)
            
            # Update story DB info (container info only, workspace already updated)
            if story_id:
                from app.agents.developer.src.utils.db_container import update_story_db_info
                update_story_db_info(story_id, workspace_path, None)
            
            return {"ready": True, "url": database_url, "info": db_info}
    except Exception as db_err:
        logger.warning(f"[setup_workspace] Database setup failed: {db_err}")
    return {"ready": False, "url": "", "info": None}


def _build_project_config(tech_stack: str = "nextjs") -> dict:
    """Build default project config based on tech stack."""
    if tech_stack in ("nextjs", "nodejs-react", "react"):
        return {
            "tech_stack": {
                "name": tech_stack,
                "service": [
                    {
                        "name": "app",
                        "path": ".",
                        "format_cmd": "pnpm run format",
                        "lint_fix_cmd": "pnpm run lint:fix", 
                        "typecheck_cmd": "pnpm run typecheck",
                        "build_cmd": "pnpm run build",
                    }
                ]
            }
        }
    elif tech_stack in ("python", "fastapi", "django"):
        return {
            "tech_stack": {
                "name": tech_stack,
                "service": [
                    {
                        "name": "backend",
                        "path": ".",
                        "format_cmd": "ruff format .",
                        "lint_fix_cmd": "ruff check --fix .",
                        "typecheck_cmd": "mypy .",
                        "build_cmd": "",
                    }
                ]
            }
        }
    else:
        # Default fallback
        return {
            "tech_stack": {
                "name": tech_stack,
                "service": [
                    {
                        "name": "app",
                        "path": ".",
                        "format_cmd": "",
                        "lint_fix_cmd": "",
                        "typecheck_cmd": "",
                        "build_cmd": "",
                    }
                ]
            }
        }


async def setup_workspace(state: DeveloperState, agent=None) -> DeveloperState:
    """Setup git workspace/branch for code modification."""
    from langgraph.types import interrupt
    from app.agents.developer.src.utils.signal_utils import check_interrupt_signal
    from app.agents.developer.src.utils.story_logger import StoryLogger
    
    # Create story logger for detailed logging to frontend
    story_logger = StoryLogger.from_state(state, agent).with_node("setup_workspace")
    
    # Check for pause/cancel signal
    story_id = state.get("story_id", "")
    if story_id:
        signal = check_interrupt_signal(story_id, agent)
        if signal:
            await story_logger.info(f"Interrupt signal received: {signal}")
            interrupt({"reason": signal, "story_id": story_id, "node": "setup_workspace"})
    
    await story_logger.info("🔧 Starting workspace setup...")
    try:
        story_id = state.get("story_id", state.get("task_id", "unknown"))
        story_code = state.get("story_code", f"STORY-{story_id[:8]}")
        
        # Use story_code for branch name (sanitized)
        safe_code = story_code.replace('/', '-').replace('\\', '-')
        branch_name = f"story_{safe_code}"
        
        # Check if workspace_path already exists and is valid (reuse mode)
        existing_workspace = state.get("workspace_path", "")
        if existing_workspace and Path(existing_workspace).exists():
            await story_logger.info(f"Reusing existing workspace")
            workspace_info = {
                "workspace_path": existing_workspace,
                "branch_name": branch_name,
                "main_workspace": state.get("main_workspace", existing_workspace),
                "workspace_ready": True,
            }
        else:
            await story_logger.info(f"Creating git worktree for branch: {branch_name}")
            
            if hasattr(agent, 'main_workspace'):
                main_workspace = agent.main_workspace
            elif hasattr(agent, 'workspace_path'):
                main_workspace = agent.workspace_path
            else:
                await story_logger.error("Agent has no workspace path attribute")
                return {**state, "workspace_ready": False}
            
            workspace_info = setup_git_worktree(
                story_code=story_code,
                main_workspace=main_workspace,
                worktree_type="story",
                agent_name=agent.name if agent else "Developer"
            )
        
        workspace_path = workspace_info.get("workspace_path", "")
        branch_name = workspace_info.get("branch_name", "")
        
        # Update story in DB with workspace info and branch name
        if story_id and workspace_path:
            from app.agents.developer.src.utils.db_container import update_story_db_info
            update_success = update_story_db_info(story_id, workspace_path, branch_name)
            if update_success:
                await story_logger.debug(f"Updated story DB: worktree_path={workspace_path}, branch={branch_name}")
            else:
                await story_logger.warning(f"Failed to update story DB for story_id={story_id}")
        
        # Load context (fast, sync)
        project_context = ""
        agents_md = ""
        if workspace_path:
            try:
                agents_md = get_agents_md(workspace_path)
                project_context = get_project_context(workspace_path)
                await story_logger.debug("Loaded project context")
            except Exception as ctx_err:
                await story_logger.warning(f"Failed to load project context: {ctx_err}")
        
        # Load skill registry (fast, sync)
        tech_stack = state.get("tech_stack", "nextjs")
        skill_registry = SkillRegistry.load(tech_stack)
        
        # Run postgres + pnpm install in PARALLEL
        database_ready = False
        pnpm_success = True
        
        pkg_json = os.path.join(workspace_path, "package.json") if workspace_path else ""
        if workspace_path and pkg_json and os.path.exists(pkg_json):
            # Phase 1 Optimization: Run DB + pnpm + prisma generate in PARALLEL
            await story_logger.info("⚡ Starting parallel setup: DB + pnpm + Prisma...")
            loop = asyncio.get_event_loop()
            from functools import partial
            
            # Launch all 3 in parallel (prisma generate doesn't need DB)
            db_future = loop.run_in_executor(_executor, partial(_start_database, workspace_path, story_id))
            pnpm_future = loop.run_in_executor(_executor, _run_pnpm_install, workspace_path)
            prisma_gen_future = loop.run_in_executor(_executor, _run_prisma_generate, workspace_path)
            
            # Wait for all 3 to complete
            db_result, pnpm_success, gen_success = await asyncio.gather(
                db_future, pnpm_future, prisma_gen_future
            )
            
            database_ready = db_result.get("ready", False)
            
            if not pnpm_success:
                await story_logger.warning("pnpm install failed, continuing...")
            if not gen_success:
                await story_logger.warning("prisma generate failed")
            
            # Only db push needs database ready (sequential after parallel)
            if database_ready and gen_success:
                await story_logger.info("🗄️ Syncing database schema...")
                push_success = await loop.run_in_executor(_executor, _run_prisma_db_push, workspace_path)
                if not push_success:
                    await story_logger.warning("prisma db push failed")
        
        # Build project config with tech stack
        project_config = _build_project_config(tech_stack)
        
        # Notify user workspace is ready (milestone message - saved to DB)
        if workspace_info.get("workspace_ready"):
            db_status = "DB ready" if database_ready else "No DB"
            await story_logger.info(f"Workspace ready | Branch: {workspace_info.get('branch_name')} | {db_status}")
            
            # Set PROCESSING state now that workspace is ready
            # This was moved from _handle_story_processing to here for accurate state tracking
            if story_id and agent and hasattr(agent, '_update_story_state'):
                from app.models.base import StoryAgentState
                await agent._update_story_state(story_id, StoryAgentState.PROCESSING)
            
            await story_logger.message("Workspace sẵn sàng, bắt đầu phân tích...")
        
        return {
            **state,
            "workspace_path": workspace_info["workspace_path"],
            "branch_name": workspace_info["branch_name"],
            "main_workspace": workspace_info["main_workspace"],
            "workspace_ready": workspace_info["workspace_ready"],
            "agents_md": agents_md,
            "project_context": project_context,
            "tech_stack": tech_stack,
            # skill_registry not stored in state - contains non-serializable Path objects
            # It's re-loaded on demand in nodes that need it
            "available_skills": skill_registry.get_skill_ids(),
            "project_config": project_config,
        }
        
    except Exception as e:
        # Re-raise GraphInterrupt - it's expected for pause/cancel
        from langgraph.errors import GraphInterrupt
        if isinstance(e, GraphInterrupt):
            raise
        await story_logger.error(f"Workspace setup failed: {str(e)}", exc=e)
        return {
            **state,
            "workspace_ready": False,
            "error": f"Workspace setup failed: {str(e)}",
        }
