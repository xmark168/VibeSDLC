"""File management endpoints for project files."""

import logging
import os
from pathlib import Path
from typing import Any, Optional, Dict
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.services import ProjectService
from app.models import Role
from app.schemas import FileNode, FileTreeResponse, FileContentResponse, GitStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/files", tags=["files"])


# ============= Endpoints =============

@router.get("/", response_model=FileTreeResponse)
def list_project_files(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    depth: int = Query(default=3, ge=1, le=10, description="Maximum depth to traverse"),
) -> FileTreeResponse:
    """
    Get file tree for a project.

    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user
        depth: Maximum depth to traverse (default 3)

    Returns:
        FileTreeResponse: File tree structure
    """
    # Get project and verify access
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    # Get project path
    project_path = project.project_path
    if not project_path:
        # Auto-generate if not exists
        project_path = f"projects/{project_id}"
        project.project_path = project_path
        session.commit()

    # Ensure project folder exists
    project_folder = Path(project_path)
    if not project_folder.exists():
        project_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created project folder: {project_folder}")

    # Build file tree
    root_node = _build_file_tree(project_folder, "", depth)

    return FileTreeResponse(
        project_id=project_id,
        project_path=project_path,
        root=root_node,
    )


@router.get("/content", response_model=FileContentResponse)
def get_file_content(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    path: str = Query(..., description="Relative path to the file"),
) -> FileContentResponse:
    """
    Get content of a specific file.

    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user
        path: Relative path to the file

    Returns:
        FileContentResponse: File content and metadata
    """
    # Get project and verify access
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    # Build full path
    project_path = project.project_path or f"projects/{project_id}"
    full_path = Path(project_path) / path

    # Security check: ensure path is within project folder
    try:
        full_path = full_path.resolve()
        project_folder = Path(project_path).resolve()
        if not str(full_path).startswith(str(project_folder)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path: path traversal not allowed",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid path: {str(e)}",
        )

    # Check if file exists
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    if not full_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a file",
        )

    # Read file content
    try:
        content = full_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary file - return base64 or error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot read binary file as text",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading file: {str(e)}",
        )

    # Get file metadata
    stat = full_path.stat()

    return FileContentResponse(
        path=path,
        name=full_path.name,
        content=content,
        size=stat.st_size,
        modified=str(stat.st_mtime),
    )


@router.get("/git-status", response_model=GitStatusResponse)
def get_git_status(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> GitStatusResponse:
    """
    Get git status for project files (modified, added, deleted, untracked).

    Uses GitPython to detect file changes similar to MetaGPT approach.

    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user

    Returns:
        GitStatusResponse: Dictionary of files with their change types
    """
    from git import Repo, InvalidGitRepositoryError

    # Get project and verify access
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    # Get project path
    project_path = project.project_path or f"projects/{project_id}"
    project_folder = Path(project_path)

    if not project_folder.exists():
        return GitStatusResponse(
            project_id=project_id,
            is_git_repo=False,
            files={},
        )

    # Try to open as git repository
    try:
        repo = Repo(project_folder)
    except InvalidGitRepositoryError:
        return GitStatusResponse(
            project_id=project_id,
            is_git_repo=False,
            files={},
        )

    # Get file changes (MetaGPT approach)
    files: Dict[str, str] = {}

    # 1. Get untracked files
    for filepath in repo.untracked_files:
        files[filepath] = "U"  # Untracked

    # 2. Get changed files (comparing index with working directory)
    try:
        for diff in repo.index.diff(None):
            # diff.a_path is the file path
            # diff.change_type is A/D/M/R/T
            files[diff.a_path] = diff.change_type
    except Exception as e:
        logger.warning(f"Error getting git diff: {e}")

    # 3. Get staged files (comparing HEAD with index)
    try:
        for diff in repo.head.commit.diff():
            if diff.a_path not in files:
                files[diff.a_path] = f"S:{diff.change_type}"  # Staged
    except Exception as e:
        # Might fail if no commits yet
        logger.debug(f"Error getting staged files: {e}")

    return GitStatusResponse(
        project_id=project_id,
        is_git_repo=True,
        files=files,
    )


# ============= Helper Functions =============

def _build_file_tree(folder: Path, relative_path: str, max_depth: int) -> FileNode:
    """
    Recursively build file tree structure.

    Args:
        folder: Path to the folder
        relative_path: Relative path from project root
        max_depth: Maximum depth to traverse

    Returns:
        FileNode: Tree structure
    """
    if max_depth <= 0:
        return FileNode(
            name=folder.name or "root",
            type="folder",
            path=relative_path or "/",
            children=[],
        )

    children = []

    try:
        # Sort: folders first, then files, alphabetically
        items = sorted(folder.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))

        for item in items:
            item_relative_path = f"{relative_path}/{item.name}" if relative_path else item.name

            if item.is_dir():
                # Skip hidden folders and common ignored directories
                if item.name.startswith(".") or item.name in ["node_modules", "__pycache__", ".git", ".venv", "venv"]:
                    continue

                child_node = _build_file_tree(item, item_relative_path, max_depth - 1)
                children.append(child_node)
            else:
                # Skip hidden files
                if item.name.startswith("."):
                    continue

                stat = item.stat()
                children.append(FileNode(
                    name=item.name,
                    type="file",
                    path=item_relative_path,
                    size=stat.st_size,
                    modified=str(stat.st_mtime),
                ))
    except PermissionError:
        logger.warning(f"Permission denied accessing folder: {folder}")
    except Exception as e:
        logger.error(f"Error reading folder {folder}: {e}")

    return FileNode(
        name=folder.name or "root",
        type="folder",
        path=relative_path or "/",
        children=children,
    )
