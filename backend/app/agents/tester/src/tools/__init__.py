"""Tools package for Tester Agent."""

from app.agents.tester.src.tools.skill_tools import (
    activate_skill,
    read_skill_file,
    list_skill_files,
    get_skill_tools,
    set_skill_context,
    reset_skill_cache,
    get_skill_catalog,
)

from app.agents.tester.src.tools.filesystem_tools import (
    glob_files,
    grep_files,
    read_file,
    write_file,
    edit_file,
    list_directory,
    get_project_structure,
    get_filesystem_tools,
    FILESYSTEM_TOOLS,
)

from app.agents.tester.src.tools.tester_tools import (
    get_test_files,
    read_test_file,
    get_test_summary,
    search_tests,
    get_stories_in_review,
    run_tests,
    create_bug_story,
    get_tester_tools,
    get_execution_tools,
    TESTER_TOOLS,
    TESTER_EXECUTION_TOOLS,
)

from app.utils.workspace_utils import (
    setup_git_worktree,
    commit_workspace_changes,
    get_agents_md,
    get_project_context,
)
from app.agents.tester.src.tools.workspace_tools import (
    cleanup_worktree,
    merge_to_main,
    revert_test_changes,
)

__all__ = [
    # Skill tools
    "activate_skill",
    "read_skill_file",
    "list_skill_files",
    "get_skill_tools",
    "set_skill_context",
    "reset_skill_cache",
    "get_skill_catalog",
    # Filesystem tools
    "glob_files",
    "grep_files",
    "read_file",
    "write_file",
    "edit_file",
    "list_directory",
    "get_project_structure",
    "get_filesystem_tools",
    "FILESYSTEM_TOOLS",
    # Tester tools
    "get_test_files",
    "read_test_file",
    "get_test_summary",
    "search_tests",
    "get_stories_in_review",
    "run_tests",
    "create_bug_story",
    "get_tester_tools",
    "get_execution_tools",
    "TESTER_TOOLS",
    "TESTER_EXECUTION_TOOLS",
    # Workspace tools
    "setup_git_worktree",
    "commit_workspace_changes",
    "cleanup_worktree",
    "merge_to_main",
    "revert_test_changes",
    "get_agents_md",
    "get_project_context",
]
