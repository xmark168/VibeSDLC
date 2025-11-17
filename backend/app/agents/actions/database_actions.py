"""Database actions for agents to interact with the database.

These actions wrap database operations in agent-friendly interfaces,
allowing agents to create/update stories, epics, and other entities.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.models import (
    AgentExecution,
    AgentExecutionStatus,
    ApprovalRequest,
    ApprovalStatus,
    Epic,
    Project,
    Story,
    StoryStatus,
    StoryType,
    User,
)

logger = logging.getLogger(__name__)


class DatabaseActions:
    """Database actions for agents to perform CRUD operations"""

    def __init__(self, session: Session):
        """Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self.session = session

    # ==================== STORY ACTIONS ====================

    def create_story(
        self,
        project_id: UUID,
        title: str,
        description: Optional[str] = None,
        story_type: StoryType = StoryType.USER_STORY,
        status: StoryStatus = StoryStatus.TODO,
        epic_id: Optional[UUID] = None,
        acceptance_criteria: Optional[str] = None,
        assignee_id: Optional[UUID] = None,
        reviewer_id: Optional[UUID] = None,
        story_point: Optional[int] = None,
        priority: Optional[int] = None,
        created_by_agent: Optional[str] = None,
        **kwargs,
    ) -> Story:
        """Create a new story in the database.

        Args:
            project_id: Project UUID
            title: Story title
            description: Story description
            story_type: UserStory or EnablerStory
            status: Initial status (defaults to Todo)
            epic_id: Optional epic to link to
            acceptance_criteria: Acceptance criteria text
            assignee_id: User assigned to implement
            reviewer_id: User assigned to review
            story_point: Estimation points
            priority: Priority ranking
            created_by_agent: Name of agent that created this
            **kwargs: Additional fields

        Returns:
            Created Story instance
        """
        # Auto-calculate rank (max + 1)
        stmt = select(Story).where(Story.project_id == project_id)
        stories = self.session.exec(stmt).all()
        max_rank = max([s.rank for s in stories if s.rank], default=0)

        story = Story(
            project_id=project_id,
            title=title,
            description=description,
            type=story_type,
            status=status,
            epic_id=epic_id,
            acceptance_criteria=acceptance_criteria,
            assignee_id=assignee_id,
            reviewer_id=reviewer_id,
            story_point=story_point,
            priority=priority,
            rank=max_rank + 1,
            **kwargs,
        )

        self.session.add(story)
        self.session.commit()
        self.session.refresh(story)

        logger.info(
            f"Created story {story.id} in project {project_id} "
            f"by agent: {created_by_agent or 'unknown'}"
        )

        return story

    def update_story(
        self,
        story_id: UUID,
        updates: Dict[str, Any],
    ) -> Optional[Story]:
        """Update an existing story.

        Args:
            story_id: Story UUID
            updates: Dict of field updates

        Returns:
            Updated Story instance or None if not found
        """
        story = self.session.get(Story, story_id)
        if not story:
            logger.warning(f"Story {story_id} not found for update")
            return None

        # Apply updates
        for field, value in updates.items():
            if hasattr(story, field):
                setattr(story, field, value)

        self.session.add(story)
        self.session.commit()
        self.session.refresh(story)

        logger.info(f"Updated story {story_id} with fields: {list(updates.keys())}")

        return story

    def transition_story_status(
        self,
        story_id: UUID,
        new_status: StoryStatus,
        changed_by: str,
    ) -> Optional[Story]:
        """Transition story to a new status.

        Args:
            story_id: Story UUID
            new_status: Target status
            changed_by: User/agent making the change

        Returns:
            Updated Story instance or None if not found
        """
        story = self.session.get(Story, story_id)
        if not story:
            logger.warning(f"Story {story_id} not found for status transition")
            return None

        old_status = story.status
        story.status = new_status

        # Set completed_at when moving to Done
        if new_status == StoryStatus.DONE and not story.completed_at:
            story.completed_at = datetime.now(timezone.utc)

        self.session.add(story)
        self.session.commit()
        self.session.refresh(story)

        logger.info(
            f"Transitioned story {story_id} from {old_status} to {new_status} "
            f"by {changed_by}"
        )

        return story

    def assign_story(
        self,
        story_id: UUID,
        assignee_id: Optional[UUID] = None,
        reviewer_id: Optional[UUID] = None,
        assigned_by: Optional[str] = None,
    ) -> Optional[Story]:
        """Assign a story to users.

        Args:
            story_id: Story UUID
            assignee_id: User to assign implementation
            reviewer_id: User to assign review
            assigned_by: Agent/user making the assignment

        Returns:
            Updated Story instance or None if not found
        """
        story = self.session.get(Story, story_id)
        if not story:
            logger.warning(f"Story {story_id} not found for assignment")
            return None

        if assignee_id is not None:
            story.assignee_id = assignee_id
        if reviewer_id is not None:
            story.reviewer_id = reviewer_id

        self.session.add(story)
        self.session.commit()
        self.session.refresh(story)

        logger.info(
            f"Assigned story {story_id} - assignee: {assignee_id}, "
            f"reviewer: {reviewer_id} by {assigned_by or 'unknown'}"
        )

        return story

    def get_story(self, story_id: UUID) -> Optional[Story]:
        """Get a story by ID.

        Args:
            story_id: Story UUID

        Returns:
            Story instance or None if not found
        """
        return self.session.get(Story, story_id)

    def get_stories_by_project(
        self,
        project_id: UUID,
        status: Optional[StoryStatus] = None,
    ) -> list[Story]:
        """Get all stories for a project, optionally filtered by status.

        Args:
            project_id: Project UUID
            status: Optional status filter

        Returns:
            List of Story instances
        """
        stmt = select(Story).where(Story.project_id == project_id)
        if status:
            stmt = stmt.where(Story.status == status)

        stmt = stmt.order_by(Story.rank)
        return list(self.session.exec(stmt).all())

    # ==================== EPIC ACTIONS ====================

    def create_epic(
        self,
        project_id: UUID,
        title: str,
        description: Optional[str] = None,
    ) -> Epic:
        """Create a new epic.

        Args:
            project_id: Project UUID
            title: Epic title
            description: Epic description

        Returns:
            Created Epic instance
        """
        epic = Epic(
            project_id=project_id,
            title=title,
            description=description,
        )

        self.session.add(epic)
        self.session.commit()
        self.session.refresh(epic)

        logger.info(f"Created epic {epic.id} in project {project_id}")

        return epic

    def get_epic(self, epic_id: UUID) -> Optional[Epic]:
        """Get an epic by ID.

        Args:
            epic_id: Epic UUID

        Returns:
            Epic instance or None if not found
        """
        return self.session.get(Epic, epic_id)

    def get_epics_by_project(self, project_id: UUID) -> list[Epic]:
        """Get all epics for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of Epic instances
        """
        stmt = select(Epic).where(Epic.project_id == project_id)
        return list(self.session.exec(stmt).all())

    # ==================== AGENT EXECUTION TRACKING ====================

    def create_agent_execution(
        self,
        project_id: UUID,
        agent_name: str,
        agent_type: str,
        trigger_message_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> AgentExecution:
        """Create a new agent execution record.

        Args:
            project_id: Project UUID
            agent_name: Name of the agent
            agent_type: Type of agent (TeamLeader, BusinessAnalyst, etc.)
            trigger_message_id: Message that triggered this execution
            user_id: User who triggered this (if applicable)

        Returns:
            Created AgentExecution instance
        """
        execution = AgentExecution(
            project_id=project_id,
            agent_name=agent_name,
            agent_type=agent_type,
            status=AgentExecutionStatus.PENDING,
            trigger_message_id=trigger_message_id,
            user_id=user_id,
        )

        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)

        logger.info(f"Created agent execution {execution.id} for {agent_name}")

        return execution

    def update_agent_execution(
        self,
        execution_id: UUID,
        status: Optional[AgentExecutionStatus] = None,
        token_used: Optional[int] = None,
        llm_calls: Optional[int] = None,
        error_message: Optional[str] = None,
        error_traceback: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentExecution]:
        """Update an agent execution record.

        Args:
            execution_id: Execution UUID
            status: New status
            token_used: Total tokens used
            llm_calls: Number of LLM calls
            error_message: Error message if failed
            error_traceback: Error traceback if failed
            result: Execution result

        Returns:
            Updated AgentExecution instance or None if not found
        """
        execution = self.session.get(AgentExecution, execution_id)
        if not execution:
            logger.warning(f"Agent execution {execution_id} not found")
            return None

        if status:
            execution.status = status

            # Set timestamps based on status
            if status == AgentExecutionStatus.RUNNING and not execution.started_at:
                execution.started_at = datetime.now(timezone.utc)
            elif status in [AgentExecutionStatus.COMPLETED, AgentExecutionStatus.FAILED]:
                execution.completed_at = datetime.now(timezone.utc)
                if execution.started_at:
                    # Ensure started_at is timezone-aware
                    if execution.started_at.tzinfo is None:
                        execution.started_at = execution.started_at.replace(tzinfo=timezone.utc)
                    execution.duration_ms = int(
                        (execution.completed_at - execution.started_at).total_seconds() * 1000
                    )

        if token_used is not None:
            execution.token_used += token_used
        if llm_calls is not None:
            execution.llm_calls += llm_calls
        if error_message:
            execution.error_message = error_message
        if error_traceback:
            execution.error_traceback = error_traceback
        if result:
            execution.result = result

        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)

        logger.debug(f"Updated agent execution {execution_id} status: {status}")

        return execution

    # ==================== APPROVAL ACTIONS ====================

    def create_approval_request(
        self,
        project_id: UUID,
        request_type: str,
        agent_name: str,
        proposed_data: Dict[str, Any],
        preview_data: Optional[Dict[str, Any]] = None,
        explanation: Optional[str] = None,
        execution_id: Optional[UUID] = None,
    ) -> ApprovalRequest:
        """Create a new approval request.

        Args:
            project_id: Project UUID
            request_type: Type of request (story_creation, etc.)
            agent_name: Agent requesting approval
            proposed_data: Proposed changes
            preview_data: Preview for UI
            explanation: Explanation for the request
            execution_id: Associated execution ID

        Returns:
            Created ApprovalRequest instance
        """
        approval = ApprovalRequest(
            project_id=project_id,
            execution_id=execution_id,
            request_type=request_type,
            agent_name=agent_name,
            proposed_data=proposed_data,
            preview_data=preview_data,
            explanation=explanation,
            status=ApprovalStatus.PENDING,
        )

        self.session.add(approval)
        self.session.commit()
        self.session.refresh(approval)

        logger.info(
            f"Created approval request {approval.id} from {agent_name} "
            f"for {request_type}"
        )

        return approval

    def approve_request(
        self,
        approval_id: UUID,
        user_id: UUID,
        user_feedback: Optional[str] = None,
        modified_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[ApprovalRequest]:
        """Approve a request.

        Args:
            approval_id: Approval request UUID
            user_id: User approving the request
            user_feedback: Optional feedback from user
            modified_data: Optional modifications to proposed data

        Returns:
            Updated ApprovalRequest or None if not found
        """
        approval = self.session.get(ApprovalRequest, approval_id)
        if not approval:
            logger.warning(f"Approval request {approval_id} not found")
            return None

        approval.status = ApprovalStatus.APPROVED
        approval.approved_by_user_id = user_id
        approval.approved_at = datetime.now(timezone.utc)
        approval.user_feedback = user_feedback
        approval.modified_data = modified_data

        self.session.add(approval)
        self.session.commit()
        self.session.refresh(approval)

        logger.info(f"Approved request {approval_id} by user {user_id}")

        return approval

    def reject_request(
        self,
        approval_id: UUID,
        user_id: UUID,
        user_feedback: Optional[str] = None,
    ) -> Optional[ApprovalRequest]:
        """Reject a request.

        Args:
            approval_id: Approval request UUID
            user_id: User rejecting the request
            user_feedback: Feedback explaining rejection

        Returns:
            Updated ApprovalRequest or None if not found
        """
        approval = self.session.get(ApprovalRequest, approval_id)
        if not approval:
            logger.warning(f"Approval request {approval_id} not found")
            return None

        approval.status = ApprovalStatus.REJECTED
        approval.approved_by_user_id = user_id
        approval.approved_at = datetime.now(timezone.utc)
        approval.user_feedback = user_feedback

        self.session.add(approval)
        self.session.commit()
        self.session.refresh(approval)

        logger.info(f"Rejected request {approval_id} by user {user_id}")

        return approval

    def mark_approval_applied(
        self,
        approval_id: UUID,
        created_entity_id: Optional[UUID] = None,
    ) -> Optional[ApprovalRequest]:
        """Mark an approval as applied.

        Args:
            approval_id: Approval request UUID
            created_entity_id: ID of created entity (Story/Epic)

        Returns:
            Updated ApprovalRequest or None if not found
        """
        approval = self.session.get(ApprovalRequest, approval_id)
        if not approval:
            logger.warning(f"Approval request {approval_id} not found")
            return None

        approval.applied = True
        approval.applied_at = datetime.now(timezone.utc)
        approval.created_entity_id = created_entity_id

        self.session.add(approval)
        self.session.commit()
        self.session.refresh(approval)

        logger.info(
            f"Marked approval {approval_id} as applied - "
            f"created entity: {created_entity_id}"
        )

        return approval

    # ==================== UTILITY ACTIONS ====================

    def get_project(self, project_id: UUID) -> Optional[Project]:
        """Get a project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project instance or None if not found
        """
        return self.session.get(Project, project_id)

    def get_user(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: User UUID

        Returns:
            User instance or None if not found
        """
        return self.session.get(User, user_id)
