"""Story Service - Encapsulates story database operations and business logic."""

import logging
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select, update, and_, func
from sqlalchemy.sql import ColumnElement

from app.models import Story, StoryStatus, StoryType, IssueActivity, Project, WorkflowPolicy
from app.schemas.story import StoryCreate, StoryUpdate, StoryPublic

logger = logging.getLogger(__name__)


class StoryService:
    """Service for story database operations and business logic.

    Consolidates all story-related DB operations to avoid duplicate code
    and provide business logic for story management.
    """

    def __init__(self, session: Session):
        self.session = session

    def _generate_story_code(self, project_id: UUID, epic_id: Optional[UUID] = None) -> str:
        """Generate story code in format EPIC-XXX-US-YYY or US-YYY.
        
        Args:
            project_id: Project UUID
            epic_id: Optional Epic UUID
            
        Returns:
            Generated story code string
        """
        from app.models import Epic
        
        if epic_id:
            # Get epic code
            epic = self.session.get(Epic, epic_id)
            epic_code = epic.epic_code if epic and epic.epic_code else f"EPIC-{str(epic_id)[:3].upper()}"
            
            # Count existing stories in this epic
            story_count = self.session.exec(
                select(func.count()).select_from(Story).where(
                    Story.epic_id == epic_id
                )
            ).one()
            
            return f"{epic_code}-US-{story_count + 1:03d}"
        else:
            # No epic - generate US-XXX based on project story count
            story_count = self.session.exec(
                select(func.count()).select_from(Story).where(
                    Story.project_id == project_id,
                    Story.epic_id == None
                )
            ).one()
            
            return f"US-{story_count + 1:03d}"

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
            story_code=story_data.get("story_code"),  # e.g., "EPIC-001-US-001"
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

    # ===== Review Action =====

    async def handle_review_action(
        self,
        story_id: UUID,
        action: str,
        user_id: UUID,
        suggested_title: Optional[str] = None,
        suggested_acceptance_criteria: Optional[List[str]] = None,
        suggested_requirements: Optional[List[str]] = None
    ) -> Story:
        """Handle user action on story review (apply/keep/remove).
        
        Executes the action and publishes event for BA agent response.

        Args:
            story_id: UUID of the story
            action: Action type ('apply', 'keep', 'remove')
            user_id: UUID of the user taking action
            suggested_title: Suggested title (for apply action)
            suggested_acceptance_criteria: Suggested AC (for apply action)
            suggested_requirements: Suggested requirements (for apply action)

        Returns:
            Story: Updated story instance

        Raises:
            ValueError: If story not found
        """
        story = self.session.get(Story, story_id)
        if not story:
            raise ValueError(f"Story {story_id} not found")

        story_title = story.title
        project_id = story.project_id

        # Execute action
        if action == "apply":
            if suggested_title:
                story.title = suggested_title
            if suggested_acceptance_criteria:
                story.acceptance_criteria = suggested_acceptance_criteria
            if suggested_requirements:
                story.requirements = suggested_requirements
            self.session.add(story)
            self.session.commit()
            self.session.refresh(story)

        elif action == "remove":
            # Delete story permanently
            self.session.delete(story)
            self.session.commit()
            story = None  # Story no longer exists

        # action == "keep" → no changes needed

        # Update original message's structured_data to persist the action
        try:
            from app.models import Message
            from sqlalchemy.orm.attributes import flag_modified
            
            # Find the original story_review message for this story
            statement = select(Message).where(
                Message.project_id == project_id,
                Message.message_type == "story_review"
            ).order_by(Message.created_at.desc())
            
            messages = self.session.exec(statement).all()
            for msg in messages:
                if msg.structured_data and msg.structured_data.get("story_id") == str(story_id):
                    # Map action to actionTaken format
                    action_map = {"apply": "applied", "keep": "kept", "remove": "removed"}
                    msg.structured_data = {
                        **msg.structured_data,
                        "action_taken": action_map.get(action, action)
                    }
                    flag_modified(msg, "structured_data")
                    self.session.add(msg)
                    self.session.commit()
                    logger.info(f"Updated message {msg.id} with action_taken: {action}")
                    break
        except Exception as e:
            logger.warning(f"Failed to update message structured_data: {e}")

        # Save confirmation message directly (sync) instead of async Kafka flow
        # This ensures message exists when frontend refetches after API returns
        try:
            from app.models import Message, AuthorType
            
            confirmation_messages = {
                "apply": f"Áp dụng gợi ý cho story \"{story_title}\".",
                "keep": f"Giữ nguyên story \"{story_title}\".",
                "remove": f"Loại bỏ story \"{story_title}\"."
            }
            content = confirmation_messages.get(action, f"Đã xử lý story \"{story_title}\".")
            
            confirmation_msg = Message(
                project_id=project_id,
                content=content,
                author_type=AuthorType.AGENT,
                message_type="text",
                message_metadata={"agent_name": "Business Analyst"}
            )
            self.session.add(confirmation_msg)
            self.session.commit()
            logger.info(f"Saved confirmation message for {action} action on story {story_id}")
        except Exception as e:
            logger.error(f"Failed to save confirmation message: {e}")

        return story

    # ===== Enhanced Methods with Events =====

    async def create_with_events(
        self,
        story_in: StoryCreate,
        user_id: UUID,
        user_name: str,
        override_epic_id: Optional[UUID] = None
    ) -> Story:
        """Create story with activity logging and Kafka event.

        Args:
            story_in: Story creation schema
            user_id: ID of user creating the story
            user_name: Name of user for activity log
            override_epic_id: Optional epic ID to override (used when creating new epic)

        Returns:
            Story: Created story instance
        """
        # Validate project
        project = self.session.get(Project, story_in.project_id)
        if not project:
            raise ValueError("Project not found")

        # Auto-assign rank
        story_data = story_in.model_dump()
        
        # Apply override_epic_id if provided (from newly created epic)
        if override_epic_id:
            story_data["epic_id"] = override_epic_id
        
        if story_data.get("rank") is None:
            max_rank = self.session.exec(
                select(func.max(Story.rank)).where(
                    Story.project_id == story_in.project_id,
                    Story.status == StoryStatus.TODO
                )
            ).one()
            story_data["rank"] = (max_rank or 0) + 1
        
        # Auto-generate story_code if not provided
        if not story_data.get("story_code"):
            story_data["story_code"] = self._generate_story_code(
                project_id=story_in.project_id,
                epic_id=story_data.get("epic_id")
            )
        
        # Map schema fields to model fields
        if "story_type" in story_data:
            story_data["type"] = story_data.pop("story_type")
        if "assigned_to" in story_data:
            story_data["assignee_id"] = story_data.pop("assigned_to")
        if "parent_story_id" in story_data:
            story_data["parent_id"] = story_data.pop("parent_story_id")
        
        # Remove new_epic fields (not part of Story model)
        story_data.pop("new_epic_title", None)
        story_data.pop("new_epic_domain", None)
        story_data.pop("new_epic_description", None)

        story = Story(**story_data)
        self.session.add(story)
        self.session.commit()
        self.session.refresh(story)

        # Log activity
        activity = IssueActivity(
            issue_id=story.id,
            actor_id=str(user_id),
            actor_name=user_name,
            note="Story created by BA"
        )
        self.session.add(activity)
        self.session.commit()

        # Publish Kafka event
        await self._publish_story_event(
            event_type="story.created",
            story=story,
            user_id=user_id
        )

        return story

    def get_kanban_board(self, project_id: UUID) -> Dict[str, Any]:
        """Get Kanban board grouped by columns with WIP limits.

        Args:
            project_id: Project UUID

        Returns:
            Dict with board data and WIP limits
        """
        from sqlalchemy.orm import selectinload

        project = self.session.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")

        statement = select(Story).where(
            Story.project_id == project_id
        ).options(
            selectinload(Story.parent),
            selectinload(Story.children),
            selectinload(Story.epic)
        ).order_by(Story.status, Story.rank)

        stories = self.session.exec(statement).all()

        # Group by status
        board = {
            "Todo": [],
            "InProgress": [],
            "Review": [],
            "Done": [],
            "Archived": []
        }

        for story in stories:
            column = story.status.value
            if column in board:
                story_data = StoryPublic.model_validate(story)
                # Add epic info if epic exists
                if story.epic:
                    story_data.epic_code = story.epic.epic_code
                    story_data.epic_title = story.epic.title
                    story_data.epic_description = story.epic.description
                    story_data.epic_domain = story.epic.domain
                board[column].append(story_data)

        # Get WIP limits
        wip_limits = {}
        if project.wip_data:
            for column_name, config in project.wip_data.items():
                wip_limits[column_name] = {
                    "wip_limit": config.get("limit", 10),
                    "limit_type": config.get("type", "hard")
                }

        return {
            "project_id": project_id,
            "project_name": project.name,
            "board": board,
            "wip_limits": wip_limits
        }

    def assign(
        self,
        story_id: UUID,
        assignee_id: UUID,
        user_id: UUID,
        user_name: str,
        reviewer_id: Optional[UUID] = None
    ) -> Story:
        """Assign story to user with activity logging.

        Args:
            story_id: Story UUID
            assignee_id: User to assign to
            user_id: User making the assignment
            user_name: Name for activity log
            reviewer_id: Optional reviewer

        Returns:
            Story: Updated story
        """
        story = self.session.get(Story, story_id)
        if not story:
            raise ValueError("Story not found")

        old_assignee = story.assignee_id
        story.assignee_id = assignee_id
        if reviewer_id:
            story.reviewer_id = reviewer_id

        self.session.add(story)
        self.session.commit()
        self.session.refresh(story)

        # Log activity
        activity = IssueActivity(
            issue_id=story.id,
            actor_id=str(user_id),
            actor_name=user_name,
            assignee_from=str(old_assignee) if old_assignee else None,
            assignee_to=str(assignee_id),
            note="Story assigned by TeamLeader"
        )
        self.session.add(activity)
        self.session.commit()

        return story

    async def update_status_with_validation(
        self,
        story_id: UUID,
        new_status: StoryStatus,
        user_id: UUID,
        user_name: str,
        user_email: str
    ) -> Story:
        """Update story status with WIP validation, workflow policies, and events.

        Args:
            story_id: Story UUID
            new_status: Target status
            user_id: User making the change
            user_name: Name for activity log
            user_email: Email for transition reason

        Returns:
            Story: Updated story

        Raises:
            ValueError: If story/project not found
            PermissionError: If WIP limit exceeded or policy violated
        """
        story = self.session.get(Story, story_id)
        if not story:
            raise ValueError("Story not found")

        old_status = story.status

        # Skip if unchanged
        if old_status == new_status:
            return story

        project = self.session.get(Project, story.project_id)
        if not project:
            raise ValueError("Project not found")

        # Validate WIP limits
        if project.wip_data and new_status.value in project.wip_data:
            wip_config = project.wip_data[new_status.value]
            wip_limit = wip_config.get("limit", 10)
            limit_type = wip_config.get("type", "hard")

            current_count = self.session.exec(
                select(func.count()).select_from(Story).where(
                    and_(
                        Story.project_id == story.project_id,
                        Story.status == new_status,
                        Story.id != story_id
                    )
                )
            ).one()

            if current_count >= wip_limit and limit_type == "hard":
                raise PermissionError({
                    "error": "WIP_LIMIT_EXCEEDED",
                    "message": f"Cannot move to {new_status.value}: WIP limit {wip_limit} exceeded",
                    "column": new_status.value,
                    "current_count": current_count,
                    "wip_limit": wip_limit
                })

        # Validate dependencies - must be completed before moving to InProgress/Review/Done
        # Skip validation for Todo and Archived (archived is for cleanup, not work)
        if new_status in [StoryStatus.IN_PROGRESS, StoryStatus.REVIEW, StoryStatus.DONE]:
            if story.dependencies:
                # Convert string IDs to UUIDs and query incomplete dependencies
                try:
                    dep_uuids = [UUID(d) for d in story.dependencies if d]
                    if dep_uuids:
                        incomplete_deps = self.session.exec(
                            select(Story).where(
                                and_(
                                    Story.id.in_(dep_uuids),
                                    Story.status.not_in([StoryStatus.DONE, StoryStatus.ARCHIVED])
                                )
                            )
                        ).all()
                        
                        if incomplete_deps:
                            raise PermissionError({
                                "error": "DEPENDENCIES_NOT_COMPLETED",
                                "message": f"Cannot move to {new_status.value}: {len(incomplete_deps)} dependencies not completed",
                                "incomplete_dependencies": [
                                    {"id": str(dep.id), "title": dep.title, "status": dep.status.value}
                                    for dep in incomplete_deps
                                ]
                            })
                except (ValueError, AttributeError):
                    # Invalid UUID format in dependencies, skip validation
                    pass

        # Validate workflow policies
        policy = self.session.exec(
            select(WorkflowPolicy).where(
                and_(
                    WorkflowPolicy.project_id == story.project_id,
                    WorkflowPolicy.from_status == old_status.value,
                    WorkflowPolicy.to_status == new_status.value,
                    WorkflowPolicy.is_active == True
                )
            )
        ).first()

        if policy and policy.criteria:
            violations = []
            if policy.criteria.get("assignee_required") and not story.assignee_id:
                violations.append("Story must have an assignee")
            if policy.criteria.get("acceptance_criteria_defined") and not story.acceptance_criteria:
                violations.append("Acceptance criteria must be defined")
            if policy.criteria.get("story_points_estimated") and not story.story_point:
                violations.append("Story points must be estimated")

            if violations:
                raise PermissionError({
                    "error": "POLICY_VIOLATION",
                    "message": "Workflow policy not satisfied",
                    "violations": violations,
                    "policy": {"from": old_status.value, "to": new_status.value}
                })

        # Update status and timestamps
        story.status = new_status
        story.agent_state = None
        now = datetime.now(timezone.utc)

        if new_status == StoryStatus.IN_PROGRESS and not story.started_at:
            story.started_at = now
        elif new_status == StoryStatus.REVIEW and not story.review_started_at:
            story.review_started_at = now
        elif new_status == StoryStatus.DONE and old_status != StoryStatus.DONE:
            story.completed_at = now

        self.session.add(story)
        self.session.commit()
        self.session.refresh(story)

        # Log activity
        activity = IssueActivity(
            issue_id=story.id,
            actor_id=str(user_id),
            actor_name=user_name,
            status_from=old_status.value,
            status_to=new_status.value,
            note=f"Status updated to {new_status.value}"
        )
        self.session.add(activity)
        self.session.commit()

        # Publish Kafka event
        await self._publish_status_changed_event(
            story=story,
            old_status=old_status,
            new_status=new_status,
            user_id=user_id,
            user_email=user_email
        )

        return story

    async def update_with_events(
        self,
        story_id: UUID,
        story_in: StoryUpdate,
        user_id: UUID,
        user_name: str
    ) -> Story:
        """Update story with activity logging and Kafka event.

        Args:
            story_id: Story UUID
            story_in: Update data
            user_id: User making the update
            user_name: Name for activity log

        Returns:
            Story: Updated story with epic info loaded
        """
        from sqlalchemy.orm import selectinload
        
        story = self.session.get(Story, story_id)
        if not story:
            raise ValueError("Story not found")

        update_data = story_in.model_dump(exclude_unset=True)
        story.sqlmodel_update(update_data)
        self.session.add(story)
        self.session.commit()
        
        # Reload story with epic relationship to include epic info in response
        statement = select(Story).where(Story.id == story_id).options(
            selectinload(Story.epic)
        )
        story = self.session.exec(statement).first()

        # Log activity
        activity = IssueActivity(
            issue_id=story.id,
            actor_id=str(user_id),
            actor_name=user_name,
            note="Story updated"
        )
        self.session.add(activity)
        self.session.commit()

        # Publish Kafka event
        await self._publish_story_updated_event(story, update_data, user_id)

        return story

    # ===== Private Kafka Publishing Methods =====

    async def _publish_story_event(
        self,
        event_type: str,
        story: Story,
        user_id: UUID
    ) -> None:
        """Publish story created event to Kafka."""
        try:
            from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent

            producer = await get_kafka_producer()
            await producer.publish(
                topic=KafkaTopics.STORY_EVENTS,
                event=StoryEvent(
                    event_type=event_type,
                    project_id=str(story.project_id),
                    user_id=str(user_id),
                    story_id=story.id,
                    title=story.title,
                    description=story.description,
                    story_type=story.type.value if story.type else "UserStory",
                    status=story.status.value,
                    epic_id=story.epic_id,
                    assignee_id=story.assignee_id,
                    reviewer_id=story.reviewer_id,
                    created_by_agent=None,
                ),
            )
        except Exception as e:
            logger.error(f"Failed to publish {event_type} event: {e}")

    async def _publish_status_changed_event(
        self,
        story: Story,
        old_status: StoryStatus,
        new_status: StoryStatus,
        user_id: UUID,
        user_email: str
    ) -> None:
        """Publish story status changed event to Kafka."""
        try:
            from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent

            producer = await get_kafka_producer()
            await producer.publish(
                topic=KafkaTopics.STORY_EVENTS,
                event=StoryEvent(
                    event_type="story.status.changed",
                    project_id=str(story.project_id),
                    user_id=str(user_id),
                    story_id=story.id,
                    old_status=old_status.value,
                    new_status=new_status.value,
                    changed_by=str(user_id),
                    transition_reason=f"Updated by {user_email}",
                ),
            )
        except Exception as e:
            logger.error(f"Failed to publish status changed event: {e}")

    async def _publish_story_updated_event(
        self,
        story: Story,
        update_data: Dict[str, Any],
        user_id: UUID
    ) -> None:
        """Publish story updated event to Kafka."""
        try:
            from app.kafka import get_kafka_producer, KafkaTopics, StoryEvent

            producer = await get_kafka_producer()
            await producer.publish(
                topic=KafkaTopics.STORY_EVENTS,
                event=StoryEvent(
                    event_type="story.updated",
                    project_id=str(story.project_id),
                    user_id=str(user_id),
                    story_id=story.id,
                    updated_fields=update_data,
                    updated_by=str(user_id),
                ),
            )
        except Exception as e:
            logger.error(f"Failed to publish story updated event: {e}")