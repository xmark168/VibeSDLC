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

            # Debug logging
            print("    🔍 list_files DEBUG:")
            print(f"       - working_directory: {working_directory}")
            print(f"       - directory: {directory}")
            print(f"       - pattern: {pattern}")
            print(f"       - full_path: {full_path}")
            print(f"       - exists: {full_path.exists()}")
            print(
                f"       - is_dir: {full_path.is_dir() if full_path.exists() else 'N/A'}"
            )

            # Security check
            working_dir_resolved = Path(working_directory).resolve()
            if not str(full_path).startswith(str(working_dir_resolved)):
                return "Error: Access denied - path outside working directory"

            # Check directory exists
            if not full_path.exists():
                return f"Error: Directory '{directory}' does not exist (full path: {full_path})"

            if not full_path.is_dir():
                return (
                    f"Error: '{directory}' is not a directory (full path: {full_path})"
                )

            # List files
            if recursive:
                files = list(full_path.rglob(pattern))
            else:
                files = list(full_path.glob(pattern))

            print(f"       - files found (before filter): {len(files)}")

            # Filter only files (not directories)
            files = [f for f in files if f.is_file()]

            print(f"       - files found (after filter): {len(files)}")
            for f in files[:5]:  # Show first 5
                print(f"         * {f.name}")

            # Make paths relative to working_directory
            relative_files = [str(f.relative_to(working_dir_resolved)) for f in files]

            if not relative_files:
                return f"No files found matching pattern '{pattern}' in '{directory}' (searched: {full_path})"

            return "\n".join(sorted(relative_files))

        except Exception as e:
            import traceback

            print("    ❌ list_files exception:")
            traceback.print_exc()
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

    def edit_file(
        self,
        file_path: str,
        old_str: str,
        new_str: str,
        working_directory: str = ".",
        replace_all: bool = False,
    ) -> str:
        """Edit file by replacing old_str with new_str on local filesystem."""
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

            # Read current content
            content = full_path.read_text(encoding="utf-8")

            # Check if old_str exists
            if old_str not in content:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"String not found in file: '{old_str[:100]}...'",
                    }
                )

            # Check for multiple occurrences if not replace_all
            occurrences = content.count(old_str)
            if not replace_all and occurrences > 1:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"String appears {occurrences} times in file. "
                        f"Use replace_all=True to replace all instances, or provide a more specific string.",
                    }
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_str, new_str)
                result_msg = f"Successfully replaced {occurrences} occurrence(s) in '{file_path}'"
            else:
                new_content = content.replace(old_str, new_str, 1)
                result_msg = f"Successfully replaced 1 occurrence in '{file_path}'"

            # Write back
            full_path.write_text(new_content, encoding="utf-8")

            return json.dumps({"status": "success", "message": result_msg})

        except PermissionError:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Permission denied editing '{file_path}'",
                }
            )
        except Exception as e:
            return json.dumps(
                {"status": "error", "message": f"Error editing file: {str(e)}"}
            )

    def grep_search(
        self,
        pattern: str,
        directory: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = False,
        context_lines: int = 0,
        working_directory: str = ".",
    ) -> str:
        """Search for pattern in files using Python implementation (cross-platform)."""
        import fnmatch
        import re

        try:
            # Resolve full path
            search_path = Path(working_directory) / directory
            search_path = search_path.resolve()

            # Security check
            working_dir_resolved = Path(working_directory).resolve()
            if not str(search_path).startswith(str(working_dir_resolved)):
                return "Error: Access denied - path outside working directory"

            # Check directory exists
            if not search_path.exists():
                return f"Error: Directory '{directory}' does not exist"

            if not search_path.is_dir():
                return f"Error: '{directory}' is not a directory"

            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return f"Error: Invalid regex pattern: {str(e)}"

            # Search files
            results = []
            files_searched = 0

            # Get all files matching file_pattern
            for file_path in search_path.rglob("*"):
                if not file_path.is_file():
                    continue

                # Check if file matches file_pattern
                if file_pattern != "*" and not fnmatch.fnmatch(
                    file_path.name, file_pattern
                ):
                    continue

                files_searched += 1

                # Search in file
                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            # Get relative path
                            rel_path = file_path.relative_to(working_dir_resolved)

                            # Format result
                            result_line = f"{rel_path}:{line_num}:{line.rstrip()}"
                            results.append((line_num, result_line))

                            # Add context lines if requested
                            if context_lines > 0:
                                # Add lines before
                                for i in range(
                                    max(0, line_num - context_lines - 1), line_num - 1
                                ):
                                    ctx_line = f"{rel_path}:{i + 1}:{lines[i].rstrip()}"
                                    results.append((i + 1, ctx_line))

                                # Add lines after
                                for i in range(
                                    line_num, min(len(lines), line_num + context_lines)
                                ):
                                    ctx_line = f"{rel_path}:{i + 1}:{lines[i].rstrip()}"
                                    results.append((i + 1, ctx_line))

                except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read
                    continue

            if not results:
                return f"No matches found for pattern '{pattern}' (searched {files_searched} files)"

            # Sort and deduplicate results
            unique_results = []
            seen = set()
            for _, result in sorted(results):
                if result not in seen:
                    unique_results.append(result)
                    seen.add(result)

            return "\n".join(unique_results)

        except Exception as e:
            return f"Error executing search: {str(e)}"

    def execute_command(
        self,
        command: str,
        working_directory: str = ".",
        timeout: int = 60,
        capture_output: bool = True,
    ) -> str:
        """
        Execute shell command in working directory.

        Security checks:
        - Blocks dangerous commands (rm -rf /, sudo, etc.)
        - Validates working directory is within allowed paths
        - Enforces timeout to prevent hanging

        Args:
            command: Shell command to execute
            working_directory: Base directory for command execution
            timeout: Command timeout in seconds (default: 60)
            capture_output: Whether to capture stdout/stderr (default: True)

        Returns:
            JSON string with execution results
        """
        import subprocess
        import time

        try:
            # Security check: Block dangerous commands
            dangerous_patterns = [
                "rm -rf /",
                "rm -rf /*",
                "sudo",
                "su ",
                "chmod 777",
                "mkfs",
                "dd if=",
                "> /dev/",
                "curl | sh",
                "wget | sh",
                "eval",
                "exec",
            ]

            command_lower = command.lower().strip()
            for pattern in dangerous_patterns:
                if pattern in command_lower:
                    return json.dumps(
                        {
                            "status": "error",
                            "exit_code": -1,
                            "stdout": "",
                            "stderr": f"Security: Dangerous command blocked: '{pattern}'",
                            "execution_time": 0.0,
                        }
                    )

            # Resolve working directory
            working_dir_resolved = Path(working_directory).resolve()
            if not working_dir_resolved.exists():
                return json.dumps(
                    {
                        "status": "error",
                        "exit_code": -1,
                        "stdout": "",
                        "stderr": f"Working directory does not exist: {working_directory}",
                        "execution_time": 0.0,
                    }
                )

            # Execute command
            start_time = time.time()

            result = subprocess.run(
                command,
                shell=True,
                cwd=str(working_dir_resolved),
                capture_output=capture_output,
                text=True,
                timeout=timeout,
            )

            execution_time = time.time() - start_time

            # Return results
            return json.dumps(
                {
                    "status": "success" if result.returncode == 0 else "error",
                    "exit_code": result.returncode,
                    "stdout": result.stdout if capture_output else "",
                    "stderr": result.stderr if capture_output else "",
                    "execution_time": round(execution_time, 2),
                }
            )

        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "status": "error",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds",
                    "execution_time": timeout,
                }
            )
        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Error executing command: {str(e)}",
                    "execution_time": 0.0,
                }
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

    def edit_file(
        self,
        file_path: str,
        old_str: str,
        new_str: str,
        working_directory: str = ".",
        replace_all: bool = False,
    ) -> str:
        """Edit file by replacing old_str with new_str in Daytona sandbox."""
        try:
            # Resolve to sandbox path
            sandbox_path = self._resolve_sandbox_path(file_path, working_directory)

            # Download current content from sandbox
            content = self.sandbox.fs.download_file(sandbox_path)

            # Check if old_str exists
            if old_str not in content:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"String not found in file: '{old_str[:100]}...'",
                    }
                )

            # Check for multiple occurrences if not replace_all
            occurrences = content.count(old_str)
            if not replace_all and occurrences > 1:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"String appears {occurrences} times in file. "
                        f"Use replace_all=True to replace all instances, or provide a more specific string.",
                    }
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_str, new_str)
                result_msg = f"Successfully replaced {occurrences} occurrence(s) in '{file_path}'"
            else:
                new_content = content.replace(old_str, new_str, 1)
                result_msg = f"Successfully replaced 1 occurrence in '{file_path}'"

            # Upload modified content back to sandbox
            self.sandbox.fs.upload_file(new_content, sandbox_path)

            return json.dumps({"status": "success", "message": result_msg})

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Error editing file in sandbox: {str(e)}",
                }
            )

    def grep_search(
        self,
        pattern: str,
        directory: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = False,
        context_lines: int = 0,
        working_directory: str = ".",
    ) -> str:
        """Search for pattern in files using Daytona sandbox process execution."""
        try:
            # Resolve to sandbox path
            sandbox_path = self._resolve_sandbox_path(directory, working_directory)

            # Build grep command for sandbox execution
            # Try ripgrep first, fallback to grep
            rg_cmd = f"rg '{pattern}' {sandbox_path} -n --color=never"

            if not case_sensitive:
                rg_cmd += " -i"

            if context_lines > 0:
                rg_cmd += f" -C {context_lines}"

            if file_pattern != "*":
                rg_cmd += f" -g '{file_pattern}'"

            # Execute command in sandbox
            try:
                # Try ripgrep first
                result = self.sandbox.process.execute_command(rg_cmd)

                # Check if command succeeded
                if result.get("exit_code") == 0:
                    return result.get("stdout", "")
                elif result.get("exit_code") == 1:
                    return f"No matches found for pattern '{pattern}'"
                else:
                    # Ripgrep not available, try grep
                    grep_cmd = "grep -rn"

                    if not case_sensitive:
                        grep_cmd += " -i"

                    if context_lines > 0:
                        grep_cmd += f" -C {context_lines}"

                    grep_cmd += f" '{pattern}' {sandbox_path}"

                    if file_pattern != "*":
                        grep_cmd += f" --include='{file_pattern}'"

                    result = self.sandbox.process.execute_command(grep_cmd)

                    if result.get("exit_code") == 0:
                        return result.get("stdout", "")
                    elif result.get("exit_code") == 1:
                        return f"No matches found for pattern '{pattern}'"
                    else:
                        return f"Error: {result.get('stderr', 'Unknown error')}"

            except Exception as e:
                return f"Error executing search in sandbox: {str(e)}"

        except Exception as e:
            return f"Error searching in sandbox: {str(e)}"

    def execute_command(
        self,
        command: str,
        working_directory: str = ".",
        timeout: int = 60,
        capture_output: bool = True,
    ) -> str:
        """
        Execute shell command in Daytona sandbox.

        Uses sandbox.process.exec() to run commands in the sandbox environment.

        Args:
            command: Shell command to execute
            working_directory: Base directory for command execution
            timeout: Command timeout in seconds (default: 60)
            capture_output: Whether to capture stdout/stderr (default: True)

        Returns:
            JSON string with execution results
        """
        import time

        try:
            # Security check: Block dangerous commands
            dangerous_patterns = [
                "rm -rf /",
                "rm -rf /*",
                "sudo",
                "su ",
                "chmod 777",
                "mkfs",
                "dd if=",
                "> /dev/",
                "curl | sh",
                "wget | sh",
                "eval",
                "exec",
            ]

            command_lower = command.lower().strip()
            for pattern in dangerous_patterns:
                if pattern in command_lower:
                    return json.dumps(
                        {
                            "status": "error",
                            "exit_code": -1,
                            "stdout": "",
                            "stderr": f"Security: Dangerous command blocked: '{pattern}'",
                            "execution_time": 0.0,
                        }
                    )

            # Execute command in sandbox
            start_time = time.time()

            # Use sandbox.process.exec() to run command
            result = self.sandbox.process.exec(
                cmd=command,
                cwd=working_directory,
                timeout=timeout,
            )

            execution_time = time.time() - start_time

            # Parse result from Daytona API
            # Daytona returns: {"exit_code": int, "stdout": str, "stderr": str}
            exit_code = result.get("exit_code", -1)
            stdout = result.get("stdout", "") if capture_output else ""
            stderr = result.get("stderr", "") if capture_output else ""

            return json.dumps(
                {
                    "status": "success" if exit_code == 0 else "error",
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_time": round(execution_time, 2),
                }
            )

        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Error executing command in sandbox: {str(e)}",
                    "execution_time": 0.0,
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
