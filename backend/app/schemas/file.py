"""File operation schemas (from routes/files.py)."""

from uuid import UUID
from pydantic import BaseModel
from typing import Optional


class FileNode(BaseModel):
    """Single file or folder node"""
    name: str
    type: str  # "file" or "folder"
    path: str  # Relative path from project root
    size: Optional[int] = None  # Size in bytes (for files)
    modified: Optional[str] = None  # Last modified timestamp
    children: Optional[list["FileNode"]] = None  # Only for folders


class FileTreeResponse(BaseModel):
    """Response containing the file tree"""
    project_id: UUID
    root: FileNode


class FileContentResponse(BaseModel):
    """Response containing file content"""
    path: str
    content: str
    encoding: str = "utf-8"
    size: int


class GitStatusResponse(BaseModel):
    """Response containing git status of files"""
    project_id: UUID
    branch: str
    modified: list[str]
    untracked: list[str]
    staged: list[str]
