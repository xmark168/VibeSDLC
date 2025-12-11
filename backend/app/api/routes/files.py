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


@router.get("/", response_model=FileTreeResponse)
def list_project_files(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    depth: int = Query(default=3, ge=1, le=10, description="Maximum depth to traverse"),
    worktree: str = Query(default=None, description="Worktree path to view (optional)"),
) -> FileTreeResponse:
    """
    Get file tree for a project.

    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user
        depth: Maximum depth to traverse (default 3)
        worktree: Optional worktree path to view instead of main project

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

    # Get project path - use worktree path if provided
    if worktree:
        project_folder = Path(worktree)
        project_path = worktree  # Set project_path for response
        # Verify worktree belongs to this project (security check)
        project_base = Path(project.project_path or f"projects/{project_id}")
        try:
            # Worktree should be in same parent directory or subdirectory
            if not (project_folder.exists() and project_folder.is_dir()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid worktree path",
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid worktree path",
            )
    else:
        project_path = project.project_path
        if not project_path:
            project_path = f"projects/{project_id}"
            project.project_path = project_path
            session.commit()
        project_folder = Path(project_path)

    # Ensure project folder exists
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
    worktree: str = Query(default=None, description="Worktree path to use instead of main project"),
) -> FileContentResponse:
    """
    Get content of a specific file.

    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user
        path: Relative path to the file
        worktree: Optional worktree path to use instead of main project

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

    # Build full path - use worktree if provided
    if worktree:
        base_path = worktree
    else:
        base_path = project.project_path or f"projects/{project_id}"
    full_path = Path(base_path) / path

    # Security check: ensure path is within base folder
    try:
        full_path = full_path.resolve()
        base_folder = Path(base_path).resolve()
        if not str(full_path).startswith(str(base_folder)):
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

    # Check if file is binary by extension
    BINARY_EXTENSIONS = {
        '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',  # Office
        '.pdf',  # PDF
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.svg',  # Images
        '.zip', '.rar', '.7z', '.tar', '.gz',  # Archives
        '.exe', '.dll', '.so', '.dylib',  # Binaries
        '.mp3', '.mp4', '.wav', '.avi', '.mov',  # Media
        '.woff', '.woff2', '.ttf', '.eot',  # Fonts
    }
    
    file_ext = full_path.suffix.lower()
    if file_ext in BINARY_EXTENSIONS:
        # Return placeholder for binary files
        stat = full_path.stat()
        return FileContentResponse(
            path=path,
            name=full_path.name,
            content=f"[Binary file: {file_ext}]\n\nThis file type cannot be previewed as text.\nFile size: {stat.st_size:,} bytes",
            size=stat.st_size,
            modified=str(stat.st_mtime),
            is_binary=True,
        )
    
    # Read file content
    try:
        content = full_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary file - return placeholder
        stat = full_path.stat()
        return FileContentResponse(
            path=path,
            name=full_path.name,
            content=f"[Binary file]\n\nThis file cannot be displayed as text.\nFile size: {stat.st_size:,} bytes",
            size=stat.st_size,
            modified=str(stat.st_mtime),
            is_binary=True,
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


@router.get("/download")
def download_file(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    path: str = Query(..., description="Relative path to the file"),
):
    """
    Download a file from the project.
    
    Args:
        project_id: UUID of the project
        session: Database session
        current_user: Current authenticated user
        path: Relative path to the file
        
    Returns:
        The file as a download response
    """
    from fastapi.responses import FileResponse
    
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

    # Determine MIME type
    ext = full_path.suffix.lower()
    mime_types = {
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.pdf': 'application/pdf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.zip': 'application/zip',
    }
    media_type = mime_types.get(ext, 'application/octet-stream')
    
    logger.info(f"Download file: {full_path} ({full_path.stat().st_size} bytes, {media_type})")

    return FileResponse(
        path=full_path,
        filename=full_path.name,
        media_type=media_type,
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
            branch="",
            files={},
            modified=[],
            untracked=[],
            staged=[],
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


@router.get("/branches")
def get_branches(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """
    Get branches and worktrees for project repository.
    
    Returns:
        current: Current active branch name in main repo
        branches: List of local branch names
        worktrees: List of worktrees with their branches and paths
    """
    from git import Repo, InvalidGitRepositoryError
    import subprocess
    
    project_service = ProjectService(session)
    project = project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    if current_user.role != Role.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    project_path = project.project_path or f"projects/{project_id}"
    project_folder = Path(project_path)
    
    if not project_folder.exists():
        return {"current": None, "branches": [], "worktrees": []}
    
    try:
        repo = Repo(project_folder)
    except InvalidGitRepositoryError:
        return {"current": None, "branches": [], "worktrees": []}
    
    # Get current branch
    try:
        current = repo.active_branch.name
    except TypeError:
        current = repo.head.commit.hexsha[:7]
    
    # Get local branches
    branches = [b.name for b in repo.branches]
    
    # Get worktrees using git command
    worktrees = []
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=project_folder,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            current_worktree = {}
            for line in result.stdout.strip().split("\n"):
                if line.startswith("worktree "):
                    if current_worktree:
                        worktrees.append(current_worktree)
                    current_worktree = {"path": line[9:]}
                elif line.startswith("HEAD "):
                    current_worktree["head"] = line[5:]
                elif line.startswith("branch "):
                    # refs/heads/branch_name -> branch_name
                    current_worktree["branch"] = line[7:].replace("refs/heads/", "")
                elif line == "bare":
                    current_worktree["bare"] = True
            if current_worktree:
                worktrees.append(current_worktree)
    except Exception as e:
        logger.warning(f"Failed to get worktrees: {e}")
    
    return {
        "current": current,
        "branches": branches,
        "worktrees": worktrees
    }


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
