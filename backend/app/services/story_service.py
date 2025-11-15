"""
Story Service - Business logic for story and Kanban workflow management

This is the core of the Lean Kanban system, implementing:
- Story CRUD operations
- Status transitions with WIP limit validation
- Workflow rules enforcement
- Blocking/unblocking stories
- Agent assignments
- Status history tracking
- Cycle time calculations
"""
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from fastapi import HTTPException, status

from app.models import Story, User, StoryAgentAssignment, StoryStatusHistory, Agent, Epic, Project
from app.kanban_schemas import StoryCreate, StoryUpdate, StoryCreateInternal, StatusHistoryCreate, AssignmentCreate, AgentResponse, AssignmentResponse
from app.dependencies import get_story_with_project, get_epic_with_project, get_project_or_404, verify_project_owner
from app.enums import StoryStatus, StoryType, StoryPriority
from app.services.project_service import DEFAULT_KANBAN_POLICY
from app.kafka.producer import kafka_producer
from app.kafka.schemas import StoryEvent


class StoryService:
    """Service for managing stories and Kanban workflow"""

    # ==================== BASIC CRUD ====================

    @staticmethod
    async def create(data: StoryCreate, current_user: User, db: AsyncSession) -> Story:
        """Create a new story"""
        # 1. Get epic with project
        epic, project = await get_epic_with_project(data.epic_id, db)

        # 2. Verify project ownership
        await verify_project_owner(project, current_user)

        # 3. Create story
        story = Story(
            title=data.title,
            description=data.description,
            epic_id=data.epic_id,
            type=data.type,
            priority=data.priority,
            acceptance_criteria=data.acceptance_criteria,
            status=StoryStatus.TODO,
            created_by_id=current_user.id
        )
        db.add(story)
        await db.commit()
        await db.refresh(story)

        # 4. Create initial status history record
        history = StoryStatusHistory(
            story_id=story.id,
            old_status=None,
            new_status=StoryStatus.TODO,
            changed_by_id=current_user.id
        )
        db.add(history)
        await db.commit()

        return story

    @staticmethod
    async def get_by_epic(
        epic_id: int,
        db: AsyncSession,
        status_filter: Optional[StoryStatus] = None
    ) -> List[Story]:
        """Get stories by epic"""
        stmt = select(Story).where(
            Story.epic_id == epic_id,
            Story.deleted_at == None
        )
        if status_filter:
            stmt = stmt.where(Story.status == status_filter)

        result = await db.execute(stmt)
        stories = result.scalars().all()
        return list(stories)

    @staticmethod
    async def get_by_id(story_id: int, db: AsyncSession) -> Story:
        """Get story by ID"""
        story, _ = await get_story_with_project(story_id, db)
        return story

    @staticmethod
    async def update(
        story_id: int,
        data: StoryUpdate,
        current_user: User,
        db: AsyncSession
    ) -> Story:
        """Update story (non-status fields only)"""
        # 1. Get story with project
        story, project = await get_story_with_project(story_id, db)

        # 2. Verify project ownership
        await verify_project_owner(project, current_user)

        # 3. Update story
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(story, key, value)
        await db.commit()
        await db.refresh(story)

        return story

    @staticmethod
    async def delete(story_id: int, current_user: User, db: AsyncSession) -> None:
        """Soft delete story"""
        # 1. Get story with project
        story, project = await get_story_with_project(story_id, db)

        # 2. Verify project ownership
        await verify_project_owner(project, current_user)

        # 3. Soft delete
        story.deleted_at = datetime.utcnow()
        await db.commit()

    # ==================== KANBAN WORKFLOW ====================

    @staticmethod
    async def move_status(
        story_id: int,
        new_status: StoryStatus,
        current_user: User,
        db: AsyncSession
    ) -> Story:
        """
        Move story to new status with Lean Kanban validations

        This implements core Kanban principles:
        - Workflow rules validation
        - WIP limit enforcement
        - Completion requirements
        """
        # 1. Get story with project
        story, project = await get_story_with_project(story_id, db)

        # 2. Verify project ownership
        await verify_project_owner(project, current_user)

        # 3. Get kanban policy
        policy = project.kanban_policy or DEFAULT_KANBAN_POLICY

        # 4. Validate transition is allowed
        allowed_transitions = policy["workflow_rules"]["allowed_transitions"]
        allowed = allowed_transitions.get(story.status, [])

        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from {story.status} to {new_status}. Allowed transitions: {allowed}"
            )

        # 5. Check WIP limits (skip for BLOCKED, DONE, ARCHIVED)
        if new_status not in [StoryStatus.BLOCKED, StoryStatus.DONE, StoryStatus.ARCHIVED]:
            await StoryService._check_wip_limit(project, new_status, policy, db)

        # 6. Validate completion requirements (if moving to DONE)
        if new_status == StoryStatus.DONE:
            await StoryService._validate_completion(story, policy)

        # 7. Update story
        old_status = story.status
        story.status = new_status

        if new_status == StoryStatus.DONE:
            story.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(story)

        # 8. Create status history record
        history = StoryStatusHistory(
            story_id=story_id,
            old_status=old_status,
            new_status=new_status,
            changed_by_id=current_user.id
        )
        db.add(history)
        await db.commit()

        # 9. Send Kafka event to trigger agents
        event = StoryEvent(
            event_type="status_changed",
            story_id=story.id,
            project_id=project.id,
            epic_id=story.epic_id,
            changes={"old_status": old_status, "new_status": new_status},
            triggered_by=current_user.id,
            timestamp=datetime.utcnow()
        )
        kafka_producer.send_story_event(event)

        return story

    @staticmethod
    async def _check_wip_limit(
        project: Project,
        target_status: StoryStatus,
        policy: dict,
        db: AsyncSession
    ) -> None:
        """Check if WIP limit would be exceeded"""
        # Find column config
        columns = policy.get("columns", [])
        column = next((c for c in columns if c["status"] == target_status), None)

        if not column or column.get("wip_limit") is None:
            return  # No WIP limit

        wip_limit = column["wip_limit"]

        # Count current stories in this status (via project's epics)
        query = (
            select(func.count(Story.id))
            .join(Epic, Story.epic_id == Epic.id)
            .where(
                and_(
                    Epic.project_id == project.id,
                    Story.status == target_status,
                    Story.deleted_at == None,
                    Epic.deleted_at == None
                )
            )
        )

        result = await db.execute(query)
        current_count = result.scalar()

        if current_count >= wip_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"WIP limit reached for {target_status}. Limit: {wip_limit}, Current: {current_count}"
            )

    @staticmethod
    async def _validate_completion(story: Story, policy: dict) -> None:
        """Validate story meets completion requirements"""
        requirements = policy.get("workflow_rules", {}).get("completion_requirements", {})

        # Check acceptance criteria
        if requirements.get("acceptance_criteria_required") and not story.acceptance_criteria:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Acceptance criteria is required before marking story as DONE"
            )

        # Check min agents assigned
        min_agents = requirements.get("min_agents_assigned", 0)
        if min_agents > 0:
            agent_count = len(story.agent_assignments)
            if agent_count < min_agents:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"At least {min_agents} agent(s) must be assigned before marking as DONE"
                )

    # ==================== AGENT ASSIGNMENTS ====================

    @staticmethod
    async def assign_agent(
        story_id: int,
        agent_id: int,
        role: Optional[str],
        current_user: User,
        db: AsyncSession
    ) -> StoryAgentAssignment:
        """Assign agent to story"""
        # 1. Get story with project
        story, project = await get_story_with_project(story_id, db)

        # 2. Verify project ownership
        await verify_project_owner(project, current_user)

        # 3. Get agent and verify same project
        stmt = select(Agent).where(
            Agent.id == agent_id,
            Agent.deleted_at == None
        )
        result = await db.execute(stmt)
        agent = result.scalar_one_or_none()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )

        if agent.project_id != project.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent must belong to the same project as the story"
            )

        # 4. Check if agent is active
        if not agent.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign inactive agent"
            )

        # 4.5 Validate agent capacity
        from app.services.agent_service import AgentService
        await AgentService.validate_capacity(agent_id, db)

        # 5. Check not already assigned
        stmt = select(StoryAgentAssignment).where(
            StoryAgentAssignment.story_id == story_id,
            StoryAgentAssignment.agent_id == agent_id
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent is already assigned to this story"
            )

        # 6. Create assignment
        assignment = StoryAgentAssignment(
            story_id=story_id,
            agent_id=agent_id,
            role=role
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

        return assignment

    @staticmethod
    async def unassign_agent(
        story_id: int,
        agent_id: int,
        current_user: User,
        db: AsyncSession
    ) -> None:
        """Remove agent assignment"""
        # 1. Get story with project
        story, project = await get_story_with_project(story_id, db)

        # 2. Verify project ownership
        await verify_project_owner(project, current_user)

        # 3. Find and delete assignment
        stmt = select(StoryAgentAssignment).where(
            StoryAgentAssignment.story_id == story_id,
            StoryAgentAssignment.agent_id == agent_id
        )
        result = await db.execute(stmt)
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )

        await db.delete(assignment)
        await db.commit()

    # ==================== STATUS HISTORY & METRICS ====================

    @staticmethod
    async def get_status_history(story_id: int, db: AsyncSession) -> List[StoryStatusHistory]:
        """Get status change history"""
        # Verify story exists
        await StoryService.get_by_id(story_id, db)

        # Get history ordered by time
        query = (
            select(StoryStatusHistory)
            .where(StoryStatusHistory.story_id == story_id)
            .order_by(StoryStatusHistory.changed_at.asc())
        )

        result = await db.execute(query)
        history = result.scalars().all()

        return list(history)

    @staticmethod
    async def calculate_cycle_time(story_id: int, db: AsyncSession) -> Optional[dict]:
        """
        Calculate cycle time (first IN_PROGRESS to DONE)

        Cycle time measures the time from when work starts to when it's completed
        """
        # Get status history
        history = await StoryService.get_status_history(story_id, db)

        # Find first IN_PROGRESS
        first_in_progress = next(
            (h for h in history if h.new_status == StoryStatus.IN_PROGRESS),
            None
        )

        # Find first DONE
        first_done = next(
            (h for h in history if h.new_status == StoryStatus.DONE),
            None
        )

        if not first_in_progress or not first_done:
            return None  # Cycle not complete

        # Calculate difference in hours
        cycle_time_seconds = (first_done.changed_at - first_in_progress.changed_at).total_seconds()
        cycle_time_hours = cycle_time_seconds / 3600

        return {
            "story_id": story_id,
            "started_at": first_in_progress.changed_at,
            "completed_at": first_done.changed_at,
            "cycle_time_hours": round(cycle_time_hours, 2)
        }
