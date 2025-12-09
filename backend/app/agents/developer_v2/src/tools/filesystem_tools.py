"""File System Tools using LangChain @tool decorator."""

import os
import re
import glob as glob_module
from pathlib import Path
from langchain_core.tools import tool

from app.agents.developer_v2.src.utils.llm_utils import file_cache
from ._base_context import get_root_dir, is_safe_path

_modified_files: set = set()
_files_read_session: set = set()


def get_modified_files() -> list:
    return list(_modified_files)


def reset_modified_files():
    _modified_files.clear()
    _files_read_session.clear()


def _track_modified(file_path: str):
    _modified_files.add(file_path)


def _track_read(file_path: str):
    _files_read_session.add(file_path)


@tool
def read_file_safe(file_path: str) -> str:
    """Read contents of a file safely within the project root."""
    if not file_path or not file_path.strip():
        return "Error: file_path cannot be empty"
    
    root_dir = get_root_dir()
    full_path = os.path.join(root_dir, file_path)
    
    if not is_safe_path(full_path, root_dir):
        return f"Error: Access denied. Path outside root: {file_path}"
    
    cached = file_cache.get(full_path)
    if cached is not None:
        _track_read(file_path)
        return f"Content of {file_path}:\n\n{cached}"
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        file_cache.set(full_path, content)
        _track_read(file_path)
        return f"Content of {file_path}:\n\n{content}"
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def list_directory_safe(dir_path: str = ".") -> str:
    """List all files and directories in a given path."""
    root_dir = get_root_dir()
    full_path = os.path.join(root_dir, dir_path)
    
    if not is_safe_path(full_path, root_dir):
        return f"Error: Access denied. Path outside root: {dir_path}"
    
    try:
        items = os.listdir(full_path)
        files, dirs = [], []
        ignored = {'.next', '.git', '__pycache__', 'node_modules'}
        
        for item in items:
            if item in ignored:
                continue
            item_path = os.path.join(full_path, item)
            if os.path.isdir(item_path):
                dirs.append(f"{item}/")
            else:
                files.append(f"{item} ({os.path.getsize(item_path)} bytes)")
        
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
def glob(pattern: str, path: str = ".") -> str:
    """Search for files matching a glob pattern."""
    root_dir = get_root_dir()
    search_path = os.path.join(root_dir, path, pattern)
    
    try:
        matches = []
        for file_path in glob_module.glob(search_path, recursive=True):
            if is_safe_path(file_path, root_dir):
                matches.append(os.path.relpath(file_path, root_dir))
        
        if matches:
            return f"Found {len(matches)} file(s) matching '{pattern}':\n" + "\n".join(matches)
        return f"No files found matching pattern: {pattern}"
    except Exception as e:
        return f"Error searching files: {str(e)}"


@tool
def grep_files(pattern: str, path: str = ".", file_pattern: str = "*") -> str:
    """Search for text pattern inside files."""
    root_dir = get_root_dir()
    search_path = Path(os.path.join(root_dir, path))
    results = []
    
    try:
        for file_path in search_path.rglob(file_pattern):
            if file_path.is_file() and is_safe_path(str(file_path), root_dir):
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    for i, line in enumerate(content.splitlines(), 1):
                        if re.search(pattern, line):
                            rel_path = file_path.relative_to(root_dir)
                            results.append(f"{rel_path}:{i}: {line.strip()}")
                except:
                    pass
        
        if not results:
            return f"No matches for '{pattern}'"
        return "\n".join(results[:50])
    except Exception as e:
        return f"Error searching: {str(e)}"
