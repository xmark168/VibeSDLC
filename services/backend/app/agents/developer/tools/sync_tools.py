# app/agents/developer/implementor/tools/sync_tools.py
"""
Virtual File System Sync Tools

This module provides tools to sync files from DeepAgents virtual file system
(stored in LangGraph State) to the real disk file system.

This is necessary because:
1. DeepAgents uses a virtual/mock file system for isolation and safety
2. Git operations require files to exist on real disk
3. We need an explicit sync mechanism before committing changes
"""

import json
from pathlib import Path
from typing import Annotated, List, Any, Dict
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class SyncVirtualToDiskInput(BaseModel):
    """Input schema
    for sync_virtual_to_disk_tool."""

    working_directory: str = Field(..., description="Root directory to sync files to")
    file_patterns: List[str] | None = Field(
        None, description="Optional list of file patterns to sync"
    )
    overwrite_existing: bool = Field(
        True, description="Whether to overwrite existing files on disk"
    )
    create_backup: bool = Field(
        False, description="Whether to create .bak backup of existing files"
    )


@tool(args_schema=SyncVirtualToDiskInput)
def sync_virtual_to_disk_tool(
    working_directory: str,
    file_patterns: List[str] | None = None,
    overwrite_existing: bool = True,
    create_backup: bool = False,
) -> str:
    """
    Sync files from virtual file system (State["files"]) to real disk.

    This tool MUST be called BEFORE committing changes to Git, because:
    - DeepAgents file tools (write_file, edit_file) only modify virtual file system
    - Git operations require files to exist on real disk
    - This tool bridges the gap between virtual FS and real disk

    Args:
        working_directory: Root directory to sync files to (e.g., "D:\\demo")
        file_patterns: Optional list of file patterns to sync (e.g., ["*.py", "src/*"])
                      If None, syncs ALL files from virtual FS
        overwrite_existing: Whether to overwrite existing files on disk (default: True)
        create_backup: Whether to create .bak backup of existing files (default: False)

    Returns:
        JSON string with sync results:
        {
            "status": "success" | "partial" | "error",
            "synced_files": ["file1.py", "file2.py", ...],
            "skipped_files": ["file3.py", ...],
            "failed_files": [{"file": "file4.py", "error": "..."}],
            "count": 10,
            "total_size_bytes": 12345
        }

    Example:
        # Sync all files before committing
        sync_virtual_to_disk_tool(working_directory="D:\\demo")

        # Sync only Python files
        sync_virtual_to_disk_tool(
            working_directory="D:\\demo",
            file_patterns=["*.py", "**/*.py"]
        )

    Workflow:
        1. load_codebase_tool(working_directory)  # Analyze existing code
        2. generate_code_tool(...)                 # Generate code (virtual FS)
        3. sync_virtual_to_disk_tool(working_directory)  # ✅ Sync to disk
        4. commit_changes_tool(...)                # Now Git can see files
    """
    try:
        # Get virtual file system from DeepAgents state context
        state = None
        try:
            # Try to get state from DeepAgents context
            import contextvars

            # DeepAgents stores state in context vars
            for var in contextvars.copy_context().items():
                if hasattr(var[1], "get") and "files" in var[1]:
                    state = var[1]
                    break
        except Exception:
            pass

        # If still no state, try alternative method
        if state is None:
            try:
                from deepagents.state import get_current_state

                state = get_current_state()
            except (ImportError, RuntimeError, AttributeError):
                state = {}

        virtual_files = state.get("files", {}) if state else {}

        if not virtual_files:
            return json.dumps(
                {
                    "status": "success",
                    "message": "No files in virtual file system to sync",
                    "synced_files": [],
                    "skipped_files": [],
                    "failed_files": [],
                    "count": 0,
                    "total_size_bytes": 0,
                },
                indent=2,
            )

        # Resolve working directory
        working_dir = Path(working_directory).resolve()

        # Validate working directory
        if not working_dir.exists():
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Working directory does not exist: {working_directory}",
                    "synced_files": [],
                    "skipped_files": [],
                    "failed_files": [],
                    "count": 0,
                },
                indent=2,
            )

        if not working_dir.is_dir():
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Working directory is not a directory: {working_directory}",
                    "synced_files": [],
                    "skipped_files": [],
                    "failed_files": [],
                    "count": 0,
                },
                indent=2,
            )

        # Filter files by patterns if specified
        files_to_sync = {}
        if file_patterns:
            for file_path, content in virtual_files.items():
                if _matches_patterns(file_path, file_patterns):
                    files_to_sync[file_path] = content
        else:
            files_to_sync = virtual_files

        # Sync files to disk
        synced_files = []
        skipped_files = []
        failed_files = []
        total_size_bytes = 0

        for file_path, content in files_to_sync.items():
            try:
                # Resolve full path
                full_path = working_dir / file_path

                # Check if file already exists
                if full_path.exists() and not overwrite_existing:
                    skipped_files.append(file_path)
                    continue

                # Create backup if requested
                if create_backup and full_path.exists():
                    backup_path = full_path.with_suffix(full_path.suffix + ".bak")
                    try:
                        backup_path.write_text(
                            full_path.read_text(encoding="utf-8"), encoding="utf-8"
                        )
                    except Exception as backup_error:
                        # Log backup error but continue with sync
                        print(
                            f"Warning: Failed to create backup for {file_path}: {backup_error}"
                        )

                # Create parent directories if needed
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # Write file to disk
                full_path.write_text(content, encoding="utf-8")

                # Track success
                synced_files.append(file_path)
                total_size_bytes += len(content.encode("utf-8"))

            except PermissionError as e:
                failed_files.append(
                    {"file": file_path, "error": f"Permission denied: {str(e)}"}
                )
            except OSError as e:
                failed_files.append({"file": file_path, "error": f"OS error: {str(e)}"})
            except Exception as e:
                failed_files.append(
                    {"file": file_path, "error": f"Unexpected error: {str(e)}"}
                )

        # Determine overall status
        if failed_files:
            status = "partial" if synced_files else "error"
        else:
            status = "success"

        result = {
            "status": status,
            "synced_files": synced_files,
            "skipped_files": skipped_files,
            "failed_files": failed_files,
            "count": len(synced_files),
            "total_size_bytes": total_size_bytes,
            "working_directory": str(working_dir),
        }

        # Add summary message
        if status == "success":
            result["message"] = (
                f"Successfully synced {len(synced_files)} file(s) to disk"
            )
        elif status == "partial":
            result["message"] = (
                f"Synced {len(synced_files)} file(s), but {len(failed_files)} failed"
            )
        else:
            result["message"] = (
                f"Failed to sync files. {len(failed_files)} error(s) occurred"
            )

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "status": "error",
                "error": f"Sync operation failed: {str(e)}",
                "synced_files": [],
                "skipped_files": [],
                "failed_files": [],
                "count": 0,
            },
            indent=2,
        )


def _matches_patterns(file_path: str, patterns: List[str]) -> bool:
    """
    Check if file path matches any of the given patterns.

    Supports simple glob patterns:
    - *.py: matches any .py file in root
    - **/*.py: matches any .py file in any directory
    - src/*: matches any file in src directory
    """
    from fnmatch import fnmatch

    for pattern in patterns:
        if fnmatch(file_path, pattern):
            return True
        # Also check with ** wildcard for recursive matching
        if "**" in pattern:
            pattern_parts = pattern.split("**/")
            if len(pattern_parts) == 2:
                # Pattern like **/*.py
                if fnmatch(file_path, pattern_parts[1]) or fnmatch(
                    file_path, "*/" + pattern_parts[1]
                ):
                    return True

    return False


class ListVirtualFilesInput(BaseModel):
    """Input schema for list_virtual_files_tool."""

    show_content: bool = Field(
        False, description="Whether to show file content preview"
    )
    max_content_length: int = Field(
        100, description="Maximum characters to show per file"
    )


@tool(args_schema=ListVirtualFilesInput)
def list_virtual_files_tool(
    show_content: bool = False,
    max_content_length: int = 100,
) -> str:
    """
    List all files currently in the virtual file system.

    Useful for debugging and understanding what files are in memory
    before syncing to disk.

    Args:
        show_content: Whether to show file content preview (default: False)
        max_content_length: Maximum characters to show per file (default: 100)

    Returns:
        JSON string with list of virtual files and their metadata

    Example:
        list_virtual_files_tool()
    """
    try:
        # Get virtual file system from DeepAgents state context
        state = None
        try:
            # Try to get state from DeepAgents context
            import contextvars

            # DeepAgents stores state in context vars
            for var in contextvars.copy_context().items():
                if hasattr(var[1], "get") and "files" in var[1]:
                    state = var[1]
                    break
        except Exception:
            pass

        # If still no state, try alternative method
        if state is None:
            try:
                from deepagents.state import get_current_state

                state = get_current_state()
            except (ImportError, RuntimeError, AttributeError):
                state = {}

        virtual_files = state.get("files", {}) if state else {}

        if not virtual_files:
            return json.dumps(
                {
                    "status": "success",
                    "message": "Virtual file system is empty",
                    "files": [],
                    "count": 0,
                },
                indent=2,
            )

        files_info = []
        total_size = 0

        for file_path, content in virtual_files.items():
            file_size = len(content.encode("utf-8"))
            total_size += file_size

            file_info = {
                "path": file_path,
                "size_bytes": file_size,
                "lines": content.count("\n") + 1,
            }

            if show_content:
                preview = content[:max_content_length]
                if len(content) > max_content_length:
                    preview += "..."
                file_info["content_preview"] = preview

            files_info.append(file_info)

        # Sort by path
        files_info.sort(key=lambda x: x["path"])

        return json.dumps(
            {
                "status": "success",
                "files": files_info,
                "count": len(files_info),
                "total_size_bytes": total_size,
                "message": f"Found {len(files_info)} file(s) in virtual file system",
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {
                "status": "error",
                "error": f"Failed to list virtual files: {str(e)}",
                "files": [],
                "count": 0,
            },
            indent=2,
        )
