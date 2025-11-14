"""
Epic Service - Business logic for epic management
"""
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models import Epic, User, Story
from app.kanban_schemas import EpicCreate, EpicUpdate
from app.dependencies import get_epic_with_project, get_project_or_404, verify_project_owner
from app.enums import StoryStatus


class EpicService:
    """Service for managing epics"""

    @staticmethod
    async def create(data: EpicCreate, current_user: User, db: AsyncSession) -> Epic:
        """
        Create a new epic

        Args:
            data: Epic creation data
            current_user: Current authenticated user
            db: Database session

        Returns:
            Created epic

        Raises:
            HTTPException: 403 if user is not project owner
            HTTPException: 404 if project not found
        """
        # 1. Verify project exists and user is owner
        project = await get_project_or_404(data.project_id, db)
        await verify_project_owner(project, current_user)

        # 2. Create epic
        epic = Epic(**data.model_dump())
        db.add(epic)
        await db.commit()
        await db.refresh(epic)

        return epic

    @staticmethod
    async def get_by_project(project_id: int, db: AsyncSession) -> List[Epic]:
        """
        Get epics by project

        Args:
            project_id: Project ID
            db: Database session

        Returns:
            List of epics
        """
        stmt = select(Epic).where(
            Epic.project_id == project_id,
            Epic.deleted_at == None
        )
        result = await db.execute(stmt)
        epics = result.scalars().all()
        return epics

    @staticmethod
    async def get_by_id(epic_id: int, db: AsyncSession) -> Epic:
        """
        Get epic by ID

        Args:
            epic_id: Epic ID
            db: Database session

        Returns:
            Epic

        Raises:
            HTTPException: 404 if not found
        """
        epic, _ = await get_epic_with_project(epic_id, db)
        return epic

    @staticmethod
    async def update(
        epic_id: int,
        data: EpicUpdate,
        current_user: User,
        db: AsyncSession
    ) -> Epic:
        """
        Update epic

        Args:
            epic_id: Epic ID
            data: Update data
            current_user: Current authenticated user
            db: Database session

        Returns:
            Updated epic

        Raises:
            HTTPException: 404 if not found
            HTTPException: 403 if user is not project owner
        """
        # 1. Get existing epic with project
        epic, project = await get_epic_with_project(epic_id, db)

        # 2. Verify project ownership
        await verify_project_owner(project, current_user)

        # 3. Update epic
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(epic, key, value)
        await db.commit()
        await db.refresh(epic)

        return epic

    @staticmethod
    async def delete(epic_id: int, current_user: User, db: AsyncSession) -> None:
        """
        Soft delete epic

        Args:
            epic_id: Epic ID
            current_user: Current authenticated user
            db: Database session

        Raises:
            HTTPException: 404 if not found
            HTTPException: 403 if user is not project owner
        """
        # 1. Get existing epic with project
        epic, project = await get_epic_with_project(epic_id, db)

        # 2. Verify project ownership
        await verify_project_owner(project, current_user)

        # 3. Soft delete (set deleted_at)
        epic.deleted_at = datetime.utcnow()
        await db.commit()

    @staticmethod
    async def get_stories(epic_id: int, db: AsyncSession) -> List[Story]:
        """
        Get all stories in epic

        Args:
            epic_id: Epic ID
            db: Database session

        Returns:
            List of stories

        Raises:
            HTTPException: 404 if epic not found
        """
        # Verify epic exists
        await EpicService.get_by_id(epic_id, db)

        # Get stories
        stmt = select(Story).where(
            Story.epic_id == epic_id,
            Story.deleted_at == None
        )
        result = await db.execute(stmt)
        stories = result.scalars().all()
        return stories

    @staticmethod
    async def get_progress(epic_id: int, db: AsyncSession) -> dict:
        """
        Calculate epic progress statistics

        Args:
            epic_id: Epic ID
            db: Database session

        Returns:
            Dictionary with progress stats

        Raises:
            HTTPException: 404 if epic not found
        """
        # Verify epic exists
        epic = await EpicService.get_by_id(epic_id, db)

        # Count stories by status
        query = (
            select(Story.status, func.count(Story.id))
            .where(
                Story.epic_id == epic_id,
                Story.deleted_at == None
            )
            .group_by(Story.status)
        )

        result = await db.execute(query)
        status_counts = {row[0]: row[1] for row in result}

        # Calculate totals
        total_stories = sum(status_counts.values())
        completed_stories = status_counts.get(StoryStatus.DONE, 0) + status_counts.get(StoryStatus.ARCHIVED, 0)
        in_progress_stories = status_counts.get(StoryStatus.IN_PROGRESS, 0)
        blocked_stories = status_counts.get(StoryStatus.BLOCKED, 0)

        # Calculate percentage
        completion_percentage = (
            (completed_stories / total_stories * 100) if total_stories > 0 else 0
        )

        return {
            "epic_id": epic_id,
            "epic_title": epic.title,
            "total_stories": total_stories,
            "completed_stories": completed_stories,
            "in_progress_stories": in_progress_stories,
            "blocked_stories": blocked_stories,
            "completion_percentage": round(completion_percentage, 2),
            "by_status": status_counts
        }
