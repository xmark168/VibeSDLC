"""Setup workspace node - Setup git workspace/branch for test generation."""

import hashlib
import logging
import os
import subprocess
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.agents.tester.src.skills import SkillRegistry
from app.agents.tester.src.state import TesterState
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

    # Check for common config files
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


def _setup_git_worktree(
    task_id: str, main_workspace: str, agent_name: str = "tester"
) -> dict:
    """Setup git worktree for isolated test development.

    Returns:
        dict with workspace_path, branch_name, workspace_ready
    """
    try:
        main_path = Path(main_workspace)
        if not main_path.exists():
            logger.warning(
                f"[_setup_git_worktree] Main workspace not found: {main_workspace}"
            )
            return {
                "workspace_path": main_workspace,
                "branch_name": "",
                "main_workspace": main_workspace,
                "workspace_ready": False,
            }

        # Create branch name from task_id
        short_id = task_id.split("-")[-1][:8] if "-" in task_id else task_id[:8]
        branch_name = f"test_{short_id}"

        # Worktree path: parent_dir/.worktrees/branch_name
        worktrees_dir = main_path.parent / ".worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)
        worktree_path = worktrees_dir / branch_name

        # If worktree already exists, reuse it
        if worktree_path.exists():
            logger.info(
                f"[_setup_git_worktree] Reusing existing worktree: {worktree_path}"
            )
            return {
                "workspace_path": str(worktree_path),
                "branch_name": branch_name,
                "main_workspace": main_workspace,
                "workspace_ready": True,
            }

        # Create new worktree
        try:
            # First, try to create branch from main
            subprocess.run(
                ["git", "branch", branch_name, "main"],
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
                logger.info(f"[_setup_git_worktree] Created worktree: {worktree_path}")
                return {
                    "workspace_path": str(worktree_path),
                    "branch_name": branch_name,
                    "main_workspace": main_workspace,
                    "workspace_ready": True,
                }
            else:
                logger.warning(
                    f"[_setup_git_worktree] Worktree creation failed: {result.stderr}"
                )

        except subprocess.TimeoutExpired:
            logger.warning("[_setup_git_worktree] Git command timed out")
        except Exception as e:
            logger.warning(f"[_setup_git_worktree] Git error: {e}")

        # Fallback: use main workspace directly
        return {
            "workspace_path": main_workspace,
            "branch_name": "",
            "main_workspace": main_workspace,
            "workspace_ready": True,
        }

    except Exception as e:
        logger.error(f"[_setup_git_worktree] Error: {e}", exc_info=True)
        return {
            "workspace_path": main_workspace,
            "branch_name": "",
            "main_workspace": main_workspace,
            "workspace_ready": False,
        }





def _get_package_hash(workspace_path: str) -> str:
    """Get hash of package.json content."""
    pkg_path = os.path.join(workspace_path, "package.json")
    if not os.path.exists(pkg_path):
        return ""
    with open(pkg_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _should_run_install(workspace_path: str) -> bool:
    """Check if bun/npm install should run based on package.json hash."""
    hash_file = os.path.join(workspace_path, ".install-hash")
    current_hash = _get_package_hash(workspace_path)

    if not current_hash:
        return False

    if os.path.exists(hash_file):
        with open(hash_file) as f:
            cached_hash = f.read().strip()
        if cached_hash == current_hash:
            return False

    return True


def _save_package_hash(workspace_path: str):
    """Save current package.json hash."""
    hash_file = os.path.join(workspace_path, ".install-hash")
    current_hash = _get_package_hash(workspace_path)
    if current_hash:
        with open(hash_file, "w") as f:
            f.write(current_hash)


async def setup_workspace(state: TesterState, agent=None) -> dict:
    """Setup workspace for test generation.

    This node:
    1. Gets project path from database
    2. Creates git worktree for isolated test development
    3. Loads project context and AGENTS.md
    4. Initializes skill registry
    5. Runs package install if needed

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

        # Get project path
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

        # Setup git worktree
        workspace_info = _setup_git_worktree(
            task_id=task_id,
            main_workspace=main_workspace,
            agent_name="tester",
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
                    logger.info(
                        f"[setup_workspace] Loaded AGENTS.md: {len(agents_md)} chars"
                    )
            except Exception as e:
                logger.warning(f"[setup_workspace] Failed to load context: {e}")

        # Load skill registry
        skill_registry = SkillRegistry.load(tech_stack)
        logger.info(
            f"[setup_workspace] Loaded SkillRegistry for '{tech_stack}' with {len(skill_registry.skills)} skills"
        )

        # Run package install if needed
        if workspace_path and _should_run_install(workspace_path):
            try:
                # Detect package manager
                if (Path(workspace_path) / "bun.lockb").exists():
                    install_cmd = ["bun", "install"]
                elif (Path(workspace_path) / "pnpm-lock.yaml").exists():
                    install_cmd = ["pnpm", "install"]
                else:
                    install_cmd = ["npm", "install"]

                logger.info(f"[setup_workspace] Running {install_cmd[0]} install...")
                result = subprocess.run(
                    install_cmd,
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if result.returncode == 0:
                    _save_package_hash(workspace_path)
                    logger.info("[setup_workspace] Package install successful")
                else:
                    logger.warning(
                        f"[setup_workspace] Package install failed: {result.stderr[:200]}"
                    )
            except subprocess.TimeoutExpired:
                logger.warning("[setup_workspace] Package install timed out")
            except Exception as e:
                logger.warning(f"[setup_workspace] Package install error: {e}")
        else:
            if workspace_path:
                logger.info(
                    "[setup_workspace] Skipping install (package.json unchanged)"
                )

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
