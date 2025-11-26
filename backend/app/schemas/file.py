"""File operation schemas."""

from uuid import UUID
from pydantic import BaseModel
from typing import Optional


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
    content: str
    encoding: str = "utf-8"
    size: int


class GitStatusResponse(BaseModel):
    project_id: UUID
    branch: str
    modified: list[str]
    untracked: list[str]
    staged: list[str]
