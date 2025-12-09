"""Unified Context for Developer V2 Tools."""

import os
from contextvars import ContextVar

_tool_context: ContextVar[dict] = ContextVar('tool_context', default={
    "root_dir": None,
    "project_id": None,
    "task_id": None,
})


def set_tool_context(root_dir: str = None, project_id: str = None, task_id: str = None):
    """Set unified context for all tools."""
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


def is_safe_path(path: str, root_dir: str = None) -> bool:
    """Check if path is within root directory."""
    root = root_dir or get_root_dir()
    return os.path.realpath(path).startswith(os.path.realpath(root))
