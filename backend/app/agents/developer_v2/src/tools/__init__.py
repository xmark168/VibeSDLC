"""Developer V2 Tools - LangChain @tool decorated functions."""

# Unified context (single source of truth)
from ._base_context import (
    set_tool_context,
    get_root_dir,
    get_project_id,
    get_task_id,
    is_safe_path,
    reset_context,
)

# Filesystem tools
from .filesystem_tools import (
    read_file_safe,
    write_file_safe,
    list_directory_safe,
    delete_file_safe,
    copy_file_safe,
    move_file_safe,
    glob,
    grep_files,
    edit_file,
    multi_edit_file,
)

# Git tools
from .git_tools import (
    git_status,
    git_commit,
    git_create_branch,
    git_checkout,
    git_diff,
    git_merge,
    git_delete_branch,
    git_create_worktree,
    git_remove_worktree,
    git_list_worktrees,
)

# Shell tools
from .shell_tools import (
    execute_shell,
    run_shell,
)

# Execution tools
from .execution_tools import (
    CommandResult,
    install_dependencies,
    detect_test_command,
    execute_command_async,
    find_test_file,
)

# Workspace tools
from .workspace_tools import (
    setup_git_worktree,
    commit_workspace_changes,
)

# Skill tools (Claude-driven activation)
from .skill_tools import (
    set_skill_context,
    reset_skill_cache,
    activate_skill,
    read_skill_file,
    list_skill_files,
)

__all__ = [
    # Unified context
    "set_tool_context",
    "get_root_dir",
    "get_project_id",
    "get_task_id",
    "is_safe_path",
    "reset_context",
    # Filesystem
    "read_file_safe",
    "write_file_safe",
    "list_directory_safe",
    "delete_file_safe",
    "copy_file_safe",
    "move_file_safe",
    "glob",
    "grep_files",
    "edit_file",
    "multi_edit_file",
    # Git
    "git_status",
    "git_commit",
    "git_create_branch",
    "git_checkout",
    "git_diff",
    "git_merge",
    "git_delete_branch",
    "git_create_worktree",
    "git_remove_worktree",
    "git_list_worktrees",
    # Shell
    "execute_shell",
    "run_shell",
    # Execution
    "CommandResult",
    "install_dependencies",
    "detect_test_command",
    "execute_command_async",
    "find_test_file",
    # Workspace
    "setup_git_worktree",
    "commit_workspace_changes",
    # Skill tools
    "set_skill_context",
    "reset_skill_cache",
    "activate_skill",
    "read_skill_file",
    "list_skill_files",
]
