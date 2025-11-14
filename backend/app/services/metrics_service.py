"""
Metrics Service - Business logic for Lean Kanban metrics and analytics

This service implements key Lean Kanban metrics:
- Throughput: Stories completed per time period
- Cycle Time: Time from IN_PROGRESS to DONE
- Lead Time: Time from TODO to DONE
- Work In Progress (WIP): Current stories by status
- Cumulative Flow Diagram (CFD): Historical WIP data
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from fastapi import HTTPException, status

from app.models import Story, Epic, Project, StoryStatusHistory
from app.dependencies import get_project_or_404
from app.enums import StoryStatus


class MetricsService:
    """Service for calculating Lean Kanban metrics"""

    # ==================== THROUGHPUT ====================

    @staticmethod
    async def get_throughput(
        project_id: int,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> dict:
        """
        Calculate throughput (stories completed per period)

        Throughput measures delivery rate - a key flow metric.

        Args:
            project_id: Project ID
            start_date: Period start date
            end_date: Period end date
            db: Database session

        Returns:
            Dictionary with throughput data
        """
        # Verify project exists
        await get_project_or_404(project_id, db)

        # Count stories completed in period (via project's epics)
        query = (
            select(func.count(Story.id))
            .join(Epic, Story.epic_id == Epic.id)
            .where(
                and_(
                    Epic.project_id == project_id,
                    Story.status == StoryStatus.DONE,
                    Story.completed_at >= start_date,
                    Story.completed_at <= end_date,
                    Story.deleted_at == None,
                    Epic.deleted_at == None
                )
            )
        )

        result = await db.execute(query)
        completed_count = result.scalar() or 0

        # Calculate period in days
        period_days = (end_date - start_date).days + 1

        return {
            "project_id": project_id,
            "start_date": start_date,
            "end_date": end_date,
            "period_days": period_days,
            "completed_stories": completed_count,
            "throughput_per_day": round(completed_count / period_days, 2) if period_days > 0 else 0
        }

    # ==================== CYCLE TIME ====================

    @staticmethod
    async def get_average_cycle_time(
        project_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: AsyncSession = None
    ) -> dict:
        """
        Calculate average cycle time (IN_PROGRESS to DONE)

        Cycle time measures how long work takes once started.
        This is a critical efficiency metric.

        Args:
            project_id: Project ID
            start_date: Optional filter - stories completed after this date
            end_date: Optional filter - stories completed before this date
            db: Database session

        Returns:
            Dictionary with average cycle time
        """
        # Verify project exists
        await get_project_or_404(project_id, db)

        # Get all completed stories in period
        story_query = (
            select(Story.id)
            .join(Epic, Story.epic_id == Epic.id)
            .where(
                and_(
                    Epic.project_id == project_id,
                    Story.status == StoryStatus.DONE,
                    Story.deleted_at == None,
                    Epic.deleted_at == None
                )
            )
        )

        if start_date:
            story_query = story_query.where(Story.completed_at >= start_date)
        if end_date:
            story_query = story_query.where(Story.completed_at <= end_date)

        result = await db.execute(story_query)
        story_ids = [row[0] for row in result.fetchall()]

        if not story_ids:
            return {
                "project_id": project_id,
                "stories_analyzed": 0,
                "average_cycle_time_hours": None,
                "min_cycle_time_hours": None,
                "max_cycle_time_hours": None
            }

        # Calculate cycle times for each story
        cycle_times = []

        for story_id in story_ids:
            # Get first IN_PROGRESS and first DONE from history
            history_query = (
                select(StoryStatusHistory)
                .where(StoryStatusHistory.story_id == story_id)
                .order_by(StoryStatusHistory.changed_at.asc())
            )

            result = await db.execute(history_query)
            history = result.scalars().all()

            first_in_progress = next(
                (h for h in history if h.new_status == StoryStatus.IN_PROGRESS),
                None
            )
            first_done = next(
                (h for h in history if h.new_status == StoryStatus.DONE),
                None
            )

            if first_in_progress and first_done:
                cycle_time_seconds = (first_done.changed_at - first_in_progress.changed_at).total_seconds()
                cycle_time_hours = cycle_time_seconds / 3600
                cycle_times.append(cycle_time_hours)

        if not cycle_times:
            return {
                "project_id": project_id,
                "stories_analyzed": len(story_ids),
                "average_cycle_time_hours": None,
                "min_cycle_time_hours": None,
                "max_cycle_time_hours": None
            }

        return {
            "project_id": project_id,
            "stories_analyzed": len(story_ids),
            "average_cycle_time_hours": round(sum(cycle_times) / len(cycle_times), 2),
            "min_cycle_time_hours": round(min(cycle_times), 2),
            "max_cycle_time_hours": round(max(cycle_times), 2)
        }

    # ==================== LEAD TIME ====================

    @staticmethod
    async def get_average_lead_time(
        project_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: AsyncSession = None
    ) -> dict:
        """
        Calculate average lead time (TODO to DONE)

        Lead time measures total time from request to delivery.
        This includes waiting time before work starts.

        Args:
            project_id: Project ID
            start_date: Optional filter - stories completed after this date
            end_date: Optional filter - stories completed before this date
            db: Database session

        Returns:
            Dictionary with average lead time
        """
        # Verify project exists
        await get_project_or_404(project_id, db)

        # Get all completed stories in period
        story_query = (
            select(Story.id)
            .join(Epic, Story.epic_id == Epic.id)
            .where(
                and_(
                    Epic.project_id == project_id,
                    Story.status == StoryStatus.DONE,
                    Story.deleted_at == None,
                    Epic.deleted_at == None
                )
            )
        )

        if start_date:
            story_query = story_query.where(Story.completed_at >= start_date)
        if end_date:
            story_query = story_query.where(Story.completed_at <= end_date)

        result = await db.execute(story_query)
        story_ids = [row[0] for row in result.fetchall()]

        if not story_ids:
            return {
                "project_id": project_id,
                "stories_analyzed": 0,
                "average_lead_time_hours": None,
                "min_lead_time_hours": None,
                "max_lead_time_hours": None
            }

        # Calculate lead times for each story
        lead_times = []

        for story_id in story_ids:
            # Get first TODO (creation) and first DONE from history
            history_query = (
                select(StoryStatusHistory)
                .where(StoryStatusHistory.story_id == story_id)
                .order_by(StoryStatusHistory.changed_at.asc())
            )

            result = await db.execute(history_query)
            history = result.scalars().all()

            # First record should be creation (TODO)
            first_todo = next(
                (h for h in history if h.new_status == StoryStatus.TODO),
                None
            )
            first_done = next(
                (h for h in history if h.new_status == StoryStatus.DONE),
                None
            )

            if first_todo and first_done:
                lead_time_seconds = (first_done.changed_at - first_todo.changed_at).total_seconds()
                lead_time_hours = lead_time_seconds / 3600
                lead_times.append(lead_time_hours)

        if not lead_times:
            return {
                "project_id": project_id,
                "stories_analyzed": len(story_ids),
                "average_lead_time_hours": None,
                "min_lead_time_hours": None,
                "max_lead_time_hours": None
            }

        return {
            "project_id": project_id,
            "stories_analyzed": len(story_ids),
            "average_lead_time_hours": round(sum(lead_times) / len(lead_times), 2),
            "min_lead_time_hours": round(min(lead_times), 2),
            "max_lead_time_hours": round(max(lead_times), 2)
        }

    # ==================== WORK IN PROGRESS ====================

    @staticmethod
    async def get_current_wip(project_id: int, db: AsyncSession) -> dict:
        """
        Get current Work In Progress by status

        WIP is a fundamental Kanban metric showing current load.
        Monitoring WIP helps identify bottlenecks.

        Args:
            project_id: Project ID
            db: Database session

        Returns:
            Dictionary with WIP counts by status
        """
        # Verify project exists
        project = await get_project_or_404(project_id, db)

        # Count stories by status (via project's epics)
        query = (
            select(Story.status, func.count(Story.id))
            .join(Epic, Story.epic_id == Epic.id)
            .where(
                and_(
                    Epic.project_id == project_id,
                    Story.deleted_at == None,
                    Epic.deleted_at == None
                )
            )
            .group_by(Story.status)
        )

        result = await db.execute(query)
        wip_by_status = {row[0]: row[1] for row in result}

        # Calculate total active WIP (exclude DONE and ARCHIVED)
        active_wip = sum(
            count for status, count in wip_by_status.items()
            if status not in [StoryStatus.DONE, StoryStatus.ARCHIVED]
        )

        return {
            "project_id": project_id,
            "project_name": project.name,
            "total_active_wip": active_wip,
            "by_status": wip_by_status
        }

    # ==================== CUMULATIVE FLOW DIAGRAM ====================

    @staticmethod
    async def get_cumulative_flow(
        project_id: int,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession
    ) -> dict:
        """
        Generate Cumulative Flow Diagram data

        CFD shows how work accumulates over time in each status.
        It's one of the most powerful Kanban visualizations for:
        - Identifying bottlenecks
        - Predicting delivery dates
        - Monitoring flow health

        Args:
            project_id: Project ID
            start_date: Period start date
            end_date: Period end date
            db: Database session

        Returns:
            Dictionary with CFD data points
        """
        # Verify project exists
        await get_project_or_404(project_id, db)

        # Generate daily data points
        current_date = start_date
        cfd_data = []

        while current_date <= end_date:
            # For each day, count stories in each status at end of day
            day_end = current_date.replace(hour=23, minute=59, second=59)

            # Get all stories that existed at this point
            story_query = (
                select(Story.id)
                .join(Epic, Story.epic_id == Epic.id)
                .where(
                    and_(
                        Epic.project_id == project_id,
                        Story.created_at <= day_end,
                        Epic.deleted_at == None
                    )
                )
            )

            result = await db.execute(story_query)
            story_ids = [row[0] for row in result.fetchall()]

            # For each story, determine its status at day_end
            status_counts = {status: 0 for status in StoryStatus}

            for story_id in story_ids:
                # Get latest status change before day_end
                history_query = (
                    select(StoryStatusHistory.new_status)
                    .where(
                        and_(
                            StoryStatusHistory.story_id == story_id,
                            StoryStatusHistory.changed_at <= day_end
                        )
                    )
                    .order_by(StoryStatusHistory.changed_at.desc())
                    .limit(1)
                )

                result = await db.execute(history_query)
                status = result.scalar()

                if status:
                    status_counts[status] += 1

            cfd_data.append({
                "date": current_date.date().isoformat(),
                "counts": status_counts
            })

            # Move to next day
            current_date += timedelta(days=1)

        return {
            "project_id": project_id,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "data_points": len(cfd_data),
            "cfd_data": cfd_data
        }

    # ==================== BLOCKED STORIES ====================

    @staticmethod
    async def get_blocked_stories(project_id: int, db: AsyncSession) -> dict:
        """
        Get all currently blocked stories

        Blocked stories represent impediments that need attention.
        This metric helps with impediment management.

        Args:
            project_id: Project ID
            db: Database session

        Returns:
            Dictionary with blocked stories data
        """
        # Verify project exists
        await get_project_or_404(project_id, db)

        # Get blocked stories
        query = (
            select(Story)
            .join(Epic, Story.epic_id == Epic.id)
            .where(
                and_(
                    Epic.project_id == project_id,
                    Story.status == StoryStatus.BLOCKED,
                    Story.deleted_at == None,
                    Epic.deleted_at == None
                )
            )
        )

        result = await db.execute(query)
        blocked_stories = result.scalars().all()

        # Calculate how long each has been blocked
        blocked_details = []

        for story in blocked_stories:
            # Find when it was blocked
            history_query = (
                select(StoryStatusHistory.changed_at)
                .where(
                    and_(
                        StoryStatusHistory.story_id == story.id,
                        StoryStatusHistory.new_status == StoryStatus.BLOCKED
                    )
                )
                .order_by(StoryStatusHistory.changed_at.desc())
                .limit(1)
            )

            result = await db.execute(history_query)
            blocked_at = result.scalar()

            blocked_duration = None
            if blocked_at:
                duration_seconds = (datetime.utcnow() - blocked_at).total_seconds()
                blocked_duration = round(duration_seconds / 3600, 2)  # hours

            blocked_details.append({
                "story_id": story.id,
                "story_title": story.title,
                "epic_id": story.epic_id,
                "blocked_at": blocked_at,
                "blocked_duration_hours": blocked_duration
            })

        return {
            "project_id": project_id,
            "blocked_count": len(blocked_stories),
            "blocked_stories": blocked_details
        }
