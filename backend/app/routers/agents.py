"""
Agent Router - API endpoints for agent management
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models import User
from app.services.agent_service import AgentService
from app.kanban_schemas import AgentCreate, AgentUpdate, AgentResponse, StoryResponse
from app.enums import AgentType


router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create agent"
)
async def create_agent(
    data: AgentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new AI agent

    **Authorization**: Project owner only

    - **project_id**: Project this agent belongs to
    - **name**: Unique agent name
    - **type**: Agent type (FLOW_MANAGER, BUSINESS_ANALYST, DEVELOPER, TESTER)
    - **description**: Optional description
    - **is_active**: Whether agent is active

    Returns the created agent
    """
    agent = await AgentService.create(data, current_user, db)
    return agent


@router.get(
    "",
    response_model=List[AgentResponse],
    summary="List agents"
)
async def list_agents(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    agent_type: Optional[AgentType] = Query(None, description="Filter by agent type"),
    active_only: bool = Query(False, description="Only return active agents"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of agents

    **Filters**:
    - **project_id**: Filter agents by project
    - **agent_type**: Filter by agent type
    - **active_only**: Only return active agents

    Returns list of agents
    """
    if project_id:
        agents = await AgentService.get_by_project(
            project_id, db, agent_type, active_only
        )
    else:
        # If no project_id, this should list all agents (or return error)
        # For now, require project_id
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id query parameter is required"
        )

    return agents


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent by ID"
)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific agent by ID

    Returns agent details
    """
    agent = await AgentService.get_by_id(agent_id, db)
    return agent


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent"
)
async def update_agent(
    agent_id: int,
    data: AgentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an agent

    **Authorization**: Project owner only

    - **name**: Update name (must be unique)
    - **type**: Update agent type
    - **description**: Update description
    - **is_active**: Update active status
    - **project_id**: Move agent to different project (must own both projects)

    Returns updated agent
    """
    agent = await AgentService.update(agent_id, data, current_user, db)
    return agent


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agent"
)
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete an agent

    **Authorization**: Project owner only

    The agent will be marked as deleted but not removed from database.
    All story assignments will be cascaded deleted.
    """
    await AgentService.delete(agent_id, current_user, db)


@router.get(
    "/{agent_id}/workload",
    summary="Get agent workload"
)
async def get_agent_workload(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get agent workload statistics

    Returns:
    - Total number of assigned stories
    - Stories count by status

    Useful for load balancing and capacity planning
    """
    workload = await AgentService.get_workload(agent_id, db)
    return workload


@router.get(
    "/{agent_id}/stories",
    response_model=List[StoryResponse],
    summary="Get agent's assigned stories"
)
async def get_agent_stories(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all stories assigned to this agent

    Returns list of stories ordered by creation date (newest first)
    """
    stories = await AgentService.get_assigned_stories(agent_id, db)
    return stories
