"""Unified Context for Developer V2 Tools.

Thread-safe context using contextvars to support multi-agent scenarios.
"""

import os
from contextvars import ContextVar
from typing import Optional

# Thread-safe context variable
_tool_context: ContextVar[dict] = ContextVar('tool_context', default={
    "root_dir": None,
    "project_id": None,
    "task_id": None,
})


def set_tool_context(
    root_dir: str = None,
    project_id: str = None,
    task_id: str = None
):
    """Set unified context for all tools. Thread-safe."""
    ctx = _tool_context.get().copy()
    if root_dir:
        ctx["root_dir"] = root_dir
    if project_id:
        ctx["project_id"] = project_id
    if task_id:
        ctx["task_id"] = task_id
    _tool_context.set(ctx)


def get_root_dir() -> str:
    """Get root directory from context or use cwd."""
    return _tool_context.get().get("root_dir") or os.getcwd()


def get_project_id() -> Optional[str]:
    """Get project ID from context."""
    return _tool_context.get().get("project_id")


def get_task_id() -> Optional[str]:
    """Get task ID from context."""
    return _tool_context.get().get("task_id")


def is_safe_path(path: str, root_dir: str = None) -> bool:
    """Check if path is within root directory (security sandbox)."""
    root = root_dir or get_root_dir()
    real_path = os.path.realpath(path)
    real_root = os.path.realpath(root)
    return real_path.startswith(real_root)


def reset_context():
    """Reset context to defaults. Useful for testing."""
    _tool_context.set({
        "root_dir": None,
        "project_id": None,
        "task_id": None,
    })
