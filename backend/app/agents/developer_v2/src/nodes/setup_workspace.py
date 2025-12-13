"""Setup workspace node - Setup git workspace/branch for code modification."""
import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from app.agents.developer_v2.src.state import DeveloperState

from app.agents.developer_v2.src.skills import SkillRegistry
from app.agents.developer_v2.src.utils.db_container import (
    start_postgres_container,
    update_env_file,
    get_database_url,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Git worktree management
# =============================================================================

def _kill_processes_in_directory(directory: Path, agent_name: str = "Developer") -> None:
    """Kill node processes that might be locking files (Windows only)."""
    import platform
    if platform.system() != "Windows":
        return
    try:
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True, timeout=10)
    except Exception:
        pass


def cleanup_old_worktree(main_workspace: Path, branch_name: str, worktree_path: Path, agent_name: str = "Developer"):
    """Clean up worktree and branch. Order: prune → kill → remove → delete dir → prune → delete branch."""
    import platform, tempfile, time
    
    # Prune first
    try:
        subprocess.run(["git", "worktree", "prune"], cwd=str(main_workspace), capture_output=True, timeout=10)
    except Exception:
        pass
    
    if worktree_path.exists():
        _kill_processes_in_directory(worktree_path, agent_name)
        
        try:
            subprocess.run(["git", "worktree", "remove", str(worktree_path), "--force"], cwd=str(main_workspace), capture_output=True, timeout=30)
        except Exception:
            pass
        
        if worktree_path.exists():
            for attempt in range(3):
                try:
                    shutil.rmtree(worktree_path)
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(0.5 * (attempt + 1))
                        _kill_processes_in_directory(worktree_path, agent_name)
                    elif platform.system() == "Windows":
                        try:
                            empty_dir = tempfile.mkdtemp()
                            subprocess.run(["robocopy", empty_dir, str(worktree_path), "/mir", "/r:0", "/w:0", "/njh", "/njs", "/nc", "/ns", "/np", "/nfl", "/ndl"], capture_output=True, timeout=30)
                            shutil.rmtree(empty_dir, ignore_errors=True)
                            shutil.rmtree(worktree_path, ignore_errors=True)
                        except Exception:
                            logger.error(f"[{agent_name}] Failed to remove directory: {e}")
    
    # Prune again + delete branch
    try:
        subprocess.run(["git", "worktree", "prune"], cwd=str(main_workspace), capture_output=True, timeout=10)
    except Exception:
        pass
    try:
        subprocess.run(["git", "branch", "-D", branch_name], cwd=str(main_workspace), capture_output=True, timeout=10)
    except Exception:
        pass


def setup_git_worktree(
    story_code: str,
    main_workspace: Path | str,
    agent_name: str = "Developer"
) -> dict:
    """Setup git worktree for story development.
    
    Worktree path: {main_workspace}/.worktrees/{story_code}
    Example: /path/to/project/.worktrees/US-001
    
    Args:
        story_code: Unique story code (e.g., "US-001", "EPIC-001-US-001")
        main_workspace: Path to main project workspace
        agent_name: Agent name for logging
    """
    main_workspace = Path(main_workspace).resolve()
    # Sanitize story_code for filesystem (replace invalid chars)
    safe_code = story_code.replace('/', '-').replace('\\', '-')
    branch_name = f"story_{safe_code}"
    
    # Worktree path: main_workspace/.worktrees/story_code
    worktrees_dir = main_workspace / ".worktrees"
    worktrees_dir.mkdir(exist_ok=True)
    worktree_path = (worktrees_dir / safe_code).resolve()
    
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
    
    # Clean up old worktree
    cleanup_old_worktree(main_workspace, branch_name, worktree_path, agent_name)
    
    # Auto-commit uncommitted files so worktree has them
    try:
        # Check for uncommitted changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(main_workspace),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if status.returncode == 0 and status.stdout.strip():
            # Add all files and commit
            subprocess.run(["git", "add", "-A"], cwd=str(main_workspace), capture_output=True, timeout=30)
            subprocess.run(
                ["git", "commit", "-m", "Auto-commit before worktree creation"],
                cwd=str(main_workspace),
                capture_output=True,
                timeout=30,
            )
            logger.debug(f"[{agent_name}] Auto-committed uncommitted files")
    except Exception as e:
        logger.warning(f"[{agent_name}] Auto-commit failed: {e}")
    
    logger.debug(f"[{agent_name}] Creating worktree '{branch_name}' at: {worktree_path}")
    
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
    
    # Create worktree
    worktree_result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch_name],
        cwd=str(main_workspace),
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    logger.debug(f"[{agent_name}] Worktree created: {worktree_path}")
    
    workspace_ready = worktree_path.exists() and worktree_path.is_dir()
    
    if not workspace_ready:
        logger.warning(f"[{agent_name}] Worktree not created, using main workspace")
        worktree_path = main_workspace
    
    return {
        "workspace_path": str(worktree_path),
        "branch_name": branch_name,
        "main_workspace": str(main_workspace),
        "workspace_ready": workspace_ready,
    }

def get_agents_md(workspace_path: str | Path) -> str:
    """Read AGENTS.md from workspace root."""
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
    """Read project context files (README.md, package.json summary)."""
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


def _run_prisma_seed(workspace_path: str) -> bool:
    """Run prisma db seed (60s timeout)."""
    seed_file = os.path.join(workspace_path, "prisma", "seed.ts")
    if not os.path.exists(seed_file):
        return True
    try:
        result = subprocess.run("pnpm exec ts-node --compiler-options {\"module\":\"CommonJS\"} prisma/seed.ts", cwd=workspace_path, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60, shell=True)
        if result.returncode == 0:
            return True
        logger.warning(f"[setup_workspace] seed FAILED: {result.stderr[:200] if result.stderr else ''}")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("[setup_workspace] seed TIMEOUT")
        return False
    except Exception as e:
        logger.warning(f"[setup_workspace] seed ERROR: {e}")
        return False


def _start_database(workspace_path: str, story_id: str = None) -> dict:
    """Start postgres container (blocking). Returns db_info dict."""
    try:
        db_info = start_postgres_container(story_id)
        if db_info:
            update_env_file(workspace_path, story_id)
            database_url = get_database_url(story_id)
            
            # Update story DB info (container info only, workspace already updated)
            if story_id:
                from app.agents.developer_v2.src.utils.db_container import update_story_db_info
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
    from app.agents.developer_v2.developer_v2 import check_interrupt_signal
    from app.agents.developer_v2.src.utils.story_logger import StoryLogger
    
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
        
        if state.get("workspace_ready"):
            await story_logger.debug("Workspace ready, checking dependencies...")
        
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
                return {**state, "workspace_ready": False, "index_ready": False}
            
            workspace_info = setup_git_worktree(
                story_code=story_code,
                main_workspace=main_workspace,
                agent_name=agent.name
            )
        
        index_ready = False
        workspace_path = workspace_info.get("workspace_path", "")
        branch_name = workspace_info.get("branch_name", "")
        
        # Update story in DB with workspace info and branch name
        if story_id and workspace_path:
            from app.agents.developer_v2.src.utils.db_container import update_story_db_info
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
            await story_logger.info("📦 Installing dependencies (pnpm install)...")
            loop = asyncio.get_event_loop()
            from functools import partial
            db_future = loop.run_in_executor(_executor, partial(_start_database, workspace_path, story_id))
            pnpm_future = loop.run_in_executor(_executor, _run_pnpm_install, workspace_path)
            
            # Wait for both
            db_result, pnpm_success = await asyncio.gather(db_future, pnpm_future)
            
            database_ready = db_result.get("ready", False)
            db_result.get("url", "")
            
            if not pnpm_success:
                await story_logger.warning("pnpm install failed, continuing...")
            
            # Run prisma generate and db push AFTER pnpm install completes
            schema_path = os.path.join(workspace_path, "prisma", "schema.prisma")
            if pnpm_success and os.path.exists(schema_path):
                await story_logger.info("🗄️ Generating Prisma client...")
                gen_success = await loop.run_in_executor(_executor, _run_prisma_generate, workspace_path)
                
                if gen_success:
                    # Run db push to create/update tables
                    if database_ready:
                        await story_logger.info("🗄️ Syncing database schema (prisma db push)...")
                        push_success = await loop.run_in_executor(_executor, _run_prisma_db_push, workspace_path)
                        if not push_success:
                            await story_logger.warning("prisma db push failed, tables may not be created")
                        else:
                            # Run seed after db push succeeds
                            seed_file = os.path.join(workspace_path, "prisma", "seed.ts")
                            if os.path.exists(seed_file):
                                await story_logger.info("🌱 Seeding database...")
                                seed_success = await loop.run_in_executor(_executor, _run_prisma_seed, workspace_path)
                                if not seed_success:
                                    await story_logger.warning("prisma db seed failed, will retry in build step")
                else:
                    await story_logger.warning("prisma generate failed")
        
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
            
            await story_logger.message("✅ Workspace sẵn sàng, bắt đầu phân tích...")
        
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
