"""Shared helper functions for Developer V2 nodes."""
import logging

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools import set_tool_context

logger = logging.getLogger(__name__)


def setup_tool_context(workspace_path: str = None, project_id: str = None, task_id: str = None):
    """Set global context for all tools before agent invocation."""
    set_tool_context(root_dir=workspace_path, project_id=project_id, task_id=task_id)


def get_langfuse_span(state: DeveloperState, name: str, input_data: dict = None):
    """Get Langfuse span if handler is available."""
    handler = state.get("langfuse_handler")
    if not handler:
        return None
    try:
        from langfuse import get_client
        langfuse = get_client()
        return langfuse.span(name=name, input=input_data or {})
    except Exception:
        return None
