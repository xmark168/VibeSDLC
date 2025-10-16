# app/agents/developer/implementor/tools/__init__.py
"""
Tools for the Code Implementor Agent
"""

from .codebase_tools import load_codebase_tool, index_codebase_tool, search_similar_code_tool
from .git_tools_gitpython import (
    create_feature_branch_tool,
    commit_changes_tool,
    create_pull_request_tool,
)
from .stack_tools import detect_stack_tool, retrieve_boilerplate_tool
from .generation_tools import select_integration_strategy_tool, generate_code_tool
from .review_tools import collect_feedback_tool, refine_code_tool
from .sync_tools import sync_virtual_to_disk_tool, list_virtual_files_tool

__all__ = [
    # Codebase operations
    "load_codebase_tool",
    "index_codebase_tool",
    "search_similar_code_tool",
    # Virtual FS sync operations
    "sync_virtual_to_disk_tool",
    "list_virtual_files_tool",
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
