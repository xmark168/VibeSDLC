"""Story Service - Encapsulates story database operations and business logic."""

from datetime import datetime
from uuid import UUID
from typing import Optional, List
from sqlmodel import Session, select, update, and_
from sqlalchemy.sql import ColumnElement

from app.models import Story, StoryStatus, StoryType
from app.schemas.story import StoryCreate, StoryUpdate, StoryPublic


class StoryService:
    """Service for story database operations and business logic.

    Consolidates all story-related DB operations to avoid duplicate code
    and provide business logic for story management.
    """

    def __init__(self, session: Session):
        self.session = session

    # ===== Story Creation =====

    def create(self, story_in: StoryCreate) -> Story:
        """Create a new story.

        Args:
            story_in: Story creation schema

        Returns:
            Story: Created story instance
        """
        # Prepare story data from input
        story_data = story_in.model_dump()

        # Create story instance
        db_story = Story(
            project_id=story_data["project_id"],
            title=story_data["title"],
            description=story_data.get("description"),
            type=story_data.get("story_type", StoryType.USER_STORY),
            status=StoryStatus.TODO,  # Default to TODO when creating
            priority=story_data.get("priority"),  # 1-3 (1=High, 2=Medium, 3=Low)
            story_point=story_data.get("story_point"),  # Fibonacci scale
            acceptance_criteria=story_data.get("acceptance_criteria"),
            assignee_id=story_data.get("assigned_to"),
            epic_id=story_data.get("epic_id"),
            parent_id=story_data.get("parent_story_id"),
            target_release=story_data.get("target_release"),
            dependencies=story_data.get("dependencies", []),
            tags=story_data.get("tags", []),
            labels=story_data.get("labels", []),
            business_value=story_data.get("business_value"),
            risk_level=story_data.get("risk_level"),
        )

        self.session.add(db_story)
        self.session.commit()
        self.session.refresh(db_story)
        return db_story

    # ===== Story Retrieval =====

    def get_by_id(self, story_id: UUID) -> Optional[Story]:
        """Get story by ID.

        Args:
            story_id: UUID of the story

        Returns:
            Story or None if not found
        """
        return self.session.get(Story, story_id)

    def get_by_project_and_status(
        self,
        project_id: UUID,
        status: StoryStatus
    ) -> List[Story]:
        """Get all stories in a project with a specific status.

        Args:
            project_id: Project UUID
            status: Story status to filter by

        Returns:
            List of stories
        """
        statement = (
            select(Story)
            .where(Story.project_id == project_id)
            .where(Story.status == status)
            .order_by(Story.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_all_by_project(self, project_id: UUID) -> List[Story]:
        """Get all stories in a project.

        Args:
            project_id: Project UUID

        Returns:
            List of stories
        """
        statement = (
            select(Story)
            .where(Story.project_id == project_id)
            .order_by(Story.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_by_project_and_assignee(
        self,
        project_id: UUID,
        assignee_id: UUID
    ) -> List[Story]:
        """Get all stories in a project assigned to a specific user.

        Args:
            project_id: Project UUID
            assignee_id: UUID of the assignee

        Returns:
            List of stories
        """
        statement = (
            select(Story)
            .where(Story.project_id == project_id)
            .where(Story.assignee_id == assignee_id)
            .order_by(Story.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_by_project_and_type(
        self,
        project_id: UUID,
        story_type: StoryType
    ) -> List[Story]:
        """Get all stories in a project of a specific type.

        Args:
            project_id: Project UUID
            story_type: Type of story to filter by

        Returns:
            List of stories
        """
        statement = (
            select(Story)
            .where(Story.project_id == project_id)
            .where(Story.type == story_type)
            .order_by(Story.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_by_project_and_priority(
        self,
        project_id: UUID,
        priority_value: int
    ) -> List[Story]:
        """Get all stories in a project with a specific priority.

        Args:
            project_id: Project UUID
            priority_value: Priority value (1-5)

        Returns:
            List of stories
        """
        statement = (
            select(Story)
            .where(Story.project_id == project_id)
            .where(Story.priority == priority_value)
            .order_by(Story.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_by_project_and_title(
        self,
        project_id: UUID,
        title: str
    ) -> List[Story]:
        """Get stories in a project matching a title pattern.

        Args:
            project_id: Project UUID
            title: Title pattern to match (case-insensitive)

        Returns:
            List of stories
        """
        statement = (
            select(Story)
            .where(Story.project_id == project_id)
            .where(Story.title.ilike(f"%{title}%"))
            .order_by(Story.created_at.desc())
        )
        return self.session.exec(statement).all()

    # ===== Story Update =====

    def update(self, db_story: Story, story_in: StoryUpdate) -> Story:
        """Update a story.

        Args:
            db_story: Story instance to update
            story_in: Story update schema

        Returns:
            Story: Updated story instance
        """
        # Get non-None fields from update schema
        update_data = story_in.model_dump(exclude_unset=True)

        # Update story fields
        for field, value in update_data.items():
            if hasattr(db_story, field):
                if field == 'status':
                    # Handle status change business logic
                    setattr(db_story, field, value)
                    self._handle_status_change(db_story, value)
                elif field == 'assigned_to':
                    # Map to assignee_id in the model
                    setattr(db_story, 'assignee_id', value)
                elif field == 'story_type':
                    # Map to type in the model
                    setattr(db_story, 'type', value)
                else:
                    setattr(db_story, field, value)

        self.session.add(db_story)
        self.session.commit()
        self.session.refresh(db_story)
        return db_story

    def update_status(self, story_id: UUID, new_status: StoryStatus) -> Optional[Story]:
        """Update story status with business logic.

        Args:
            story_id: UUID of the story
            new_status: New status to set

        Returns:
            Updated story or None if not found
        """
        db_story = self.session.get(Story, story_id)
        if not db_story:
            return None

        old_status = db_story.status
        db_story.status = new_status

        # Handle status change business logic
        self._handle_status_change(db_story, new_status, old_status)

        self.session.add(db_story)
        self.session.commit()
        self.session.refresh(db_story)
        return db_story

    def _handle_status_change(
        self,
        story: Story,
        new_status: StoryStatus,
        old_status: Optional[StoryStatus] = None
    ) -> None:
        """Handle business logic for status change.

        Args:
            story: Story instance
            new_status: New status
            old_status: Previous status (optional for initialization)
        """
        current_time = datetime.now()

        if new_status == StoryStatus.IN_PROGRESS and old_status != StoryStatus.IN_PROGRESS:
            # When moving to In Progress, record the time
            story.started_at = current_time
        elif new_status == StoryStatus.REVIEW and old_status != StoryStatus.REVIEW:
            # When moving to Review, record the time
            story.review_started_at = current_time
        elif new_status == StoryStatus.DONE and old_status != StoryStatus.DONE:
            # When moving to Done, record completion time
            story.completed_at = current_time

    # ===== Story Deletion =====

    def delete(self, story_id: UUID) -> bool:
        """Delete a story by ID.

        Args:
            story_id: UUID of the story to delete

        Returns:
            True if deleted, False if not found
        """
        db_story = self.session.get(Story, story_id)
        if db_story:
            self.session.delete(db_story)
            self.session.commit()
            return True
        return False

    # ===== Search and Filter =====

    def search_by_criteria(
        self,
        project_id: UUID,
        title: Optional[str] = None,
        status: Optional[StoryStatus] = None,
        story_type: Optional[StoryType] = None,
        assignee_id: Optional[UUID] = None,
        priority: Optional[int] = None,
    ) -> List[Story]:
        """Search stories by multiple criteria.

        Args:
            project_id: Project UUID
            title: Title pattern to match
            status: Status to filter by
            story_type: Story type to filter by
            assignee_id: Assignee UUID to filter by
            priority: Priority to filter by

        Returns:
            List of matching stories
        """
        filters = [Story.project_id == project_id]
        
        if title:
            filters.append(Story.title.ilike(f"%{title}%"))
        if status:
            filters.append(Story.status == status)
        if story_type:
            filters.append(Story.type == story_type)
        if assignee_id:
            filters.append(Story.assignee_id == assignee_id)
        if priority:
            filters.append(Story.priority == priority)

        statement = select(Story).where(and_(*filters)).order_by(Story.created_at.desc())
        return self.session.exec(statement).all()

    def get_story_stats(self, project_id: UUID) -> dict:
        """Get story statistics for a project.

        Args:
            project_id: Project UUID

        Returns:
            Dictionary with story statistics
        """
        all_stories = self.get_all_by_project(project_id)
        total = len(all_stories)

        status_counts = {
            StoryStatus.TODO: 0,
            StoryStatus.IN_PROGRESS: 0,
            StoryStatus.REVIEW: 0,
            StoryStatus.DONE: 0,
        }

        type_counts = {
            StoryType.USER_STORY: 0,
            StoryType.ENABLER_STORY: 0,
        }

        total_points = 0
        completed_points = 0

        for story in all_stories:
            status_counts[story.status] += 1
            type_counts[story.type] += 1

            if story.story_point:
                total_points += story.story_point
                if story.status == StoryStatus.DONE:
                    completed_points += story.story_point

        completed = status_counts[StoryStatus.DONE]
        in_progress = status_counts[StoryStatus.IN_PROGRESS]

        return {
            "total": total,
            "todo": status_counts[StoryStatus.TODO],
            "in_progress": in_progress,
            "review": status_counts[StoryStatus.REVIEW],
            "done": completed,
            "completed_percentage": (completed / total * 100) if total > 0 else 0,
            "total_story_points": total_points,
            "completed_story_points": completed_points,
            "completion_percentage_by_points": (completed_points / total_points * 100) if total_points > 0 else 0,
            "user_stories": type_counts[StoryType.USER_STORY],
            "enabler_stories": type_counts[StoryType.ENABLER_STORY],
        }

    def bulk_update_status(
        self,
        project_id: UUID,
        from_status: StoryStatus,
        to_status: StoryStatus
    ) -> int:
        """Bulk update story statuses within a project.

        Args:
            project_id: Project UUID
            from_status: Status to update from
            to_status: Status to update to

        Returns:
            Number of stories updated
        """
        current_time = datetime.now()
        
        # Update stories
        stmt = (
            update(Story)
            .where(Story.project_id == project_id)
            .where(Story.status == from_status)
            .values(status=to_status)
        )
        
        # Handle status change logic for each updated story
        stories_to_update = self.session.exec(
            select(Story).where(
                Story.project_id == project_id,
                Story.status == from_status
            )
        ).all()
        
        result = self.session.exec(stmt)
        self.session.commit()
        
        # Apply additional logic for status changes
        for story in stories_to_update:
            self._handle_status_change(story, to_status, from_status)
            self.session.add(story)
        
        self.session.commit()
        return result.rowcount

    def get_stories_by_epic(self, epic_id: UUID) -> List[Story]:
        """Get all stories associated with an epic.

        Args:
            epic_id: UUID of the epic

        Returns:
            List of stories
        """
        statement = (
            select(Story)
            .where(Story.epic_id == epic_id)
            .order_by(Story.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_stories_by_parent(self, parent_id: UUID) -> List[Story]:
        """Get all child stories of a parent story.

        Args:
            parent_id: UUID of the parent story

        Returns:
            List of child stories
        """
        statement = (
            select(Story)
            .where(Story.parent_id == parent_id)
            .order_by(Story.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_unassigned_stories(self, project_id: UUID) -> List[Story]:
        """Get all unassigned stories in a project.

        Args:
            project_id: Project UUID

        Returns:
            List of unassigned stories
        """
        statement = (
            select(Story)
            .where(Story.project_id == project_id)
            .where(Story.assignee_id.is_(None))
            .order_by(Story.created_at.desc())
        )
        return self.session.exec(statement).all()