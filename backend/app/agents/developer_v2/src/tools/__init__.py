"""Developer V2 Tools - LangChain @tool decorated functions."""

# Filesystem tools
from .filesystem_tools import (
    set_fs_context,
    read_file_safe,
    write_file_safe,
    list_directory_safe,
    delete_file_safe,
    copy_file_safe,
    move_file_safe,
    search_files,
    edit_file,
)

# Git tools
from .git_tools import (
    set_git_context,
    git_init,
    git_status,
    git_commit,
    git_create_branch,
    git_checkout,
    git_push,
    git_diff,
    git_merge,
    git_delete_branch,
    git_create_worktree,
    git_remove_worktree,
    git_list_worktrees,
)

# Shell and search tools
from .shell_tools import (
    set_shell_context,
    execute_shell,
    web_search_ddg,
    semantic_code_search,
)

# CocoIndex and project context tools
from .cocoindex_tools import (
    set_tool_context,
    search_codebase,
    index_workspace,
    update_workspace_index,
    get_related_code_indexed,
    search_codebase_tool,
    reindex_workspace,
    get_related_code,
    get_project_structure,
    get_coding_guidelines,
    get_code_examples,
    get_project_info,
    detect_project_structure,
    get_agents_md,
    get_project_context,
    get_boilerplate_examples,
    validate_plan_file_paths,
    get_markdown_code_block_type,
)

# Code context tools
from .code_context_tools import (
    get_all_workspace_files,
    get_related_code_context,
    get_legacy_code,
    format_code_for_context,
)

# Execution tools
from .execution_tools import (
    CommandResult,
    install_dependencies,
    detect_framework_from_package_json,
    detect_test_command,
    execute_command_async,
    execute_command_sync,
    find_test_file,
)

__all__ = [
    # Context setters
    "set_fs_context",
    "set_git_context",
    "set_shell_context",
    "set_tool_context",
    # Filesystem
    "read_file_safe",
    "write_file_safe",
    "list_directory_safe",
    "delete_file_safe",
    "copy_file_safe",
    "move_file_safe",
    "search_files",
    "edit_file",
    # Git
    "git_init",
    "git_status",
    "git_commit",
    "git_create_branch",
    "git_checkout",
    "git_push",
    "git_diff",
    "git_merge",
    "git_delete_branch",
    "git_create_worktree",
    "git_remove_worktree",
    "git_list_worktrees",
    # Shell & Search
    "execute_shell",
    "web_search_ddg",
    "semantic_code_search",
    # CocoIndex & Project Context
    "search_codebase",
    "index_workspace",
    "update_workspace_index",
    "get_related_code_indexed",
    "search_codebase_tool",
    "reindex_workspace",
    "get_related_code",
    "get_project_structure",
    "get_coding_guidelines",
    "get_code_examples",
    "get_project_info",
    "detect_project_structure",
    "get_agents_md",
    "get_project_context",
    "get_boilerplate_examples",
    "validate_plan_file_paths",
    "get_markdown_code_block_type",
    # Code Context
    "get_all_workspace_files",
    "get_related_code_context",
    "get_legacy_code",
    "format_code_for_context",
    # Execution
    "CommandResult",
    "install_dependencies",
    "detect_framework_from_package_json",
    "detect_test_command",
    "execute_command_async",
    "execute_command_sync",
    "find_test_file",
]
