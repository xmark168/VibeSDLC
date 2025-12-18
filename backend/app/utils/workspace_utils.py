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

def _find_handle_exe() -> str | None:
    """Find handle.exe in common locations."""
    import os
    import shutil
    
    # Check common install locations
    locations = [
        r"C:\Program Files\Sysinternals\handle.exe",
        r"C:\Windows\System32\handle.exe",
        r"C:\Sysinternals\handle.exe",
    ]
    
    for path in locations:
        if os.path.exists(path):
            return path
    
    # Check if it's in PATH
    if shutil.which("handle.exe"):
        return "handle.exe"
    
    return None


def _kill_with_handle_exe(directory: Path, agent_name: str = "Agent") -> bool:
    """Kill processes using handle.exe with process name filter for faster scanning.
    
    Uses -p filter to scan only common workspace-locking processes (node, Code, git, etc.)
    This makes scanning 5-10x faster by skipping irrelevant processes like chrome, explorer, etc.
    """
    handle_exe = _find_handle_exe()
    if not handle_exe:
        logger.debug(f"[{agent_name}] handle.exe not found")
        return False
    
    try:
        # Process filter for common workspace-locking processes
        # This makes scanning 5-10x faster by skipping irrelevant processes
        process_filter = "node,Code,git,pnpm,npm,yarn,tsc,webpack,vite,next,turbo"
        
        # Run handle.exe with -p filter
        # Note: handle.exe automatically searches recursively in all subdirectories
        start_time = time.time()
        result = subprocess.run(
            [handle_exe, "-accepteula", "-nobanner", "-p", process_filter, str(directory)],
            capture_output=True,
            text=True,
            timeout=5,  # Reduced from 10s to 5s (filtering makes it much faster)
            encoding='utf-8',
            errors='replace'
        )
        scan_elapsed = time.time() - start_time
        
        if result.returncode != 0:
            logger.debug(f"[{agent_name}] handle.exe failed: {result.stderr[:200]}")
            return False
        
        # Parse output to extract PIDs
        # Format: "process.exe    pid: 1234   type: File   C:\path\to\file"
        import re
        pids = set()
        process_names = {}
        
        for line in result.stdout.splitlines():
            # Look for "pid: XXXX" pattern
            pid_match = re.search(r'pid:\s*(\d+)', line)
            if pid_match:
                pid = int(pid_match.group(1))
                pids.add(pid)
                
                # Extract process name (first word on line)
                name_match = re.match(r'^(\S+)', line.strip())
                if name_match:
                    process_names[pid] = name_match.group(1)
        
        if not pids:
            logger.debug(f"[{agent_name}] No processes found by handle.exe (scanned in {scan_elapsed:.1f}s)")
            return True  # Success - nothing to kill
        
        # Kill each process
        killed_count = 0
        for pid in pids:
            proc_name = process_names.get(pid, "unknown")
            try:
                kill_result = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    timeout=3
                )
                if kill_result.returncode == 0:
                    logger.debug(f"[{agent_name}] Killed {proc_name} (PID {pid})")
                    killed_count += 1
            except Exception as e:
                logger.debug(f"[{agent_name}] Failed to kill PID {pid}: {e}")
        
        logger.info(f"[{agent_name}] Killed {killed_count}/{len(pids)} processes in {scan_elapsed:.1f}s (via handle.exe -p filter)")
        return True
    
    except subprocess.TimeoutExpired:
        logger.warning(f"[{agent_name}] handle.exe timed out")
        return False
    except Exception as e:
        logger.warning(f"[{agent_name}] handle.exe error: {e}")
        return False


def _kill_processes_in_directory(directory: Path, agent_name: str = "Agent") -> None:
    """Kill processes that are locking files in the specified directory (Windows only).
    
    Uses handle.exe from Sysinternals Suite for accurate file handle detection.
    If handle.exe is not available, logs a warning and continues (non-critical).
    """
    import platform
    if platform.system() != "Windows":
        return
    
    # Use handle.exe (most accurate method for Windows)
    if _kill_with_handle_exe(directory, agent_name):
        return
    
    # handle.exe not available or failed - log warning but continue
    logger.warning(f"[{agent_name}] handle.exe not available or failed. Install Sysinternals Suite for better performance.")


def cleanup_workspace(
    workspace_path: str | Path,
    repo_path: str | Path = None,
    branch_name: str = None,
    skip_node_modules: bool = False,
    agent_name: str = "Agent"
) -> None:
    """Unified workspace cleanup function.
    
    This function handles cleanup of any workspace directory with optional
    git worktree and branch cleanup.
    
    Args:
        workspace_path: Path to workspace/worktree to cleanup
        repo_path: Main git repository path (required for git operations)
        branch_name: Git branch name to delete (optional)
        skip_node_modules: If True, skip deleting node_modules (faster for restart)
        agent_name: Agent name for logging
        
    Usage:
        # Cleanup worktree with git operations
        cleanup_workspace(
            workspace_path="/path/to/.worktrees/US-001",
            repo_path="/path/to/main/repo",
            branch_name="story_US-001"
        )
        
        # Cleanup any directory without git operations
        cleanup_workspace(workspace_path="/path/to/temp/workspace")
    """
    import platform
    cleanup_start_time = time.time()
    
    workspace_path = Path(workspace_path)
    
    # STEP 1: Git cleanup FIRST (always run, even if directory doesn't exist)
    # This handles stale worktree registrations in .git/worktrees/
    if repo_path:
        repo_path = Path(repo_path)
        
        # Remove worktree from git's tracking
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(workspace_path), "--force"],
                cwd=str(repo_path),
                capture_output=True,
                timeout=10
            )
        except Exception:
            pass
        
        # Prune stale worktree entries
        try:
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=str(repo_path),
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass
        
        # Delete branch (if branch_name provided)
        if branch_name:
            try:
                subprocess.run(
                    ["git", "branch", "-D", branch_name],
                    cwd=str(repo_path),
                    capture_output=True,
                    timeout=10
                )
            except Exception:
                pass
    
    # STEP 2: Check if workspace directory exists
    if not workspace_path.exists():
        logger.debug(f"[{agent_name}] Git cleaned, workspace directory doesn't exist")
        cleanup_elapsed = time.time() - cleanup_start_time
        logger.info(f"[{agent_name}] Workspace cleanup completed in {cleanup_elapsed:.1f}s")
        return
    
    # STEP 3: Kill processes locking files
    _kill_processes_in_directory(workspace_path, agent_name)
    
    # STEP 4: Delete node_modules (much faster without it)
    if not skip_node_modules:
        node_modules_path = workspace_path / "node_modules"
        if node_modules_path.exists():
            logger.info(f"[{agent_name}] Deleting node_modules before workspace cleanup...")
            try:
                # Kill processes locking node_modules files
                _kill_processes_in_directory(node_modules_path, agent_name)
                time.sleep(1.5)  # Wait for processes to fully terminate
                
                # Try Windows-optimized deletion first
                success = False
                if platform.system() == "Windows":
                    success = _fast_delete_node_modules_windows(node_modules_path, agent_name)
                
                # Fallback to shutil if Windows method failed or not on Windows
                if not success:
                    logger.debug(f"[{agent_name}] Falling back to shutil.rmtree...")
                    start_time = time.time()
                    shutil.rmtree(node_modules_path, ignore_errors=True)
                    elapsed = time.time() - start_time
                    logger.info(f"[{agent_name}] node_modules deleted in {elapsed:.1f}s (shutil)")
                
                if not node_modules_path.exists():
                    logger.info(f"[{agent_name}] node_modules deleted successfully")
                else:
                    logger.warning(f"[{agent_name}] node_modules partially deleted, rất lâu")
            except Exception as e:
                logger.warning(f"[{agent_name}] Failed to pre-delete node_modules: {e}")
    else:
        logger.debug(f"[{agent_name}] Skipping node_modules delete")
    
    # STEP 5: Delete workspace directory with retry
    if workspace_path.exists():
        for attempt in range(3):
            # Kill processes BEFORE each attempt
            if attempt == 0 or attempt == 2:
                _kill_processes_in_directory(workspace_path, agent_name)
                time.sleep(1.0)  # Wait for process cleanup
            
            try:
                shutil.rmtree(workspace_path)
                logger.debug(f"[{agent_name}] Workspace deleted on attempt {attempt + 1}")
                break
            except Exception as e:
                if attempt < 2:
                    # Exponential backoff: 0.5s, 1.0s
                    time.sleep(0.5 * (2 ** attempt))
                else:
                    # Last attempt failed - log but continue
                    logger.warning(f"[{agent_name}] Failed to remove workspace after 3 attempts: {e}")
    
    # Log cleanup time for performance monitoring
    cleanup_elapsed = time.time() - cleanup_start_time
    logger.info(f"[{agent_name}] Workspace cleanup completed in {cleanup_elapsed:.1f}s")


def _fast_delete_node_modules_windows(node_modules_path: Path, agent_name: str = "Agent") -> bool:
    """Fast deletion of node_modules using Windows native commands.
    
    Uses cmd.exe rmdir which is much faster than Python's shutil.rmtree
    for directories with many small files (typical node_modules structure).
    
    Returns True if successful, False otherwise.
    """
    import platform
    if platform.system() != "Windows":
        return False
    
    if not node_modules_path.exists():
        return True
    
    try:
        start_time = time.time()
        logger.debug(f"[{agent_name}] Using Windows rmdir for fast deletion...")
        
        # Use native Windows command for fast deletion
        result = subprocess.run(
            ["cmd.exe", "/c", "rmdir", "/s", "/q", str(node_modules_path)],
            capture_output=True,
            timeout=60,
            text=True
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0 or not node_modules_path.exists():
            logger.info(f"[{agent_name}] node_modules deleted in {elapsed:.1f}s (Windows rmdir)")
            return True
        else:
            logger.debug(f"[{agent_name}] rmdir returned {result.returncode}: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning(f"[{agent_name}] Windows rmdir timed out after 60s")
        return False
    except Exception as e:
        logger.debug(f"[{agent_name}] Windows rmdir failed: {e}")
        return False


def cleanup_old_worktree(
    main_workspace: Path,
    branch_name: str,
    worktree_path: Path,
    agent_name: str = "Agent",
    skip_node_modules: bool = False
) -> None:
    """Clean up worktree and branch (legacy wrapper).
    
    This is a legacy wrapper around cleanup_workspace() for backward compatibility.
    New code should use cleanup_workspace() directly.
    
    Args:
        main_workspace: Main git repository path
        branch_name: Git branch name to delete
        worktree_path: Path to worktree to cleanup
        agent_name: Agent name for logging
        skip_node_modules: If True, skip deleting node_modules (faster for restart)
    """
    cleanup_workspace(
        workspace_path=worktree_path,
        repo_path=main_workspace,
        branch_name=branch_name,
        skip_node_modules=skip_node_modules,
        agent_name=agent_name
    )


def setup_git_worktree(
    story_code: str,
    main_workspace: Path | str,
    worktree_type: str = "story",
    agent_name: str = "Agent",
    skip_node_modules: bool = False
) -> dict:
    """Setup git worktree for agent tasks.
    
    Args:
        story_code: Story code (e.g., "US-001")
        main_workspace: Main git repository path
        worktree_type: Type of worktree ("story", "test", "ba")
        agent_name: Agent name for logging
        skip_node_modules: If True, skip deleting node_modules during cleanup (10x faster for restart)
    
    Returns:
        dict with workspace_path, branch_name, main_workspace, workspace_ready
    """
    setup_start_time = time.time()
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
    
    # Always clean up old worktree to ensure fresh state
    # Note: skip_node_modules can be used for faster cleanup if dependencies don't change
    cleanup_old_worktree(main_workspace, branch_name, worktree_path, agent_name, skip_node_modules)
    
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
    
    # Delete branch if exists (ensure clean state for new worktree)
    subprocess.run(
        ["git", "branch", "-D", branch_name],
        cwd=str(main_workspace),
        capture_output=True,
        timeout=10,
    )
    
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
    
    # Log total setup time for performance monitoring
    setup_elapsed = time.time() - setup_start_time
    logger.info(f"[{agent_name}] Workspace setup completed in {setup_elapsed:.1f}s")
    
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
