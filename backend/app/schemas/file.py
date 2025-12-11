"""File operation schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class FileNode(BaseModel):
    name: str
    type: str
    path: str
    size: Optional[int] = None
    modified: Optional[str] = None
    children: Optional[list["FileNode"]] = None


class FileTreeResponse(BaseModel):
    project_id: UUID
    root: FileNode


class FileContentResponse(BaseModel):
    path: str
    name: str = ""
    content: str
    encoding: str = "utf-8"
    size: int
    modified: str = ""
    is_binary: bool = False


class GitStatusResponse(BaseModel):
    project_id: UUID
    is_git_repo: bool = True
    branch: str = ""
    files: dict[str, str] = {}
    modified: list[str] = []
    untracked: list[str] = []
    staged: list[str] = []
