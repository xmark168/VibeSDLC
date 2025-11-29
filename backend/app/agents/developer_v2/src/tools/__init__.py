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

__all__ = [
    # Context setters
    "set_fs_context",
    "set_git_context",
    "set_shell_context",
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
]
