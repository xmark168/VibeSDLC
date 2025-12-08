"""Workspace management tools for Developer V2."""

import logging
import os
import shutil
import stat
import subprocess
from pathlib import Path

from ._base_context import set_tool_context
from .git_tools import (
    _git_status, _git_commit,
    _git_create_worktree, _git_remove_worktree, _git_delete_branch
)

logger = logging.getLogger(__name__)


def _force_remove_dir(path: Path) -> bool:
    """Force remove directory, handles Windows long paths and read-only files."""
    if not path.exists():
        return True
    
    try:
        # Windows: use rd /s /q for long paths in node_modules
        if os.name == 'nt':
            result = subprocess.run(
                f'rd /s /q "{path}"',
                shell=True, capture_output=True, timeout=60
            )
            if not path.exists():
                return True
        
        # Fallback: shutil.rmtree with error handler
        def on_rm_error(func, path, exc_info):
            # Handle read-only files
            os.chmod(path, stat.S_IWRITE)
            func(path)
        
        shutil.rmtree(path, onerror=on_rm_error)
        return not path.exists()
    except Exception as e:
        logger.warning(f"[workspace] Force remove failed: {e}")
        return False


def cleanup_old_worktree(main_workspace: Path, branch_name: str, agent_name: str = "Developer"):
    """Clean up existing worktree directory and branch."""
    short_id = branch_name.replace("story_", "")
    worktree_path = main_workspace.parent / f"ws_story_{short_id}"
    
    if worktree_path.exists():
        logger.info(f"[{agent_name}] Removing worktree: {worktree_path}")
        try:
            set_tool_context(root_dir=str(main_workspace))
            _git_remove_worktree(str(worktree_path))
        except Exception as e:
            logger.warning(f"[{agent_name}] Git worktree remove failed: {e}")
        
        if worktree_path.exists():
            if not _force_remove_dir(worktree_path):
                logger.error(f"[{agent_name}] Failed to remove directory: {worktree_path}")
    
    try:
        set_tool_context(root_dir=str(main_workspace))
        _git_delete_branch(branch_name)
        logger.info(f"[{agent_name}] Deleted branch: {branch_name}")
    except Exception as e:
        logger.debug(f"[{agent_name}] Branch delete (may not exist): {e}")


def setup_git_worktree(
    story_id: str,
    main_workspace: Path | str,
    agent_name: str = "Developer"
) -> dict:
    """Setup git worktree for a story task."""
    main_workspace = Path(main_workspace)
    short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
    branch_name = f"story_{short_id}"
    
    if not main_workspace.exists():
        logger.error(f"[{agent_name}] Workspace does not exist: {main_workspace}")
        return {"workspace_path": str(main_workspace), "branch_name": branch_name,
                "main_workspace": str(main_workspace), "workspace_ready": False}
    
    set_tool_context(root_dir=str(main_workspace))
    status_result = _git_status()
    
    if "not a git repository" in status_result.lower() or "fatal" in status_result.lower():
        logger.error(f"[{agent_name}] Not a git repo: {main_workspace}")
        return {"workspace_path": str(main_workspace), "branch_name": branch_name,
                "main_workspace": str(main_workspace), "workspace_ready": False}
    
    cleanup_old_worktree(main_workspace, branch_name, agent_name)
    
    logger.info(f"[{agent_name}] Creating worktree for '{branch_name}'")
    worktree_result = _git_create_worktree(branch_name)
    logger.info(f"[{agent_name}] Result: {worktree_result}")
    
    worktree_path = main_workspace.parent / f"ws_story_{short_id}"
    workspace_ready = worktree_path.exists() and worktree_path.is_dir()
    
    if not workspace_ready:
        logger.warning(f"[{agent_name}] Worktree not created, using main")
        worktree_path = main_workspace
    
    return {"workspace_path": str(worktree_path), "branch_name": branch_name,
            "main_workspace": str(main_workspace), "workspace_ready": workspace_ready}


def commit_workspace_changes(
    workspace_path: str | Path,
    title: str,
    branch_name: str = "unknown",
    agent_name: str = "Developer"
) -> str:
    """Commit changes in a workspace."""
    if not workspace_path:
        return "No workspace to commit"
    
    workspace_path = Path(workspace_path)
    set_tool_context(root_dir=str(workspace_path))
    
    status = _git_status()
    if "nothing to commit" in status.lower() or "clean" in status.lower():
        return "No changes to commit"
    
    commit_msg = f"feat: {title[:50]}"
    result = _git_commit(commit_msg, ".")
    logger.info(f"[{agent_name}] Committed on '{branch_name}': {result}")
    
    return result


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
            import json
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            parts.append(f"## package.json\nname: {pkg.get('name', 'unknown')}\ndependencies: {list(pkg.get('dependencies', {}).keys())[:10]}")
        except Exception:
            pass
    
    return "\n\n".join(parts)
