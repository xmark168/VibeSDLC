# app/agents/developer/implementor/tools/__init__.py
"""
Tools for the Code Implementor Agent
"""

from .codebase_tools import (
    index_codebase_tool,
    load_codebase_tool,
    search_similar_code_tool,
)

# NEW: Direct filesystem tools (replacing Virtual FS)
from .filesystem_tools import (
    edit_file_tool,
    grep_search_tool,
    list_files_tool,
    read_file_tool,
    write_file_tool,
)
from .generation_tools import generate_code_tool, select_integration_strategy_tool
from .git_tools_gitpython import (
    commit_changes_tool,
    create_feature_branch_tool,
    create_pull_request_tool,
)
from .review_tools import collect_feedback_tool, refine_code_tool
from .shell_tools import (
    shell_execute_safe_tool,
    shell_execute_tool,
)
from .stack_tools import detect_stack_tool, retrieve_boilerplate_tool

# DEPRECATED: Virtual FS sync tools (no longer needed with direct disk tools)
# from .sync_tools import sync_virtual_to_disk_tool, list_virtual_files_tool

__all__ = [
    # Direct filesystem operations (NEW - replaces Virtual FS)
    "read_file_tool",
    "write_file_tool",
    "edit_file_tool",
    "list_files_tool",
    "grep_search_tool",
    # Shell execution
    "shell_execute_tool",
    "shell_execute_safe_tool",
    # Codebase operations
    "load_codebase_tool",
    "index_codebase_tool",
    "search_similar_code_tool",
    # Git operations
    "create_feature_branch_tool",
    "commit_changes_tool",
    "create_pull_request_tool",
    # Stack detection & boilerplate
    "detect_stack_tool",
    "retrieve_boilerplate_tool",
    # Code generation
    "select_integration_strategy_tool",
    "generate_code_tool",
    # Review & feedback
    "collect_feedback_tool",
    "refine_code_tool",
]
