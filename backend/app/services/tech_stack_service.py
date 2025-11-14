"""
Tech Stack Service - Business logic for tech stack management
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models import TechStack
from app.kanban_schemas import TechStackCreate, TechStackUpdate, TechStackResponse


class TechStackService:
    """Service for managing technology stacks"""

    @staticmethod
    async def create(data: TechStackCreate, db: AsyncSession) -> TechStack:
        """
        Create a new tech stack

        Args:
            data: Tech stack creation data
            db: Database session

        Returns:
            Created tech stack

        Raises:
            HTTPException: 400 if tech stack with name already exists
        """
        # Check if tech stack with same name already exists
        stmt = select(TechStack).where(
            TechStack.name == data.name,
            TechStack.deleted_at == None
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tech stack with name '{data.name}' already exists"
            )

        # Create tech stack
        tech_stack = TechStack(**data.model_dump())
        db.add(tech_stack)
        await db.commit()
        await db.refresh(tech_stack)

        return tech_stack

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[TechStack]:
        """
        Get all tech stacks (excluding soft deleted)

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of tech stacks
        """
        stmt = (
            select(TechStack)
            .where(TechStack.deleted_at == None)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        tech_stacks = result.scalars().all()

        return tech_stacks

    @staticmethod
    async def get_by_id(tech_stack_id: int, db: AsyncSession) -> TechStack:
        """
        Get tech stack by ID

        Args:
            tech_stack_id: Tech stack ID
            db: Database session

        Returns:
            Tech stack

        Raises:
            HTTPException: 404 if not found
        """
        stmt = select(TechStack).where(
            TechStack.id == tech_stack_id,
            TechStack.deleted_at == None
        )
        result = await db.execute(stmt)
        tech_stack = result.scalar_one_or_none()

        if not tech_stack:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tech stack with ID {tech_stack_id} not found"
            )
        return tech_stack

    @staticmethod
    async def update(
        tech_stack_id: int,
        data: TechStackUpdate,
        db: AsyncSession
    ) -> TechStack:
        """
        Update tech stack

        Args:
            tech_stack_id: Tech stack ID
            data: Update data
            db: Database session

        Returns:
            Updated tech stack

        Raises:
            HTTPException: 404 if not found, 400 if name conflict
        """
        # Get existing tech stack
        tech_stack = await TechStackService.get_by_id(tech_stack_id, db)

        # Check name conflict if name is being changed
        if data.name and data.name != tech_stack.name:
            stmt = select(TechStack).where(
                TechStack.name == data.name,
                TechStack.deleted_at == None
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tech stack with name '{data.name}' already exists"
                )

        # Update tech stack
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(tech_stack, key, value)

        await db.commit()
        await db.refresh(tech_stack)

        return tech_stack

    @staticmethod
    async def delete(tech_stack_id: int, db: AsyncSession) -> None:
        """
        Soft delete tech stack

        Args:
            tech_stack_id: Tech stack ID
            db: Database session

        Raises:
            HTTPException: 404 if not found
        """
        # Get existing tech stack
        tech_stack = await TechStackService.get_by_id(tech_stack_id, db)

        # Soft delete (set deleted_at)
        tech_stack.deleted_at = datetime.utcnow()
        await db.commit()
