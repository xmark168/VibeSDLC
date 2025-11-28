"""Developer V2 Tools for code operations."""

import logging
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def read_file(file_path: str) -> str:
    """Read contents of a file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        File contents as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file.
    
    Args:
        file_path: Path to the file to write
        content: Content to write
        
    Returns:
        Success message or error
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def list_directory(directory_path: str) -> str:
    """List contents of a directory.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        List of files and directories
    """
    import os
    try:
        items = os.listdir(directory_path)
        return "\n".join(items)
    except FileNotFoundError:
        return f"Error: Directory not found: {directory_path}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def search_in_files(directory: str, pattern: str, file_extension: Optional[str] = None) -> str:
    """Search for a pattern in files within a directory.
    
    Args:
        directory: Directory to search in
        pattern: Pattern to search for
        file_extension: Optional file extension filter (e.g., '.py')
        
    Returns:
        Matching files and lines
    """
    import os
    import re
    
    results = []
    try:
        for root, _, files in os.walk(directory):
            for file in files:
                if file_extension and not file.endswith(file_extension):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            if re.search(pattern, line):
                                results.append(f"{file_path}:{i}: {line.strip()}")
                except (UnicodeDecodeError, PermissionError):
                    continue
                    
        return "\n".join(results) if results else "No matches found"
    except Exception as e:
        return f"Error searching: {str(e)}"


@tool
def get_file_info(file_path: str) -> str:
    """Get information about a file (size, modified time, etc.).
    
    Args:
        file_path: Path to the file
        
    Returns:
        File information
    """
    import os
    from datetime import datetime
    
    try:
        stat = os.stat(file_path)
        return f"""File: {file_path}
Size: {stat.st_size} bytes
Modified: {datetime.fromtimestamp(stat.st_mtime).isoformat()}
Created: {datetime.fromtimestamp(stat.st_ctime).isoformat()}"""
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    except Exception as e:
        return f"Error getting file info: {str(e)}"


@tool
def run_command(command: str, cwd: Optional[str] = None) -> str:
    """Run a shell command.
    
    Args:
        command: Command to run
        cwd: Working directory (optional)
        
    Returns:
        Command output
    """
    import subprocess
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout + result.stderr
        return output if output else "Command completed with no output"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds"
    except Exception as e:
        return f"Error running command: {str(e)}"


def get_developer_tools():
    """Get all developer tools."""
    return [
        read_file,
        write_file,
        list_directory,
        search_in_files,
        get_file_info,
        run_command,
    ]
