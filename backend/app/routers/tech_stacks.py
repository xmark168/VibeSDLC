"""
Tech Stack Router - API endpoints for tech stack management
"""
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.tech_stack_service import TechStackService
from app.kanban_schemas import TechStackCreate, TechStackUpdate, TechStackResponse


router = APIRouter(prefix="/tech-stacks", tags=["Tech Stacks"])


@router.post(
    "",
    response_model=TechStackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tech stack"
)
async def create_tech_stack(
    data: TechStackCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new technology stack

    - **name**: Unique name for the tech stack
    - **data**: Optional JSON data with tech specifications

    Returns the created tech stack
    """
    tech_stack = await TechStackService.create(data, db)
    return tech_stack


@router.get(
    "",
    response_model=List[TechStackResponse],
    summary="List tech stacks"
)
async def list_tech_stacks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of all technology stacks

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return

    Returns list of tech stacks
    """
    tech_stacks = await TechStackService.get_all(db, skip, limit)
    return tech_stacks


@router.get(
    "/{tech_stack_id}",
    response_model=TechStackResponse,
    summary="Get tech stack by ID"
)
async def get_tech_stack(
    tech_stack_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific technology stack by ID

    Returns tech stack details
    """
    tech_stack = await TechStackService.get_by_id(tech_stack_id, db)
    return tech_stack


@router.put(
    "/{tech_stack_id}",
    response_model=TechStackResponse,
    summary="Update tech stack"
)
async def update_tech_stack(
    tech_stack_id: int,
    data: TechStackUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a technology stack

    - **name**: Update name (must be unique)
    - **data**: Update JSON data

    Returns updated tech stack
    """
    tech_stack = await TechStackService.update(tech_stack_id, data, db)
    return tech_stack


@router.delete(
    "/{tech_stack_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tech stack"
)
async def delete_tech_stack(
    tech_stack_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete a technology stack

    The tech stack will be marked as deleted but not removed from database
    """
    await TechStackService.delete(tech_stack_id, db)
