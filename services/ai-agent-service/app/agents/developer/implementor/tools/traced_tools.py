"""
Traced Tool Wrappers for Langfuse Monitoring

This module provides wrapped versions of critical tools with enhanced Langfuse tracing.
These wrappers add detailed metadata and timing information for better observability.

Usage:
    Instead of importing tools directly, import from this module to get traced versions:
    
    from .traced_tools import (
        traced_load_codebase_tool,
        traced_create_feature_branch_tool,
        # ... other traced tools
    )
"""

import functools
import time
from typing import Any, Callable
from langchain_core.tools import BaseTool

try:
    from app.utils.langfuse_tracer import trace_span
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    from contextlib import contextmanager
    
    @contextmanager
    def trace_span(*args, **kwargs):
        yield None


def trace_tool_execution(tool_name: str, tool_type: str = "tool"):
    """
    Decorator to add Langfuse tracing to tool executions.
    
    Args:
        tool_name: Name of the tool for tracing
        tool_type: Type of tool (e.g., "codebase", "git", "generation")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not LANGFUSE_AVAILABLE:
                return func(*args, **kwargs)
            
            start_time = time.time()
            
            # Extract meaningful parameters for logging
            input_data = {
                "args": [str(arg)[:100] for arg in args],  # Truncate long args
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},
            }
            
            with trace_span(
                name=f"tool_{tool_name}",
                metadata={
                    "tool_name": tool_name,
                    "tool_type": tool_type,
                    "function": func.__name__,
                },
                input_data=input_data,
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Log success
                    if span:
                        # Try to extract meaningful output info
                        output_info = {"result_type": type(result).__name__}
                        if isinstance(result, str):
                            output_info["result_preview"] = result[:200]
                        elif isinstance(result, dict):
                            output_info["result_keys"] = list(result.keys())
                        
                        span.end(
                            output=output_info,
                            metadata={
                                "execution_time_seconds": execution_time,
                                "status": "success",
                            }
                        )
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    
                    # Log error
                    if span:
                        span.end(
                            level="ERROR",
                            status_message=str(e),
                            metadata={
                                "execution_time_seconds": execution_time,
                                "status": "error",
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                            }
                        )
                    
                    raise
        
        return wrapper
    return decorator


# Import original tools
from .codebase_tools import (
    load_codebase_tool,
    index_codebase_tool,
    search_similar_code_tool,
)
from .git_tools_gitpython import (
    create_feature_branch_tool,
    commit_changes_tool,
    create_pull_request_tool,
)
from .generation_tools import (
    select_integration_strategy_tool,
    generate_code_tool,
)
from .review_tools import (
    collect_feedback_tool,
    refine_code_tool,
)
from .sync_tools import (
    sync_virtual_to_disk_tool,
    list_virtual_files_tool,
)
from .stack_tools import (
    detect_stack_tool,
    retrieve_boilerplate_tool,
)


# Create traced versions of critical tools
# These wrap the original tools with Langfuse tracing

# Codebase tools
@trace_tool_execution("load_codebase", "codebase")
def traced_load_codebase_tool(*args, **kwargs):
    """Traced version of load_codebase_tool"""
    return load_codebase_tool.invoke(*args, **kwargs)


@trace_tool_execution("index_codebase", "codebase")
def traced_index_codebase_tool(*args, **kwargs):
    """Traced version of index_codebase_tool"""
    return index_codebase_tool.invoke(*args, **kwargs)


@trace_tool_execution("search_similar_code", "codebase")
def traced_search_similar_code_tool(*args, **kwargs):
    """Traced version of search_similar_code_tool"""
    return search_similar_code_tool.invoke(*args, **kwargs)


# Git tools
@trace_tool_execution("create_feature_branch", "git")
def traced_create_feature_branch_tool(*args, **kwargs):
    """Traced version of create_feature_branch_tool"""
    return create_feature_branch_tool.invoke(*args, **kwargs)


@trace_tool_execution("commit_changes", "git")
def traced_commit_changes_tool(*args, **kwargs):
    """Traced version of commit_changes_tool"""
    return commit_changes_tool.invoke(*args, **kwargs)


@trace_tool_execution("create_pull_request", "git")
def traced_create_pull_request_tool(*args, **kwargs):
    """Traced version of create_pull_request_tool"""
    return create_pull_request_tool.invoke(*args, **kwargs)


# Generation tools
@trace_tool_execution("select_integration_strategy", "generation")
def traced_select_integration_strategy_tool(*args, **kwargs):
    """Traced version of select_integration_strategy_tool"""
    return select_integration_strategy_tool.invoke(*args, **kwargs)


@trace_tool_execution("generate_code", "generation")
def traced_generate_code_tool(*args, **kwargs):
    """Traced version of generate_code_tool"""
    return generate_code_tool.invoke(*args, **kwargs)


# Review tools
@trace_tool_execution("collect_feedback", "review")
def traced_collect_feedback_tool(*args, **kwargs):
    """Traced version of collect_feedback_tool"""
    return collect_feedback_tool.invoke(*args, **kwargs)


@trace_tool_execution("refine_code", "review")
def traced_refine_code_tool(*args, **kwargs):
    """Traced version of refine_code_tool"""
    return refine_code_tool.invoke(*args, **kwargs)


# Sync tools
@trace_tool_execution("sync_virtual_to_disk", "sync")
def traced_sync_virtual_to_disk_tool(*args, **kwargs):
    """Traced version of sync_virtual_to_disk_tool"""
    return sync_virtual_to_disk_tool.invoke(*args, **kwargs)


@trace_tool_execution("list_virtual_files", "sync")
def traced_list_virtual_files_tool(*args, **kwargs):
    """Traced version of list_virtual_files_tool"""
    return list_virtual_files_tool.invoke(*args, **kwargs)


# Stack tools
@trace_tool_execution("detect_stack", "stack")
def traced_detect_stack_tool(*args, **kwargs):
    """Traced version of detect_stack_tool"""
    return detect_stack_tool.invoke(*args, **kwargs)


@trace_tool_execution("retrieve_boilerplate", "stack")
def traced_retrieve_boilerplate_tool(*args, **kwargs):
    """Traced version of retrieve_boilerplate_tool"""
    return retrieve_boilerplate_tool.invoke(*args, **kwargs)


# Export all traced tools
__all__ = [
    # Traced versions
    "traced_load_codebase_tool",
    "traced_index_codebase_tool",
    "traced_search_similar_code_tool",
    "traced_create_feature_branch_tool",
    "traced_commit_changes_tool",
    "traced_create_pull_request_tool",
    "traced_select_integration_strategy_tool",
    "traced_generate_code_tool",
    "traced_collect_feedback_tool",
    "traced_refine_code_tool",
    "traced_sync_virtual_to_disk_tool",
    "traced_list_virtual_files_tool",
    "traced_detect_stack_tool",
    "traced_retrieve_boilerplate_tool",
    # Original tools (for backward compatibility)
    "load_codebase_tool",
    "index_codebase_tool",
    "search_similar_code_tool",
    "create_feature_branch_tool",
    "commit_changes_tool",
    "create_pull_request_tool",
    "select_integration_strategy_tool",
    "generate_code_tool",
    "collect_feedback_tool",
    "refine_code_tool",
    "sync_virtual_to_disk_tool",
    "list_virtual_files_tool",
    "detect_stack_tool",
    "retrieve_boilerplate_tool",
]

