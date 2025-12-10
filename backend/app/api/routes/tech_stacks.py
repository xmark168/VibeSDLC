"""TechStack Management API Routes"""

import os
import shutil
import logging
from pathlib import Path
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, Body, Depends, UploadFile, File as FastAPIFile
from typing import List
from sqlmodel import select, func

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import TechStack
from app.schemas.tech_stack import (
    TechStackCreate,
    TechStackUpdate,
    TechStackResponse,
    TechStacksResponse,
    FileNode,
    FileContent,
    CreateFileRequest,
    UpdateFileRequest,
    CreateFolderRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tech-stacks", tags=["tech-stacks"])

# Skills base path
SKILLS_BASE_PATH = Path(__file__).parent.parent.parent / "agents" / "developer_v2" / "src" / "skills"
# Boilerplate base path
BOILERPLATE_BASE_PATH = Path(__file__).parent.parent.parent / "agents" / "templates" / "boilerplate"
EXCLUDED_FOLDERS = {"general", "__pycache__", ".next", "node_modules", ".git"}


def get_file_tree(path: Path, base_path: Path) -> FileNode:
    """Recursively build file tree structure"""
    relative_path = str(path.relative_to(base_path)).replace("\\", "/")
    
    if path.is_file():
        return FileNode(
            name=path.name,
            type="file",
            path=relative_path,
            children=None
        )
    
    children = []
    try:
        for item in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            children.append(get_file_tree(item, base_path))
    except PermissionError:
        pass
    
    return FileNode(
        name=path.name,
        type="folder",
        path=relative_path,
        children=children
    )


# ==================== CRUD Endpoints ====================

@router.get("", response_model=TechStacksResponse)
def list_tech_stacks(
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
):
    """List all tech stacks"""
    statement = select(TechStack)
    
    if search:
        search_term = f"%{search}%"
        statement = statement.where(
            (TechStack.name.ilike(search_term)) | (TechStack.code.ilike(search_term))
        )
    
    if is_active is not None:
        statement = statement.where(TechStack.is_active == is_active)
    
    # Count
    count_statement = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_statement).one()
    
    # Fetch
    statement = statement.order_by(TechStack.display_order, TechStack.name)
    statement = statement.offset(skip).limit(limit)
    stacks = session.exec(statement).all()
    
    return TechStacksResponse(
        data=[TechStackResponse.model_validate(s) for s in stacks],
        count=total
    )


@router.get("/available-skills")
def list_available_skills():
    """List available skill folders (excluding general and __pycache__)"""
    if not SKILLS_BASE_PATH.exists():
        return {"skills": []}
    
    skills = []
    for item in SKILLS_BASE_PATH.iterdir():
        if item.is_dir() and item.name not in EXCLUDED_FOLDERS:
            skills.append(item.name)
    
    return {"skills": sorted(skills)}


@router.get("/{stack_id}", response_model=TechStackResponse)
def get_tech_stack(
    session: SessionDep,
    stack_id: UUID,
):
    """Get a tech stack by ID"""
    stack = session.get(TechStack, stack_id)
    if not stack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TechStack with ID {stack_id} not found"
        )
    return stack


@router.get("/by-code/{code}", response_model=TechStackResponse)
def get_tech_stack_by_code(
    session: SessionDep,
    code: str,
):
    """Get a tech stack by code"""
    statement = select(TechStack).where(TechStack.code == code)
    stack = session.exec(statement).first()
    if not stack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TechStack with code '{code}' not found"
        )
    return stack


@router.post("", response_model=TechStackResponse, status_code=status.HTTP_201_CREATED)
def create_tech_stack(
    session: SessionDep,
    data: TechStackCreate = Body(...),
):
    """Create a new tech stack"""
    # Check for duplicate code
    existing = session.exec(
        select(TechStack).where(TechStack.code == data.code)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"TechStack with code '{data.code}' already exists"
        )
    
    stack = TechStack(**data.model_dump())
    session.add(stack)
    session.commit()
    session.refresh(stack)
    
    # Create skill folder
    skill_folder = SKILLS_BASE_PATH / data.code
    if not skill_folder.exists():
        skill_folder.mkdir(parents=True, exist_ok=True)
        # Create __init__.py
        (skill_folder / "__init__.py").write_text("")
        logger.info(f"Created skill folder: {skill_folder}")
    
    # Create boilerplate folder
    boilerplate_folder = BOILERPLATE_BASE_PATH / f"{data.code}-boilerplate"
    if not boilerplate_folder.exists():
        boilerplate_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created boilerplate folder: {boilerplate_folder}")
    
    logger.info(f"Created tech stack: {stack.name} ({stack.code})")
    return stack


@router.put("/{stack_id}", response_model=TechStackResponse)
def update_tech_stack(
    stack_id: UUID,
    session: SessionDep,
    data: TechStackUpdate = Body(...),
):
    """Update a tech stack"""
    stack = session.get(TechStack, stack_id)
    if not stack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TechStack with ID {stack_id} not found"
        )
    
    # Check for duplicate code if code is being changed
    if data.code and data.code != stack.code:
        existing = session.exec(
            select(TechStack).where(TechStack.code == data.code)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"TechStack with code '{data.code}' already exists"
            )
        
        # Rename skill folder
        old_folder = SKILLS_BASE_PATH / stack.code
        new_folder = SKILLS_BASE_PATH / data.code
        if old_folder.exists() and not new_folder.exists():
            old_folder.rename(new_folder)
            logger.info(f"Renamed skill folder: {old_folder} -> {new_folder}")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(stack, key, value)
    
    session.add(stack)
    session.commit()
    session.refresh(stack)
    
    logger.info(f"Updated tech stack: {stack.name} ({stack.id})")
    return stack


@router.delete("/{stack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tech_stack(
    stack_id: UUID,
    session: SessionDep,
    delete_files: bool = Query(False, description="Also delete skill folder"),
):
    """Delete a tech stack"""
    stack = session.get(TechStack, stack_id)
    if not stack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TechStack with ID {stack_id} not found"
        )
    
    code = stack.code
    session.delete(stack)
    session.commit()
    
    # Optionally delete skill folder
    if delete_files:
        skill_folder = SKILLS_BASE_PATH / code
        if skill_folder.exists():
            shutil.rmtree(skill_folder)
            logger.info(f"Deleted skill folder: {skill_folder}")
    
    logger.info(f"Deleted tech stack: {code}")


# ==================== Skill File Management ====================

@router.get("/{code}/skills/tree")
def get_skill_tree(code: str):
    """Get file tree for a skill folder"""
    skill_folder = SKILLS_BASE_PATH / code
    
    if not skill_folder.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill folder '{code}' not found"
        )
    
    tree = get_file_tree(skill_folder, skill_folder)
    return tree


@router.get("/{code}/skills/file")
def read_skill_file(
    code: str,
    path: str = Query(..., description="Relative file path"),
):
    """Read content of a skill file"""
    skill_folder = SKILLS_BASE_PATH / code
    file_path = skill_folder / path
    
    # Security check - ensure path is within skill folder
    try:
        file_path.resolve().relative_to(skill_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {path}"
        )
    
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a file: {path}"
        )
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1")
    
    return FileContent(path=path, content=content)


@router.post("/{code}/skills/file", status_code=status.HTTP_201_CREATED)
def create_skill_file(
    code: str,
    data: CreateFileRequest = Body(...),
):
    """Create a new skill file"""
    skill_folder = SKILLS_BASE_PATH / code
    file_path = skill_folder / data.path
    
    # Security check
    try:
        file_path.resolve().relative_to(skill_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    if file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File already exists: {data.path}"
        )
    
    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(data.content, encoding="utf-8")
    
    logger.info(f"Created skill file: {file_path}")
    return {"message": "File created", "path": data.path}


@router.put("/{code}/skills/file")
def update_skill_file(
    code: str,
    data: UpdateFileRequest = Body(...),
):
    """Update content of a skill file"""
    skill_folder = SKILLS_BASE_PATH / code
    file_path = skill_folder / data.path
    
    # Security check
    try:
        file_path.resolve().relative_to(skill_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {data.path}"
        )
    
    file_path.write_text(data.content, encoding="utf-8")
    
    logger.info(f"Updated skill file: {file_path}")
    return {"message": "File updated", "path": data.path}


@router.delete("/{code}/skills/file")
def delete_skill_file(
    code: str,
    path: str = Query(..., description="Relative file path"),
):
    """Delete a skill file"""
    skill_folder = SKILLS_BASE_PATH / code
    file_path = skill_folder / path
    
    # Security check
    try:
        file_path.resolve().relative_to(skill_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {path}"
        )
    
    if file_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use folder endpoint to delete folders"
        )
    
    file_path.unlink()
    
    logger.info(f"Deleted skill file: {file_path}")
    return {"message": "File deleted", "path": path}


@router.post("/{code}/skills/folder", status_code=status.HTTP_201_CREATED)
def create_skill_folder(
    code: str,
    data: CreateFolderRequest = Body(...),
):
    """Create a new skill folder"""
    skill_folder = SKILLS_BASE_PATH / code
    folder_path = skill_folder / data.path
    
    # Security check
    try:
        folder_path.resolve().relative_to(skill_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder path"
        )
    
    if folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Folder already exists: {data.path}"
        )
    
    folder_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created skill folder: {folder_path}")
    return {"message": "Folder created", "path": data.path}


@router.delete("/{code}/skills/folder")
def delete_skill_folder(
    code: str,
    path: str = Query(..., description="Relative folder path"),
):
    """Delete a skill folder"""
    skill_folder = SKILLS_BASE_PATH / code
    folder_path = skill_folder / path
    
    # Security check
    try:
        folder_path.resolve().relative_to(skill_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder path"
        )
    
    if not folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder not found: {path}"
        )
    
    if not folder_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a folder"
        )
    
    # Don't allow deleting root folder
    if folder_path == skill_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete root skill folder"
        )
    
    shutil.rmtree(folder_path)
    
    logger.info(f"Deleted skill folder: {folder_path}")
    return {"message": "Folder deleted", "path": path}


# ==================== Boilerplate File Management ====================

def get_boilerplate_folder(code: str) -> Path:
    """Get boilerplate folder path for a stack code"""
    return BOILERPLATE_BASE_PATH / f"{code}-boilerplate"


@router.get("/{code}/boilerplate/tree")
def get_boilerplate_tree(code: str):
    """Get file tree for a boilerplate folder"""
    boilerplate_folder = get_boilerplate_folder(code)
    
    if not boilerplate_folder.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Boilerplate folder '{code}-boilerplate' not found"
        )
    
    tree = get_file_tree(boilerplate_folder, boilerplate_folder)
    return tree


@router.get("/{code}/boilerplate/file")
def read_boilerplate_file(
    code: str,
    path: str = Query(..., description="Relative file path"),
):
    """Read content of a boilerplate file"""
    boilerplate_folder = get_boilerplate_folder(code)
    file_path = boilerplate_folder / path
    
    # Security check
    try:
        file_path.resolve().relative_to(boilerplate_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {path}"
        )
    
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a file: {path}"
        )
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1")
    
    return FileContent(path=path, content=content)


@router.post("/{code}/boilerplate/file", status_code=status.HTTP_201_CREATED)
def create_boilerplate_file(
    code: str,
    data: CreateFileRequest = Body(...),
):
    """Create a new boilerplate file"""
    boilerplate_folder = get_boilerplate_folder(code)
    file_path = boilerplate_folder / data.path
    
    # Security check
    try:
        file_path.resolve().relative_to(boilerplate_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    if file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File already exists: {data.path}"
        )
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(data.content, encoding="utf-8")
    
    logger.info(f"Created boilerplate file: {file_path}")
    return {"message": "File created", "path": data.path}


@router.put("/{code}/boilerplate/file")
def update_boilerplate_file(
    code: str,
    data: UpdateFileRequest = Body(...),
):
    """Update content of a boilerplate file"""
    boilerplate_folder = get_boilerplate_folder(code)
    file_path = boilerplate_folder / data.path
    
    # Security check
    try:
        file_path.resolve().relative_to(boilerplate_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {data.path}"
        )
    
    file_path.write_text(data.content, encoding="utf-8")
    
    logger.info(f"Updated boilerplate file: {file_path}")
    return {"message": "File updated", "path": data.path}


@router.delete("/{code}/boilerplate/file")
def delete_boilerplate_file(
    code: str,
    path: str = Query(..., description="Relative file path"),
):
    """Delete a boilerplate file"""
    boilerplate_folder = get_boilerplate_folder(code)
    file_path = boilerplate_folder / path
    
    # Security check
    try:
        file_path.resolve().relative_to(boilerplate_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {path}"
        )
    
    if file_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use folder endpoint to delete folders"
        )
    
    file_path.unlink()
    
    logger.info(f"Deleted boilerplate file: {file_path}")
    return {"message": "File deleted", "path": path}


@router.post("/{code}/boilerplate/folder", status_code=status.HTTP_201_CREATED)
def create_boilerplate_folder(
    code: str,
    data: CreateFolderRequest = Body(...),
):
    """Create a new boilerplate folder"""
    boilerplate_folder = get_boilerplate_folder(code)
    folder_path = boilerplate_folder / data.path
    
    # Security check
    try:
        folder_path.resolve().relative_to(boilerplate_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder path"
        )
    
    if folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Folder already exists: {data.path}"
        )
    
    folder_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created boilerplate folder: {folder_path}")
    return {"message": "Folder created", "path": data.path}


@router.delete("/{code}/boilerplate/folder")
def delete_boilerplate_folder(
    code: str,
    path: str = Query(..., description="Relative folder path"),
):
    """Delete a boilerplate folder"""
    boilerplate_folder = get_boilerplate_folder(code)
    folder_path = boilerplate_folder / path
    
    # Security check
    try:
        folder_path.resolve().relative_to(boilerplate_folder.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder path"
        )
    
    if not folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder not found: {path}"
        )
    
    if not folder_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path is not a folder"
        )
    
    # Don't allow deleting root folder
    if folder_path == boilerplate_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete root boilerplate folder"
        )
    
    shutil.rmtree(folder_path)
    
    logger.info(f"Deleted boilerplate folder: {folder_path}")
    return {"message": "Folder deleted", "path": path}


@router.post("/{code}/boilerplate/upload")
async def upload_boilerplate_folder(
    code: str,
    files: List[UploadFile] = FastAPIFile(...),
    paths: List[str] = Query(..., description="Relative paths for each file"),
    clear_existing: bool = Query(False, description="Clear existing files before upload"),
):
    """
    Upload multiple files to boilerplate folder.
    Validates that files come from a folder named {code}-boilerplate.
    """
    boilerplate_folder = get_boilerplate_folder(code)
    expected_prefix = f"{code}-boilerplate"
    
    if len(files) != len(paths):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of files and paths must match"
        )
    
    # Validate all paths start with correct prefix
    for path in paths:
        # Path should be like: nextjs-boilerplate/src/app/page.tsx
        parts = path.replace("\\", "/").split("/")
        if not parts or parts[0] != expected_prefix:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid folder structure. Expected folder name: {expected_prefix}, got: {parts[0] if parts else 'empty'}"
            )
    
    # Clear existing files if requested
    if clear_existing and boilerplate_folder.exists():
        for item in boilerplate_folder.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        logger.info(f"Cleared existing boilerplate files: {boilerplate_folder}")
    
    # Ensure boilerplate folder exists
    boilerplate_folder.mkdir(parents=True, exist_ok=True)
    
    uploaded_count = 0
    skipped_count = 0
    
    for file, path in zip(files, paths):
        # Remove the {code}-boilerplate prefix from path
        relative_path = "/".join(path.replace("\\", "/").split("/")[1:])
        
        if not relative_path:
            skipped_count += 1
            continue
            
        # Skip certain files/folders
        skip_patterns = [".git/", "node_modules/", ".next/", "__pycache__/", ".DS_Store"]
        if any(pattern in relative_path for pattern in skip_patterns):
            skipped_count += 1
            continue
        
        file_path = boilerplate_folder / relative_path
        
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file content
        try:
            content = await file.read()
            file_path.write_bytes(content)
            uploaded_count += 1
        except Exception as e:
            logger.error(f"Failed to write file {relative_path}: {e}")
            skipped_count += 1
    
    logger.info(f"Uploaded boilerplate for {code}: {uploaded_count} files, {skipped_count} skipped")
    
    return {
        "message": "Upload completed",
        "uploaded": uploaded_count,
        "skipped": skipped_count,
    }
