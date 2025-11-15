"""
Agent Service - Business logic for agent management
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models import Agent, User, StoryAgentAssignment, Story
from app.kanban_schemas import AgentCreate, AgentUpdate, AgentResponse
from app.dependencies import get_project_or_404, verify_project_owner
from app.enums import AgentType


class AgentService:
    """Service for managing AI agents"""

    @staticmethod
    async def create(data: AgentCreate, current_user: User, db: AsyncSession) -> Agent:
        """
        Create a new agent

        Args:
            data: Agent creation data
            current_user: Current authenticated user
            db: Database session

        Returns:
            Created agent

        Raises:
            HTTPException: 403 if user is not project owner
            HTTPException: 400 if agent name already exists
            HTTPException: 404 if project not found
        """
        # 1. Verify project exists and user is owner
        project = await get_project_or_404(data.project_id, db)
        await verify_project_owner(project, current_user)

        # 2. Check if agent with same name already exists in this project
        stmt = select(Agent).where(
            Agent.project_id == data.project_id,
            Agent.name == data.name,
            Agent.deleted_at == None
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent with name '{data.name}' already exists in this project"
            )

        # 3. Create agent
        agent = Agent(**data.model_dump())
        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        return agent

    @staticmethod
    async def get_by_project(
        project_id: int,
        db: AsyncSession,
        agent_type: Optional[AgentType] = None,
        active_only: bool = False
    ) -> List[Agent]:
        """
        Get agents by project

        Args:
            project_id: Project ID
            db: Database session
            agent_type: Filter by agent type (optional)
            active_only: Only return active agents

        Returns:
            List of agents
        """
        stmt = select(Agent).where(
            Agent.project_id == project_id,
            Agent.deleted_at == None
        )

        if agent_type:
            stmt = stmt.where(Agent.type == agent_type)

        if active_only:
            stmt = stmt.where(Agent.is_active == True)

        result = await db.execute(stmt)
        agents = result.scalars().all()
        return agents

    @staticmethod
    async def get_by_id(agent_id: int, db: AsyncSession) -> Agent:
        """
        Get agent by ID

        Args:
            agent_id: Agent ID
            db: Database session

        Returns:
            Agent

        Raises:
            HTTPException: 404 if not found
        """
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
        return agent

    @staticmethod
    async def update(
        agent_id: int,
        data: AgentUpdate,
        current_user: User,
        db: AsyncSession
    ) -> Agent:
        """
        Update agent

        Args:
            agent_id: Agent ID
            data: Update data
            current_user: Current authenticated user
            db: Database session

        Returns:
            Updated agent

        Raises:
            HTTPException: 404 if not found
            HTTPException: 403 if user is not project owner
            HTTPException: 400 if name conflict
        """
        # 1. Get existing agent
        agent = await AgentService.get_by_id(agent_id, db)

        # 2. Verify project ownership
        project = await get_project_or_404(agent.project_id, db)
        await verify_project_owner(project, current_user)

        # 3. Check name conflict if name is being changed
        if data.name and data.name != agent.name:
            stmt = select(Agent).where(
                Agent.project_id == agent.project_id,
                Agent.name == data.name,
                Agent.deleted_at == None
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Agent with name '{data.name}' already exists in this project"
                )

        # 4. If changing project_id, verify new project ownership
        if data.project_id and data.project_id != agent.project_id:
            new_project = await get_project_or_404(data.project_id, db)
            await verify_project_owner(new_project, current_user)

        # 5. Update agent
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(agent, key, value)
        await db.commit()
        await db.refresh(agent)

        return agent

    @staticmethod
    async def delete(agent_id: int, current_user: User, db: AsyncSession) -> None:
        """
        Soft delete agent

        Args:
            agent_id: Agent ID
            current_user: Current authenticated user
            db: Database session

        Raises:
            HTTPException: 404 if not found
            HTTPException: 403 if user is not project owner
        """
        # 1. Get existing agent
        agent = await AgentService.get_by_id(agent_id, db)

        # 2. Verify project ownership
        project = await get_project_or_404(agent.project_id, db)
        await verify_project_owner(project, current_user)

        # 3. Soft delete (set deleted_at)
        agent.deleted_at = datetime.utcnow()
        await db.commit()

    @staticmethod
    async def get_workload(agent_id: int, db: AsyncSession) -> dict:
        """
        Get agent workload statistics

        Args:
            agent_id: Agent ID
            db: Database session

        Returns:
            Dictionary with workload stats including capacity information

        Raises:
            HTTPException: 404 if agent not found
        """
        # Verify agent exists
        agent = await AgentService.get_by_id(agent_id, db)

        # Count stories by status
        query = (
            select(Story.status, func.count(Story.id))
            .join(StoryAgentAssignment, Story.id == StoryAgentAssignment.story_id)
            .where(
                StoryAgentAssignment.agent_id == agent_id,
                Story.deleted_at == None
            )
            .group_by(Story.status)
        )

        result = await db.execute(query)
        workload_by_status = {row[0]: row[1] for row in result}

        # Calculate total
        total_stories = sum(workload_by_status.values())

        # Calculate available capacity
        available_capacity = None
        if agent.capacity is not None:
            available_capacity = agent.capacity - total_stories

        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "capacity": agent.capacity,
            "total_stories": total_stories,
            "available_capacity": available_capacity,
            "by_status": workload_by_status
        }

    @staticmethod
    async def validate_capacity(agent_id: int, db: AsyncSession) -> bool:
        """
        Validate if agent has capacity for new assignment

        Args:
            agent_id: Agent ID
            db: Database session

        Returns:
            True if agent has capacity or no capacity limit set

        Raises:
            HTTPException: 400 if agent has reached capacity
            HTTPException: 404 if agent not found
        """
        agent = await AgentService.get_by_id(agent_id, db)

        # If no capacity limit, always allow
        if agent.capacity is None:
            return True

        # Count current assignments
        query = (
            select(func.count(StoryAgentAssignment.id))
            .join(Story, Story.id == StoryAgentAssignment.story_id)
            .where(
                StoryAgentAssignment.agent_id == agent_id,
                Story.deleted_at == None
            )
        )

        result = await db.execute(query)
        current_count = result.scalar() or 0

        if current_count >= agent.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent '{agent.name}' has reached maximum capacity ({current_count}/{agent.capacity} stories)"
            )

        return True

    @staticmethod
    async def get_assigned_stories(agent_id: int, db: AsyncSession) -> List[Story]:
        """
        Get all stories assigned to agent

        Args:
            agent_id: Agent ID
            db: Database session

        Returns:
            List of stories

        Raises:
            HTTPException: 404 if agent not found
        """
        # Verify agent exists
        await AgentService.get_by_id(agent_id, db)

        # Get stories
        query = (
            select(Story)
            .join(StoryAgentAssignment, Story.id == StoryAgentAssignment.story_id)
            .where(
                StoryAgentAssignment.agent_id == agent_id,
                Story.deleted_at == None
            )
            .order_by(Story.created_at.desc())
        )

        result = await db.execute(query)
        stories = result.scalars().all()

        return list(stories)
