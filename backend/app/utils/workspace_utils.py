"""Shared workspace utilities for all agents (Developer, Tester, BA, etc.)

This module provides unified workspace management functions including:
- Git worktree setup and cleanup
- Context file reading (AGENTS.md, README.md, etc.)
- Workspace commit operations
- ProjectWorkspaceManager class for workspace path management
"""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

logger = logging.getLogger(__name__)


# =============================================================================
# Git worktree management
# =============================================================================

def _kill_processes_in_directory(directory: Path, agent_name: str = "Agent") -> None:
    """Kill node processes that might be locking files (Windows only)."""
    import platform
    if platform.system() != "Windows":
        return
    try:
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True, timeout=10)
    except Exception:
        pass


def cleanup_old_worktree(
    main_workspace: Path,
    branch_name: str,
    worktree_path: Path,
    agent_name: str = "Agent"
) -> None:
    """
    Clean up worktree and branch
    """
    import platform
    
    # Prune first
    try:
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(main_workspace),
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass
    
    if worktree_path.exists():
        _kill_processes_in_directory(worktree_path, agent_name)
        
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=str(main_workspace),
                capture_output=True,
                timeout=30
            )
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
                            subprocess.run(
                                ["robocopy", empty_dir, str(worktree_path), "/mir", "/r:0", "/w:0",
                                 "/njh", "/njs", "/nc", "/ns", "/np", "/nfl", "/ndl"],
                                capture_output=True,
                                timeout=30
                            )
                            shutil.rmtree(empty_dir, ignore_errors=True)
                            shutil.rmtree(worktree_path, ignore_errors=True)
                        except Exception:
                            logger.error(f"[{agent_name}] Failed to remove directory: {e}")
    
    # Prune again + delete branch
    try:
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=str(main_workspace),
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass
    try:
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=str(main_workspace),
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass


def setup_git_worktree(
    story_code: str,
    main_workspace: Path | str,
    worktree_type: str = "story",
    agent_name: str = "Agent"
) -> dict:
    """
    Setup git worktree for agent tasks.
    """
    main_workspace = Path(main_workspace).resolve()
    safe_code = story_code.replace('/', '-').replace('\\', '-')
    short_id = story_code.split('-')[-1][:8] if '-' in story_code else story_code[:8]
    
    # Determine branch name and worktree path based on type
    if worktree_type == "story":
        branch_name = f"story_{safe_code}"
        worktrees_dir = main_workspace / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)
        worktree_path = (worktrees_dir / safe_code).resolve()
    elif worktree_type == "test":
        branch_name = f"test_{short_id}"
        worktree_path = (main_workspace.parent / f"ws_test_{short_id}").resolve()
    elif worktree_type == "ba":
        branch_name = f"ba_{safe_code}"
        worktrees_dir = main_workspace / ".worktrees"
        worktrees_dir.mkdir(exist_ok=True)
        worktree_path = (worktrees_dir / f"ba_{safe_code}").resolve()
    else:
        raise ValueError(f"Unknown worktree_type: {worktree_type}")
    
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
    
    # Auto-commit uncommitted files so worktree has them (story type only)
    if worktree_type == "story":
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(main_workspace),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if status.returncode == 0 and status.stdout.strip():
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=str(main_workspace),
                    capture_output=True,
                    timeout=30
                )
                subprocess.run(
                    ["git", "commit", "-m", "Auto-commit before worktree creation"],
                    cwd=str(main_workspace),
                    capture_output=True,
                    timeout=30,
                )
                logger.debug(f"[{agent_name}] Auto-committed uncommitted files")
        except Exception as e:
            logger.warning(f"[{agent_name}] Auto-commit failed: {e}")
    
    logger.info(f"[{agent_name}] Creating worktree '{branch_name}' at: {worktree_path}")
    
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
    
    logger.info(f"[{agent_name}] Result: {worktree_result.stdout or worktree_result.stderr}")
    
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


def commit_workspace_changes(
    workspace_path: str | Path,
    title: str,
    branch_name: str = "unknown",
    agent_name: str = "Agent"
) -> dict:
    """Commit changes in a workspace.
    
    Args:
        workspace_path: Path to workspace directory
        title: Commit message title
        branch_name: Git branch name for logging
        agent_name: Agent name for logging
    
    Returns:
        dict with keys:
        - success: bool indicating if commit succeeded
        - message: Status message
    """
    if not workspace_path:
        return {"success": True, "message": "No workspace to commit"}
    
    workspace_path = Path(workspace_path)
    
    # Check status
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(workspace_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    
    if not status_result.stdout.strip():
        return {"success": True, "message": "No changes to commit"}
    
    # Stage all changes
    subprocess.run(
        ["git", "add", "-A"],
        cwd=str(workspace_path),
        capture_output=True,
        timeout=30,
    )
    
    # Commit
    commit_msg = f"{agent_name.lower()}: {title[:50]}"
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=str(workspace_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    logger.info(f"[{agent_name}] Committed on '{branch_name}': {commit_result.stdout or commit_result.stderr}")
    
    if commit_result.returncode == 0:
        return {"success": True, "message": f"Committed: {commit_msg}"}
    return {"success": False, "message": commit_result.stderr[:200]}


# =============================================================================
# Context helpers
# =============================================================================

def get_agents_md(workspace_path: str | Path) -> str:
    """Read AGENTS.md from workspace root.
    
    Args:
        workspace_path: Path to workspace directory
    
    Returns:
        Content of AGENTS.md file, or empty string if not found
    """
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
    """Read project context files (README.md, package.json summary).
    
    Args:
        workspace_path: Path to workspace directory
    
    Returns:
        Concatenated content of context files
    """
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


def get_story_workspace(story_id: str) -> dict | None:
    """Get workspace path from Story model (created by Developer).
    
    Args:
        story_id: Story UUID
    
    Returns:
        dict with workspace_path, branch_name, main_workspace if found, None otherwise
    """
    from app.core.db import engine
    from app.models import Story
    
    try:
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id))
            if story and story.worktree_path:
                workspace_path = Path(story.worktree_path)
                if workspace_path.exists():
                    logger.info(f"[get_story_workspace] Found developer workspace: {workspace_path}")
                    return {
                        "workspace_path": str(workspace_path),
                        "branch_name": story.branch_name or f"story_{story_id.split('-')[-1][:8]}",
                        "main_workspace": str(workspace_path.parent.parent) if ".worktrees" in str(workspace_path) else str(workspace_path),
                    }
                else:
                    logger.warning(f"[get_story_workspace] Workspace path not found: {workspace_path}")
    except Exception as e:
        logger.warning(f"[get_story_workspace] Error: {e}")
    return None


# =============================================================================
# Dependency management helpers (from developer)
# =============================================================================

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


# =============================================================================
# Workspace manager class
# =============================================================================

class ProjectWorkspaceManager:
    """Git worktree manager for project workspace paths.
    
    Manages main workspace path and task-specific worktree paths.
    """
    
    def __init__(self, project_id: UUID):
        """Initialize workspace manager for a project.
        
        Args:
            project_id: Project UUID
        """
        self.project_id = project_id
        self._project_path = None
        self._load_project_path()

    def _load_project_path(self):
        """Load project_path from database."""
        from app.core.db import engine
        from app.models import Project
        
        with Session(engine) as session:
            project = session.get(Project, self.project_id)
            if project and project.project_path:
                # Convert relative path to absolute
                backend_root = Path(__file__).resolve().parent.parent.parent
                self._project_path = (backend_root / project.project_path).resolve()
                logger.info(f"Loaded project path from DB: {self._project_path}")
            else:
                logger.warning(f"Project {self.project_id} has no project_path, using fallback")
                backend_root = Path(__file__).resolve().parent.parent.parent
                self._project_path = backend_root / "projects" / str(self.project_id)

    def get_main_workspace(self) -> Path:
        """Get main workspace path (project_path from DB).
        
        Returns:
            Path to main workspace
        """
        if not self._project_path.exists():
            logger.warning(f"Project path does not exist: {self._project_path}")
        return self._project_path

    def get_task_workspace(self, story_id: str) -> Path:
        """Get worktree path for a story: {project_path}_{story_id}.
        
        Args:
            story_id: Story UUID or code
        
        Returns:
            Path to task workspace
        """
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        return Path(f"{self._project_path}_{short_id}")
