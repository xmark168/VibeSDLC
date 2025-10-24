"""
Filesystem Adapter Implementations

Provides abstraction layer cho filesystem operations với 2 implementations:
- LocalFilesystemAdapter: Local filesystem operations using Path()
- DaytonaFilesystemAdapter: Daytona sandbox filesystem operations
"""

import json
import os
from pathlib import Path

from ..config import DaytonaConfig
from ..sandbox_manager import SandboxManager, get_sandbox_manager
from .base import FilesystemAdapter


class LocalFilesystemAdapter(FilesystemAdapter):
    """
    Local filesystem operations using Path().

    Copy logic từ filesystem_tools.py để maintain backward compatibility.
    """

    def read_file(
        self,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        working_directory: str = ".",
    ) -> str:
        """Read file from local filesystem with line numbers (cat -n format)."""
        try:
            # Resolve full path
            full_path = Path(working_directory) / file_path
            full_path = full_path.resolve()

            # Security check: prevent path traversal
            working_dir_resolved = Path(working_directory).resolve()
            if not str(full_path).startswith(str(working_dir_resolved)):
                return "Error: Access denied - path outside working directory"

            # Check file exists
            if not full_path.exists():
                return f"Error: File '{file_path}' does not exist"

            if not full_path.is_file():
                return f"Error: '{file_path}' is not a file"

            # Read file
            with open(full_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Apply line range
            if start_line is not None or end_line is not None:
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                lines = lines[start:end]
                line_offset = start + 1
            else:
                line_offset = 1

            # Format with line numbers (cat -n format)
            formatted_lines = [
                f"{i + line_offset:6d}\t{line.rstrip()}" for i, line in enumerate(lines)
            ]

            return "\n".join(formatted_lines)

        except PermissionError:
            return f"Error: Permission denied reading '{file_path}'"
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def write_file(
        self,
        file_path: str,
        content: str,
        working_directory: str = ".",
        create_dirs: bool = True,
    ) -> str:
        """Write content to file on local filesystem."""
        try:
            # Resolve full path
            full_path = Path(working_directory) / file_path
            full_path = full_path.resolve()

            # Security check
            working_dir_resolved = Path(working_directory).resolve()
            if not str(full_path).startswith(str(working_dir_resolved)):
                return json.dumps(
                    {
                        "status": "error",
                        "message": "Access denied - path outside working directory",
                    }
                )

            # Create parent directories if needed
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            full_path.write_text(content, encoding="utf-8")

            lines_count = content.count("\n") + 1
            bytes_count = len(content.encode("utf-8"))

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Successfully wrote {lines_count} lines ({bytes_count} bytes) to '{file_path}'",
                }
            )

        except PermissionError:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Permission denied writing to '{file_path}'",
                }
            )
        except Exception as e:
            return json.dumps(
                {"status": "error", "message": f"Error writing file: {str(e)}"}
            )

    def list_files(
        self,
        directory: str = ".",
        pattern: str = "*",
        recursive: bool = False,
        working_directory: str = ".",
    ) -> str:
        """List files in directory with glob pattern."""
        try:
            # Resolve full path
            full_path = Path(working_directory) / directory
            full_path = full_path.resolve()

            # Security check
            working_dir_resolved = Path(working_directory).resolve()
            if not str(full_path).startswith(str(working_dir_resolved)):
                return "Error: Access denied - path outside working directory"

            # Check directory exists
            if not full_path.exists():
                return f"Error: Directory '{directory}' does not exist"

            if not full_path.is_dir():
                return f"Error: '{directory}' is not a directory"

            # List files
            if recursive:
                files = list(full_path.rglob(pattern))
            else:
                files = list(full_path.glob(pattern))

            # Filter only files (not directories)
            files = [f for f in files if f.is_file()]

            # Make paths relative to working_directory
            relative_files = [str(f.relative_to(working_dir_resolved)) for f in files]

            if not relative_files:
                return f"No files found matching pattern '{pattern}' in '{directory}'"

            return "\n".join(sorted(relative_files))

        except Exception as e:
            return f"Error listing files: {str(e)}"

    def delete_file(self, file_path: str, working_directory: str = ".") -> str:
        """Delete file from local filesystem."""
        try:
            # Resolve full path
            full_path = Path(working_directory) / file_path
            full_path = full_path.resolve()

            # Security check
            working_dir_resolved = Path(working_directory).resolve()
            if not str(full_path).startswith(str(working_dir_resolved)):
                return json.dumps(
                    {
                        "status": "error",
                        "message": "Access denied - path outside working directory",
                    }
                )

            # Check file exists
            if not full_path.exists():
                return json.dumps(
                    {"status": "error", "message": f"File '{file_path}' does not exist"}
                )

            if not full_path.is_file():
                return json.dumps(
                    {"status": "error", "message": f"'{file_path}' is not a file"}
                )

            # Delete file
            full_path.unlink()

            return json.dumps(
                {"status": "success", "message": f"Successfully deleted '{file_path}'"}
            )

        except PermissionError:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Permission denied deleting '{file_path}'",
                }
            )
        except Exception as e:
            return json.dumps(
                {"status": "error", "message": f"Error deleting file: {str(e)}"}
            )

    def create_directory(
        self, directory: str, working_directory: str = ".", mode: str = "755"
    ) -> str:
        """Create directory on local filesystem."""
        try:
            # Resolve full path
            full_path = Path(working_directory) / directory
            full_path = full_path.resolve()

            # Security check
            working_dir_resolved = Path(working_directory).resolve()
            if not str(full_path).startswith(str(working_dir_resolved)):
                return json.dumps(
                    {
                        "status": "error",
                        "message": "Access denied - path outside working directory",
                    }
                )

            # Create directory
            full_path.mkdir(parents=True, exist_ok=True)

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Successfully created directory '{directory}'",
                }
            )

        except PermissionError:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Permission denied creating directory '{directory}'",
                }
            )
        except Exception as e:
            return json.dumps(
                {"status": "error", "message": f"Error creating directory: {str(e)}"}
            )


class DaytonaFilesystemAdapter(FilesystemAdapter):
    """
    Daytona sandbox filesystem operations.

    Uses Daytona Sandbox Filesystem API (sandbox.fs.*).
    """

    def __init__(self, sandbox_manager: SandboxManager):
        """
        Initialize DaytonaFilesystemAdapter.

        Args:
            sandbox_manager: SandboxManager instance
        """
        self.sandbox_manager = sandbox_manager
        self.sandbox = sandbox_manager.get_sandbox()

    def _resolve_sandbox_path(self, file_path: str, working_directory: str) -> str:
        """
        Resolve local relative path to sandbox absolute path.

        Args:
            file_path: Relative file path
            working_directory: Working directory (e.g., "." or "/root/workspace/repo")

        Returns:
            Absolute path in sandbox (e.g., "/root/workspace/repo/app/main.py")
        """
        # If working_directory is already absolute (starts with /), use it directly
        if working_directory.startswith("/"):
            base_path = working_directory
        else:
            # Convert relative path to sandbox workspace path
            base_path = self.sandbox_manager.get_workspace_path("repo")

        # Combine base path with file path
        if file_path == ".":
            return base_path

        # Remove leading "./" if present
        if file_path.startswith("./"):
            file_path = file_path[2:]

        return f"{base_path}/{file_path}"

    def read_file(
        self,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        working_directory: str = ".",
    ) -> str:
        """Read file from Daytona sandbox with line numbers (cat -n format)."""
        try:
            # Resolve to sandbox path
            sandbox_path = self._resolve_sandbox_path(file_path, working_directory)

            # Download file content from sandbox
            content = self.sandbox.fs.download_file(sandbox_path)

            # Split into lines
            lines = content.splitlines(keepends=True)

            # Apply line range
            if start_line is not None or end_line is not None:
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                lines = lines[start:end]
                line_offset = start + 1
            else:
                line_offset = 1

            # Format with line numbers (cat -n format)
            formatted_lines = [
                f"{i + line_offset:6d}\t{line.rstrip()}" for i, line in enumerate(lines)
            ]

            return "\n".join(formatted_lines)

        except Exception as e:
            return f"Error reading file from sandbox: {str(e)}"

    def write_file(
        self,
        file_path: str,
        content: str,
        working_directory: str = ".",
        create_dirs: bool = True,
    ) -> str:
        """Write content to file in Daytona sandbox."""
        try:
            # Resolve to sandbox path
            sandbox_path = self._resolve_sandbox_path(file_path, working_directory)

            # Create parent directories if needed
            if create_dirs:
                parent_dir = os.path.dirname(sandbox_path)
                if parent_dir and parent_dir != "/":
                    try:
                        self.sandbox.fs.create_folder(parent_dir, "755")
                    except Exception:
                        # Folder might already exist, continue
                        pass

            # Upload file to sandbox
            self.sandbox.fs.upload_file(content, sandbox_path)

            lines_count = content.count("\n") + 1
            bytes_count = len(content.encode("utf-8"))

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Successfully wrote {lines_count} lines ({bytes_count} bytes) to '{file_path}'",
                }
            )

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Error writing file to sandbox: {str(e)}",
                }
            )

    def list_files(
        self,
        directory: str = ".",
        pattern: str = "*",
        recursive: bool = False,
        working_directory: str = ".",
    ) -> str:
        """List files in Daytona sandbox directory."""
        try:
            # Resolve to sandbox path
            sandbox_path = self._resolve_sandbox_path(directory, working_directory)

            # List files from sandbox
            files_info = self.sandbox.fs.list_files(sandbox_path)

            # Filter files based on pattern (simple glob matching)
            # Note: Daytona API might not support glob patterns directly,
            # so we do client-side filtering
            import fnmatch

            matching_files = []
            for file_info in files_info:
                file_name = file_info.get("name", "")
                file_type = file_info.get("type", "")

                # Only include files (not directories)
                if file_type == "file":
                    # Check if matches pattern
                    if fnmatch.fnmatch(file_name, pattern):
                        # Make path relative to working_directory
                        if directory == ".":
                            relative_path = file_name
                        else:
                            relative_path = f"{directory}/{file_name}"
                        matching_files.append(relative_path)

            if not matching_files:
                return f"No files found matching pattern '{pattern}' in '{directory}'"

            return "\n".join(sorted(matching_files))

        except Exception as e:
            return f"Error listing files in sandbox: {str(e)}"

    def delete_file(self, file_path: str, working_directory: str = ".") -> str:
        """Delete file from Daytona sandbox."""
        try:
            # Resolve to sandbox path
            sandbox_path = self._resolve_sandbox_path(file_path, working_directory)

            # Delete file from sandbox
            self.sandbox.fs.delete_file(sandbox_path)

            return json.dumps(
                {"status": "success", "message": f"Successfully deleted '{file_path}'"}
            )

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Error deleting file from sandbox: {str(e)}",
                }
            )

    def create_directory(
        self, directory: str, working_directory: str = ".", mode: str = "755"
    ) -> str:
        """Create directory in Daytona sandbox."""
        try:
            # Resolve to sandbox path
            sandbox_path = self._resolve_sandbox_path(directory, working_directory)

            # Create folder in sandbox
            self.sandbox.fs.create_folder(sandbox_path, mode)

            return json.dumps(
                {
                    "status": "success",
                    "message": f"Successfully created directory '{directory}'",
                }
            )

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Error creating directory in sandbox: {str(e)}",
                }
            )


# ============================================================================
# ADAPTER FACTORY FUNCTION
# ============================================================================


def get_filesystem_adapter() -> FilesystemAdapter:
    """
    Get filesystem adapter based on configuration.

    Returns:
        DaytonaFilesystemAdapter if Daytona is enabled, LocalFilesystemAdapter otherwise
    """
    config = DaytonaConfig.from_env()

    if config and config.enabled:
        # Daytona mode: use sandbox filesystem
        sandbox_manager = get_sandbox_manager(config)
        if sandbox_manager and sandbox_manager.is_sandbox_active():
            return DaytonaFilesystemAdapter(sandbox_manager)
        else:
            print(
                "⚠️ Daytona enabled but no active sandbox. Falling back to local filesystem."
            )
            return LocalFilesystemAdapter()

    # Local mode: use local filesystem
    return LocalFilesystemAdapter()
