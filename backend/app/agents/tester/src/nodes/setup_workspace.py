"""Setup workspace node - Setup git workspace/branch for test generation.

Mirrored from developer_v2's setup_workspace for consistency.
"""

import hashlib
import logging
import os
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.agents.tester.src.skills import SkillRegistry
from app.agents.tester.src.state import TesterState
from app.core.db import engine
from app.models import Project

logger = logging.getLogger(__name__)


# =============================================================================
# Database helpers
# =============================================================================

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


# =============================================================================
# Context helpers
# =============================================================================

def _get_agents_md(workspace_path: str) -> str:
    """Read AGENTS.md from workspace if exists."""
    agents_path = Path(workspace_path) / "AGENTS.md"
    if agents_path.exists():
        try:
            return agents_path.read_text(encoding="utf-8")[:8000]
        except Exception as e:
            logger.warning(f"[_get_agents_md] Error: {e}")
    return ""


def _get_project_context(workspace_path: str) -> str:
    """Build project context from workspace."""
    context_parts = []
    workspace = Path(workspace_path)

    config_files = [
        "package.json",
        "tsconfig.json",
        "jest.config.js",
        "jest.config.ts",
        "vitest.config.ts",
        "playwright.config.ts",
    ]

    for config_file in config_files:
        config_path = workspace / config_file
        if config_path.exists():
            try:
                content = config_path.read_text(encoding="utf-8")[:2000]
                context_parts.append(f"### {config_file}\n```\n{content}\n```")
            except Exception:
                pass

    return "\n\n".join(context_parts)


# =============================================================================
# Git worktree management (mirrored from developer_v2)
# =============================================================================

def _is_valid_git_repo(workspace_path: str) -> bool:
    """Check if workspace is a valid git repository."""
    try:
        result = subprocess.run(
            ["git", "status"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _cleanup_old_worktree(main_workspace: Path, branch_name: str) -> None:
    """Clean up existing worktree directory and branch.
    
    Mirrored from developer_v2's cleanup_old_worktree().
    """
    short_id = branch_name.replace("test_", "")
    worktree_path = main_workspace.parent / f"ws_test_{short_id}"
    
    # Remove worktree via git command
    if worktree_path.exists():
        logger.info(f"[Tester] Removing old worktree: {worktree_path}")
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=str(main_workspace),
                capture_output=True,
                timeout=30,
            )
        except Exception as e:
            logger.warning(f"[Tester] Git worktree remove failed: {e}")
        
        # Force remove directory if still exists
        if worktree_path.exists():
            try:
                shutil.rmtree(worktree_path)
                logger.info(f"[Tester] Removed directory: {worktree_path}")
            except Exception as e:
                logger.error(f"[Tester] Failed to remove directory: {e}")
    
    # Delete branch if exists
    try:
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=str(main_workspace),
            capture_output=True,
            timeout=10,
        )
        logger.debug(f"[Tester] Deleted branch: {branch_name}")
    except Exception as e:
        logger.debug(f"[Tester] Branch delete (may not exist): {e}")


def _setup_git_worktree(
    task_id: str, main_workspace: str, agent_name: str = "tester"
) -> dict:
    """Setup git worktree for isolated test development.
    
    Mirrored from developer_v2's setup_git_worktree().
    
    Returns:
        dict with workspace_path, branch_name, main_workspace, workspace_ready
    """
    main_path = Path(main_workspace)
    short_id = task_id.split("-")[-1][:8] if "-" in task_id else task_id[:8]
    branch_name = f"test_{short_id}"
    
    # Validate main workspace exists
    if not main_path.exists():
        logger.error(f"[{agent_name}] Workspace does not exist: {main_workspace}")
        return {
            "workspace_path": main_workspace,
            "branch_name": branch_name,
            "main_workspace": main_workspace,
            "workspace_ready": False,
        }
    
    # Check if main workspace is a valid git repo
    if not _is_valid_git_repo(main_workspace):
        logger.error(f"[{agent_name}] Not a git repo: {main_workspace}")
        return {
            "workspace_path": main_workspace,
            "branch_name": branch_name,
            "main_workspace": main_workspace,
            "workspace_ready": False,
        }
    
    # Clean up old worktree if exists (like developer_v2)
    _cleanup_old_worktree(main_path, branch_name)
    
    # Create new worktree path: parent/ws_test_{short_id}
    worktree_path = main_path.parent / f"ws_test_{short_id}"
    
    logger.info(f"[{agent_name}] Creating worktree for '{branch_name}' at {worktree_path}")
    
    try:
        # Get current branch to create new branch from
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=main_workspace,
            capture_output=True,
            text=True,
            timeout=10,
        )
        current_branch = result.stdout.strip() if result.returncode == 0 else "main"
        
        # Create branch from current branch
        subprocess.run(
            ["git", "branch", branch_name, current_branch],
            cwd=main_workspace,
            capture_output=True,
            timeout=30,
        )
        
        # Create worktree
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch_name],
            cwd=main_workspace,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode == 0:
            logger.info(f"[{agent_name}] Created worktree: {worktree_path}")
            return {
                "workspace_path": str(worktree_path),
                "branch_name": branch_name,
                "main_workspace": main_workspace,
                "workspace_ready": True,
            }
        else:
            logger.warning(f"[{agent_name}] Worktree creation failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.warning(f"[{agent_name}] Git command timed out")
    except Exception as e:
        logger.warning(f"[{agent_name}] Git error: {e}")
    
    # Fallback: use main workspace directly
    logger.warning(f"[{agent_name}] Worktree not created, using main workspace")
    return {
        "workspace_path": main_workspace,
        "branch_name": "",
        "main_workspace": main_workspace,
        "workspace_ready": True,
    }


# =============================================================================
# Package management
# =============================================================================

def _get_bun_path() -> str | None:
    """Find bun executable path."""
    # Check bun in PATH
    bun_in_path = shutil.which("bun")
    if bun_in_path:
        return bun_in_path
    
    # Try common Windows paths
    common_paths = [
        os.path.expandvars(r"%USERPROFILE%\.bun\bin\bun.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\bun\bin\bun.exe"),
    ]
    for path in common_paths:
        if os.path.exists(path):
            logger.info(f"[_get_bun_path] Found bun at: {path}")
            return path
    
    return None


def _get_package_hash(workspace_path: str) -> str:
    """Get hash of package.json content."""
    pkg_path = os.path.join(workspace_path, "package.json")
    if not os.path.exists(pkg_path):
        return ""
    with open(pkg_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _get_prisma_schema_hash(workspace_path: str) -> str:
    """Get hash of prisma schema."""
    schema_path = os.path.join(workspace_path, "prisma", "schema.prisma")
    if not os.path.exists(schema_path):
        return ""
    with open(schema_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _should_run_install(workspace_path: str) -> bool:
    """Check if bun install should run based on package.json hash."""
    hash_file = os.path.join(workspace_path, ".bun-install-hash")
    current_hash = _get_package_hash(workspace_path)

    if not current_hash:
        return False

    if os.path.exists(hash_file):
        with open(hash_file) as f:
            if f.read().strip() == current_hash:
                return False

    return True


def _save_install_hash(workspace_path: str):
    """Save current package.json hash."""
    hash_file = os.path.join(workspace_path, ".bun-install-hash")
    current_hash = _get_package_hash(workspace_path)
    if current_hash:
        with open(hash_file, "w") as f:
            f.write(current_hash)


def _should_run_prisma_generate(workspace_path: str) -> bool:
    """Check if prisma generate should run based on schema hash."""
    hash_file = os.path.join(workspace_path, ".prisma-schema-hash")
    current_hash = _get_prisma_schema_hash(workspace_path)

    if not current_hash:
        return False

    if os.path.exists(hash_file):
        with open(hash_file) as f:
            if f.read().strip() == current_hash:
                return False

    return True


def _save_prisma_hash(workspace_path: str):
    """Save current prisma schema hash."""
    hash_file = os.path.join(workspace_path, ".prisma-schema-hash")
    current_hash = _get_prisma_schema_hash(workspace_path)
    if current_hash:
        with open(hash_file, "w") as f:
            f.write(current_hash)


def _run_bun_install(workspace_path: str, bun_path: str) -> bool:
    """Run bun install --frozen-lockfile."""
    try:
        logger.info("[setup_workspace] Running bun install --frozen-lockfile...")
        result = subprocess.run(
            [bun_path, "install", "--frozen-lockfile"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        if result.returncode == 0:
            _save_install_hash(workspace_path)
            logger.info("[setup_workspace] bun install successful")
            return True
        else:
            # Try without --frozen-lockfile if it fails
            logger.warning(f"[setup_workspace] bun install --frozen-lockfile failed, trying without flag")
            result = subprocess.run(
                [bun_path, "install"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
            if result.returncode == 0:
                _save_install_hash(workspace_path)
                logger.info("[setup_workspace] bun install successful")
                return True
            logger.warning(f"[setup_workspace] bun install failed: {result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        logger.warning("[setup_workspace] bun install timed out")
    except Exception as e:
        logger.warning(f"[setup_workspace] bun install error: {e}")
    return False


def _run_prisma_generate(workspace_path: str, bun_path: str) -> bool:
    """Run bunx prisma generate."""
    schema_path = os.path.join(workspace_path, "prisma", "schema.prisma")
    if not os.path.exists(schema_path):
        return True  # No schema, nothing to do
    
    if not _should_run_prisma_generate(workspace_path):
        logger.info("[setup_workspace] Skipping prisma generate (schema unchanged)")
        return True
    
    try:
        logger.info("[setup_workspace] Running bunx prisma generate...")
        # Use bunx for running prisma
        bunx_path = bun_path.replace("bun.exe", "bunx.exe") if bun_path.endswith(".exe") else bun_path + "x"
        if not os.path.exists(bunx_path):
            bunx_path = bun_path  # Fallback to bun x
            cmd = [bunx_path, "x", "prisma", "generate"]
        else:
            cmd = [bunx_path, "prisma", "generate"]
        
        result = subprocess.run(
            cmd,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            shell=True,  # Use shell for bunx
        )
        
        # Alternative: use bun run if bunx fails
        if result.returncode != 0:
            result = subprocess.run(
                "bunx prisma generate",
                cwd=workspace_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                shell=True,
            )
        
        if result.returncode == 0:
            _save_prisma_hash(workspace_path)
            logger.info("[setup_workspace] prisma generate successful")
            return True
        else:
            logger.warning(f"[setup_workspace] prisma generate failed: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        logger.warning("[setup_workspace] prisma generate timed out")
    except Exception as e:
        logger.warning(f"[setup_workspace] prisma generate error: {e}")
    return False


# =============================================================================
# Main setup function
# =============================================================================

async def setup_workspace(state: TesterState, agent=None) -> dict:
    """Setup workspace for test generation.

    This node (mirrored from developer_v2):
    1. Gets project path from database
    2. Creates git worktree for isolated test development (with cleanup)
    3. Loads project context and AGENTS.md
    4. Initializes skill registry
    5. Runs bun install --frozen-lockfile
    6. Runs bunx prisma generate

    Returns:
        Updated state with workspace context
    """
    print("[NODE] setup_workspace")

    try:
        project_id = state.get("project_id", "")
        task_id = state.get("task_id", "")

        # Skip if already setup
        if state.get("workspace_ready"):
            logger.info("[setup_workspace] Workspace already ready, skipping")
            return {}

        # Get project path from database
        project_path = _get_project_path(project_id)
        if not project_path:
            logger.warning("[setup_workspace] Project path not found")
            return {
                "workspace_ready": False,
                "error": "Project path not configured",
            }

        main_workspace = str(project_path)

        # Get tech stack
        tech_stack = state.get("tech_stack") or _get_tech_stack(project_id)

        # Setup git worktree (with cleanup like developer_v2)
        workspace_info = _setup_git_worktree(
            task_id=task_id,
            main_workspace=main_workspace,
            agent_name="Tester",
        )

        workspace_path = workspace_info.get("workspace_path", main_workspace)
        branch_name = workspace_info.get("branch_name", "")
        workspace_ready = workspace_info.get("workspace_ready", False)

        # Load project context
        project_context = ""
        agents_md = ""
        if workspace_path:
            try:
                agents_md = _get_agents_md(workspace_path)
                project_context = _get_project_context(workspace_path)
                if agents_md:
                    logger.info(f"[setup_workspace] Loaded AGENTS.md: {len(agents_md)} chars")
            except Exception as e:
                logger.warning(f"[setup_workspace] Failed to load context: {e}")

        # Load skill registry
        skill_registry = SkillRegistry.load(tech_stack)
        logger.info(
            f"[setup_workspace] Loaded SkillRegistry for '{tech_stack}' "
            f"with {len(skill_registry.skills)} skills"
        )

        # Find bun
        bun_path = _get_bun_path()
        if not bun_path:
            logger.warning(
                "[setup_workspace] Bun not found. Please install: https://bun.sh/"
            )
        else:
            # Run bun install if needed
            pkg_json = os.path.join(workspace_path, "package.json")
            if os.path.exists(pkg_json):
                if _should_run_install(workspace_path):
                    _run_bun_install(workspace_path, bun_path)
                else:
                    logger.info("[setup_workspace] Skipping bun install (package.json unchanged)")
            
            # Run prisma generate if schema exists
            _run_prisma_generate(workspace_path, bun_path)

        return {
            "workspace_path": workspace_path,
            "branch_name": branch_name,
            "main_workspace": main_workspace,
            "workspace_ready": workspace_ready,
            "project_path": workspace_path,
            "project_context": project_context,
            "agents_md": agents_md,
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
