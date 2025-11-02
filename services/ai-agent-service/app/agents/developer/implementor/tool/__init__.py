# app/agents/developer/implementor/tool/__init__.py
"""
Tools for the Implementor Agent

Các tools được sử dụng trong implementor workflow để:
- Thực hiện file operations (read, write, edit)
- Chạy shell commands
- Quản lý Git operations
- Detect project stack và retrieve boilerplate
"""

from .external_file_tools import copy_directory_from_external_tool
from .filesystem_tools import (
    create_directory_tool,
    grep_search_tool,
    list_files_tool,
    read_file_tool,
    str_replace_tool,
    write_file_tool,
)
from .git_tools_gitpython import (
    commit_changes_tool,
    create_feature_branch_tool,
    create_pull_request_tool,
)
from .incremental_tools import (
    add_function_tool,
    add_import_tool,
    create_method_tool,
    modify_function_tool,
)
from .shell_tools import (
    shell_execute_safe_tool,
    shell_execute_tool,
)
from .stack_tools import detect_stack_tool, retrieve_boilerplate_tool

__all__ = [
    # Filesystem operations
    "read_file_tool",
    "write_file_tool",
    "str_replace_tool",
    "list_files_tool",
    "grep_search_tool",
    "create_directory_tool",
    # External file operations
    "copy_directory_from_external_tool",
    # Shell execution
    "shell_execute_tool",
    "shell_execute_safe_tool",
    # Git operations
    "create_feature_branch_tool",
    "commit_changes_tool",
    "create_pull_request_tool",
    # Incremental code editing
    "add_function_tool",
    "add_import_tool",
    "create_method_tool",
    "modify_function_tool",
    # Stack detection & boilerplate
    "detect_stack_tool",
    "retrieve_boilerplate_tool",
]
