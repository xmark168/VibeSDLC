# File: src/my_project/tools/filesystem_tools.py

"""
File System Tools cho CrewAI sử dụng LangChain FileManagementToolkit
"""

from langchain_community.agent_toolkits import FileManagementToolkit
from crewai.tools import BaseTool
from typing import Type, List
from pydantic import BaseModel, Field
import os


class FileSystemToolkit:
    """
    Wrapper cho LangChain FileManagementToolkit để sử dụng với CrewAI
    """
    
    def __init__(self, root_dir: str = None):
        """
        Initialize File System Toolkit
        
        Args:
            root_dir: Root directory để limit operations. 
                     Nếu None, sẽ dùng current working directory (KHÔNG KHUYẾN KHÍCH)
        """
        if root_dir is None:
            root_dir = os.getcwd()
            print(f"⚠️  Warning: Using current directory as root: {root_dir}")
            print("   It's recommended to specify a root_dir for security!")
        
        self.root_dir = root_dir
        self.toolkit = FileManagementToolkit(root_dir=root_dir)
        
    def get_tools(self) -> List:
        """
        Get all file management tools from LangChain
        
        Returns list of tools:
        - CopyFileTool: Copy files
        - DeleteFileTool: Delete files
        - FileSearchTool: Search for files
        - MoveFileTool: Move/rename files
        - ReadFileTool: Read file contents
        - WriteFileTool: Write to files
        - ListDirectoryTool: List directory contents
        """
        return self.toolkit.get_tools()


# Wrapper riêng cho từng tool nếu muốn customize

class FileReadInput(BaseModel):
    """Input for reading files"""
    file_path: str = Field(..., description="Path to file to read")


class FileWriteInput(BaseModel):
    """Input for writing files"""
    file_path: str = Field(..., description="Path to file to write")
    content: str = Field(..., description="Content to write to file")
    mode: str = Field(default="w", description="Write mode: 'w' (overwrite) or 'a' (append)")


class FileCopyInput(BaseModel):
    """Input for copying files"""
    source_path: str = Field(..., description="Source file path")
    destination_path: str = Field(..., description="Destination file path")


class FileMoveInput(BaseModel):
    """Input for moving/renaming files"""
    source_path: str = Field(..., description="Source file path")
    destination_path: str = Field(..., description="New file path")


class FileDeleteInput(BaseModel):
    """Input for deleting files"""
    file_path: str = Field(..., description="Path to file to delete")


class DirectoryListInput(BaseModel):
    """Input for listing directory"""
    dir_path: str = Field(default=".", description="Directory path to list")


class FileSearchInput(BaseModel):
    """Input for searching files"""
    pattern: str = Field(..., description="Search pattern (glob pattern like '*.py')")
    path: str = Field(default=".", description="Directory to search in")


class FileEditInput(BaseModel):
    """Input for editing files incrementally"""
    file_path: str = Field(..., description="Path to file to edit")
    old_str: str = Field(..., description="Exact string to find and replace in the file")
    new_str: str = Field(..., description="New string to replace the old string with")
    replace_all: bool = Field(default=False, description="Replace all occurrences (True) or just the first one (False)")


# Custom CrewAI-compatible File Tools

class SafeFileReadTool(BaseTool):
    name: str = "read_file_tool"
    description: str = "Read contents of a file. Provide the file path relative to project root."
    args_schema: Type[BaseModel] = FileReadInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for file operations")

    def __init__(self, root_dir: str = None, **kwargs):
        if root_dir is None:
            root_dir = os.getcwd()
        super().__init__(root_dir=root_dir, **kwargs)

    def _run(self, file_path: str) -> str:
        try:
            full_path = os.path.join(self.root_dir, file_path)
            
            # Security check
            real_path = os.path.realpath(full_path)
            real_root = os.path.realpath(self.root_dir)
            if not real_path.startswith(real_root):
                return f"Error: Access denied. Path outside root directory: {file_path}"
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"Content of {file_path}:\n\n{content}"
        except FileNotFoundError:
            return f"Error: File not found: {file_path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"


class SafeFileWriteTool(BaseTool):
    name: str = "file_write_tool"
    description: str = "Write content to a file. Creates file if doesn't exist. Use mode='a' to append."
    args_schema: Type[BaseModel] = FileWriteInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for file operations")

    def __init__(self, root_dir: str = None, **kwargs):
        if root_dir is None:
            root_dir = os.getcwd()
        super().__init__(root_dir=root_dir, **kwargs)

    def _run(self, file_path: str, content: str, mode: str = "w") -> str:
        try:
            full_path = os.path.join(self.root_dir, file_path)
            
            # Security check
            real_path = os.path.realpath(full_path)
            real_root = os.path.realpath(self.root_dir)
            if not real_path.startswith(real_root):
                return f"Error: Access denied. Path outside root directory: {file_path}"
            
            # Create directory if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, mode, encoding='utf-8') as f:
                f.write(content)
            
            action = "Appended to" if mode == "a" else "Written to"
            return f"{action} file: {file_path} ({len(content)} characters)"
        except Exception as e:
            return f"Error writing file: {str(e)}"


class SafeFileListTool(BaseTool):
    name: str = "safe_file_list_tool"
    description: str = "List all files and directories in a given directory path. Only accepts a single directory path, not multiple file paths. Usage: {'dir_path': 'relative/path/to/directory'} or {'dir_path': '.'} for current directory"
    args_schema: Type[BaseModel] = DirectoryListInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for file operations")

    def __init__(self, root_dir: str = None, **kwargs):
        if root_dir is None:
            root_dir = os.getcwd()
        super().__init__(root_dir=root_dir, **kwargs)

    def _run(self, dir_path: str = ".") -> str:
        try:
            full_path = os.path.join(self.root_dir, dir_path)

            # Security check
            real_path = os.path.realpath(full_path)
            real_root = os.path.realpath(self.root_dir)
            if not real_path.startswith(real_root):
                return f"Error: Access denied. Path outside root directory: {dir_path}"

            items = os.listdir(full_path)

            files = []
            dirs = []
            ignored_dirs = {'.next', '.git', '__pycache__'}

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


class SafeFileDeleteTool(BaseTool):
    name: str = "file_delete_tool"
    description: str = "Delete a file. Use with caution!"
    args_schema: Type[BaseModel] = FileDeleteInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for file operations")

    def __init__(self, root_dir: str = None, **kwargs):
        if root_dir is None:
            root_dir = os.getcwd()
        super().__init__(root_dir=root_dir, **kwargs)

    def _run(self, file_path: str) -> str:
        try:
            full_path = os.path.join(self.root_dir, file_path)
            
            # Security check
            real_path = os.path.realpath(full_path)
            real_root = os.path.realpath(self.root_dir)
            if not real_path.startswith(real_root):
                return f"Error: Access denied. Path outside root directory: {file_path}"
            
            if not os.path.exists(full_path):
                return f"Error: File not found: {file_path}"
            
            os.remove(full_path)
            return f"Successfully deleted: {file_path}"
            
        except Exception as e:
            return f"Error deleting file: {str(e)}"


class SafeFileCopyTool(BaseTool):
    name: str = "Copy File"
    description: str = "Copy a file from source to destination"
    args_schema: Type[BaseModel] = FileCopyInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for file operations")

    def __init__(self, root_dir: str = None, **kwargs):
        if root_dir is None:
            root_dir = os.getcwd()
        super().__init__(root_dir=root_dir, **kwargs)

    def _run(self, source_path: str, destination_path: str) -> str:
        try:
            import shutil
            
            full_source = os.path.join(self.root_dir, source_path)
            full_dest = os.path.join(self.root_dir, destination_path)
            
            # Security checks
            real_source = os.path.realpath(full_source)
            real_dest = os.path.realpath(full_dest)
            real_root = os.path.realpath(self.root_dir)
            
            if not real_source.startswith(real_root) or not real_dest.startswith(real_root):
                return "Error: Access denied. Paths outside root directory"
            
            if not os.path.exists(full_source):
                return f"Error: Source file not found: {source_path}"
            
            # Create destination directory if needed
            os.makedirs(os.path.dirname(full_dest), exist_ok=True)
            
            shutil.copy2(full_source, full_dest)
            return f"Successfully copied {source_path} to {destination_path}"
            
        except Exception as e:
            return f"Error copying file: {str(e)}"


class SafeFileMoveTool(BaseTool):
    name: str = "Move/Rename File"
    description: str = "Move or rename a file"
    args_schema: Type[BaseModel] = FileMoveInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for file operations")

    def __init__(self, root_dir: str = None, **kwargs):
        if root_dir is None:
            root_dir = os.getcwd()
        super().__init__(root_dir=root_dir, **kwargs)

    def _run(self, source_path: str, destination_path: str) -> str:
        try:
            import shutil
            
            full_source = os.path.join(self.root_dir, source_path)
            full_dest = os.path.join(self.root_dir, destination_path)
            
            # Security checks
            real_source = os.path.realpath(full_source)
            real_dest = os.path.realpath(full_dest)
            real_root = os.path.realpath(self.root_dir)
            
            if not real_source.startswith(real_root) or not real_dest.startswith(real_root):
                return "Error: Access denied. Paths outside root directory"
            
            if not os.path.exists(full_source):
                return f"Error: Source file not found: {source_path}"
            
            # Create destination directory if needed
            os.makedirs(os.path.dirname(full_dest), exist_ok=True)
            
            shutil.move(full_source, full_dest)
            return f"Successfully moved {source_path} to {destination_path}"
            
        except Exception as e:
            return f"Error moving file: {str(e)}"


class FileSearchTool(BaseTool):
    name: str = "search_file_tool"
    description: str = "Search for files matching a pattern (e.g., '*.py', 'test_*.txt')"
    args_schema: Type[BaseModel] = FileSearchInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for file operations")

    def __init__(self, root_dir: str = None, **kwargs):
        if root_dir is None:
            root_dir = os.getcwd()
        super().__init__(root_dir=root_dir, **kwargs)

    def _run(self, pattern: str, path: str = ".") -> str:
        try:
            import glob
            
            search_path = os.path.join(self.root_dir, path, pattern)
            
            # Security check
            real_root = os.path.realpath(self.root_dir)
            
            matches = []
            for file_path in glob.glob(search_path, recursive=True):
                real_path = os.path.realpath(file_path)
                if real_path.startswith(real_root):
                    rel_path = os.path.relpath(file_path, self.root_dir)
                    matches.append(rel_path)
            
            if matches:
                return f"Found {len(matches)} file(s) matching '{pattern}':\n" + "\n".join(matches)
            else:
                return f"No files found matching pattern: {pattern}"
                
        except Exception as e:
            return f"Error searching files: {str(e)}"


class SafeFileEditTool(BaseTool):
    name: str = "file_edit_tool"
    description: str = "Edit file by replacing old_str with new_str. Useful for incremental code changes and for modify existed file."
    args_schema: Type[BaseModel] = FileEditInput
    root_dir: str = Field(default_factory=os.getcwd, description="Root directory for file operations")

    def __init__(self, root_dir: str = None, **kwargs):
        if root_dir is None:
            root_dir = os.getcwd()
        super().__init__(root_dir=root_dir, **kwargs)

    def _run(self, file_path: str, old_str: str, new_str: str, replace_all: bool = False) -> str:
        try:
            full_path = os.path.join(self.root_dir, file_path)
            
            # Security check
            real_path = os.path.realpath(full_path)
            real_root = os.path.realpath(self.root_dir)
            if not real_path.startswith(real_root):
                return f"Error: Access denied. Path outside root directory: {file_path}"
            
            # Check file exists
            if not os.path.exists(full_path):
                return f"Error: File not found: {file_path}"
            
            # Read current content
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if old_str exists
            if old_str not in content:
                return f"Error: String not found in file: '{old_str[:100]}...'"
            
            # Check for multiple occurrences if not replace_all
            occurrences = content.count(old_str)
            if not replace_all and occurrences > 1:
                return (f"Error: String appears {occurrences} times in file. "
                       f"Use replace_all=True to replace all instances, or provide a more specific string.")
            
            # Perform replacement
            if replace_all:
                new_content = content.replace(old_str, new_str)
                result_msg = f"Successfully replaced {occurrences} occurrence(s) in '{file_path}'"
            else:
                new_content = content.replace(old_str, new_str, 1)
                result_msg = f"Successfully replaced 1 occurrence in '{file_path}'"
            
            # Write back
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return result_msg
            
        except PermissionError:
            return f"Error: Permission denied editing '{file_path}'"
        except Exception as e:
            return f"Error editing file: {str(e)}"