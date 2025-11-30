"""File System Tools using LangChain @tool decorator."""

import os
import shutil
import glob as glob_module
from typing import Optional
from langchain_core.tools import tool

# Global context for workspace-scoped tools
_fs_context = {
    "root_dir": None,
}


def set_fs_context(root_dir: str = None):
    """Set global context for filesystem tools."""
    if root_dir:
        _fs_context["root_dir"] = root_dir


def _get_root_dir() -> str:
    """Get root directory from context or use cwd."""
    return _fs_context.get("root_dir") or os.getcwd()


def _is_safe_path(path: str, root_dir: str) -> bool:
    """Check if path is within root directory."""
    real_path = os.path.realpath(path)
    real_root = os.path.realpath(root_dir)
    return real_path.startswith(real_root)


@tool
def read_file_safe(file_path: str) -> str:
    """Read contents of a file safely within the project root.

    Args:
        file_path: Path to file relative to project root
    """
    if not file_path or not file_path.strip():
        return "Error: file_path cannot be empty"
    
    root_dir = _get_root_dir()
    full_path = os.path.join(root_dir, file_path)
    
    if not _is_safe_path(full_path, root_dir):
        return f"Error: Access denied. Path outside root directory: {file_path}"
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"Content of {file_path}:\n\n{content}"
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file_safe(file_path: str, content: str, mode: str = "w") -> str:
    """Write content to a file. Creates file and directories if needed.

    Args:
        file_path: Path to file relative to project root
        content: Content to write
        mode: Write mode - 'w' for overwrite, 'a' for append
    """
    if not file_path or not file_path.strip():
        return "Error: file_path cannot be empty"
    
    root_dir = _get_root_dir()
    full_path = os.path.join(root_dir, file_path)
    
    if not _is_safe_path(full_path, root_dir):
        return f"Error: Access denied. Path outside root directory: {file_path}"
    
    try:
        dir_name = os.path.dirname(full_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(full_path, mode, encoding='utf-8') as f:
            f.write(content)
        action = "Appended to" if mode == "a" else "Written to"
        return f"{action} file: {file_path} ({len(content)} characters)"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def list_directory_safe(dir_path: str = ".") -> str:
    """List all files and directories in a given path.

    Args:
        dir_path: Directory path relative to project root (default: current)
    """
    root_dir = _get_root_dir()
    full_path = os.path.join(root_dir, dir_path)
    
    if not _is_safe_path(full_path, root_dir):
        return f"Error: Access denied. Path outside root directory: {dir_path}"
    
    try:
        items = os.listdir(full_path)
        files = []
        dirs = []
        ignored_dirs = {'.next', '.git', '__pycache__', 'node_modules'}
        
        for item in items:
            if item in ignored_dirs:
                continue
            item_path = os.path.join(full_path, item)
            if os.path.isdir(item_path):
                dirs.append(f"{item}/")
            else:
                size = os.path.getsize(item_path)
                files.append(f"{item} ({size} bytes)")
        
        result = f"Contents of {dir_path}:\n\n"
        if dirs:
            result += "Directories:\n" + "\n".join(sorted(dirs)) + "\n\n"
        if files:
            result += "Files:\n" + "\n".join(sorted(files))
        
        return result if (dirs or files) else f"Directory {dir_path} is empty"
    except FileNotFoundError:
        return f"Error: Directory not found: {dir_path}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def delete_file_safe(file_path: str) -> str:
    """Delete a file safely. Use with caution!

    Args:
        file_path: Path to file relative to project root
    """
    root_dir = _get_root_dir()
    full_path = os.path.join(root_dir, file_path)
    
    if not _is_safe_path(full_path, root_dir):
        return f"Error: Access denied. Path outside root directory: {file_path}"
    
    try:
        if not os.path.exists(full_path):
            return f"Error: File not found: {file_path}"
        os.remove(full_path)
        return f"Successfully deleted: {file_path}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


@tool
def copy_file_safe(source_path: str, destination_path: str) -> str:
    """Copy a file from source to destination.

    Args:
        source_path: Source file path relative to project root
        destination_path: Destination file path relative to project root
    """
    root_dir = _get_root_dir()
    full_source = os.path.join(root_dir, source_path)
    full_dest = os.path.join(root_dir, destination_path)
    
    if not _is_safe_path(full_source, root_dir) or not _is_safe_path(full_dest, root_dir):
        return "Error: Access denied. Paths outside root directory"
    
    try:
        if not os.path.exists(full_source):
            return f"Error: Source file not found: {source_path}"
        os.makedirs(os.path.dirname(full_dest), exist_ok=True)
        shutil.copy2(full_source, full_dest)
        return f"Successfully copied {source_path} to {destination_path}"
    except Exception as e:
        return f"Error copying file: {str(e)}"


@tool
def move_file_safe(source_path: str, destination_path: str) -> str:
    """Move or rename a file.

    Args:
        source_path: Source file path relative to project root
        destination_path: New file path relative to project root
    """
    root_dir = _get_root_dir()
    full_source = os.path.join(root_dir, source_path)
    full_dest = os.path.join(root_dir, destination_path)
    
    if not _is_safe_path(full_source, root_dir) or not _is_safe_path(full_dest, root_dir):
        return "Error: Access denied. Paths outside root directory"
    
    try:
        if not os.path.exists(full_source):
            return f"Error: Source file not found: {source_path}"
        os.makedirs(os.path.dirname(full_dest), exist_ok=True)
        shutil.move(full_source, full_dest)
        return f"Successfully moved {source_path} to {destination_path}"
    except Exception as e:
        return f"Error moving file: {str(e)}"


@tool
def search_files(pattern: str, path: str = ".") -> str:
    """Search for files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g., '*.py', 'test_*.txt', '**/*.tsx')
        path: Directory to search in relative to project root
    """
    root_dir = _get_root_dir()
    search_path = os.path.join(root_dir, path, pattern)
    
    try:
        matches = []
        for file_path in glob_module.glob(search_path, recursive=True):
            if _is_safe_path(file_path, root_dir):
                rel_path = os.path.relpath(file_path, root_dir)
                matches.append(rel_path)
        
        if matches:
            return f"Found {len(matches)} file(s) matching '{pattern}':\n" + "\n".join(matches)
        return f"No files found matching pattern: {pattern}"
    except Exception as e:
        return f"Error searching files: {str(e)}"


@tool
def edit_file(file_path: str, old_str: str, new_str: str, replace_all: bool = False) -> str:
    """Edit file by replacing old_str with new_str. Useful for incremental code changes.

    Args:
        file_path: Path to file relative to project root
        old_str: Exact string to find and replace
        new_str: New string to replace with
        replace_all: If True, replace all occurrences; if False, replace only first
    """
    root_dir = _get_root_dir()
    full_path = os.path.join(root_dir, file_path)
    
    if not _is_safe_path(full_path, root_dir):
        return f"Error: Access denied. Path outside root directory: {file_path}"
    
    try:
        if not os.path.exists(full_path):
            return f"Error: File not found: {file_path}"
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_str not in content:
            return f"Error: String not found in file: '{old_str[:100]}...'"
        
        occurrences = content.count(old_str)
        if not replace_all and occurrences > 1:
            return (f"Error: String appears {occurrences} times. "
                   f"Use replace_all=True or provide more specific string.")
        
        if replace_all:
            new_content = content.replace(old_str, new_str)
            result_msg = f"Replaced {occurrences} occurrence(s) in '{file_path}'"
        else:
            new_content = content.replace(old_str, new_str, 1)
            result_msg = f"Replaced 1 occurrence in '{file_path}'"
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return result_msg
    except PermissionError:
        return f"Error: Permission denied editing '{file_path}'"
    except Exception as e:
        return f"Error editing file: {str(e)}"
