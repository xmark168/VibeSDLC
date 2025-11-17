"""
CrewAI API Endpoints

Provides REST API for interacting with the multi-agent system
"""

from uuid import UUID
from typing import Any
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from app.crews.flows import create_development_flow


router = APIRouter(prefix="/crews", tags=["crews"])


# Request/Response Models
class CreateTaskRequest(BaseModel):
    """Request to create a new task"""
    project_id: UUID
    feature_description: str


class TaskResponse(BaseModel):
    """Response with task details"""
    flow_id: str
    project_id: UUID
    feature_description: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    requirements: dict[str, Any] | None = None
    implementation: dict[str, Any] | None = None
    test_results: dict[str, Any] | None = None
    final_review: dict[str, Any] | None = None


# In-memory storage for flows (replace with Redis/DB in production)
_active_flows: dict[str, Any] = {}


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    # current_user: User = Depends(get_current_user)  # Add auth when ready
):
    """
    Create a new development task

    Starts a development flow with the multi-agent system

    Args:
        request: Task creation request
        background_tasks: FastAPI background tasks

    Returns:
        TaskResponse with flow details
    """
    # For now, use a placeholder user ID
    # In production, get from current_user
    triggered_by = "system"  # current_user.id

    # Create flow
    flow = await create_development_flow(
        project_id=request.project_id,
        feature_description=request.feature_description,
        triggered_by=triggered_by,
    )

    # Store flow
    _active_flows[flow.state.flow_id] = flow

    # Execute flow in background
    async def run_flow():
        """Run the flow asynchronously"""
        try:
            await flow.kickoff()
        except Exception as e:
            print(f"Error running flow {flow.state.flow_id}: {e}")
            flow.state.status = "failed"

    background_tasks.add_task(run_flow)

    # Return response
    return TaskResponse(
        flow_id=flow.state.flow_id,
        project_id=flow.state.project_id,
        feature_description=flow.state.feature_description,
        status=flow.state.status,
        started_at=flow.state.started_at,
        completed_at=flow.state.completed_at,
    )


@router.get("/tasks/{flow_id}", response_model=TaskResponse)
async def get_task_status(flow_id: str):
    """
    Get status of a development task

    Args:
        flow_id: Flow ID

    Returns:
        TaskResponse with current status
    """
    flow = _active_flows.get(flow_id)

    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {flow_id} not found"
        )

    return TaskResponse(
        flow_id=flow.state.flow_id,
        project_id=flow.state.project_id,
        feature_description=flow.state.feature_description,
        status=flow.state.status,
        started_at=flow.state.started_at,
        completed_at=flow.state.completed_at,
        requirements=flow.state.requirements,
        implementation=flow.state.implementation,
        test_results=flow.state.test_results,
        final_review=flow.state.final_review,
    )


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks():
    """
    List all tasks

    Returns:
        List of all tasks
    """
    tasks = []

    for flow in _active_flows.values():
        tasks.append(TaskResponse(
            flow_id=flow.state.flow_id,
            project_id=flow.state.project_id,
            feature_description=flow.state.feature_description,
            status=flow.state.status,
            started_at=flow.state.started_at,
            completed_at=flow.state.completed_at,
            requirements=flow.state.requirements,
            implementation=flow.state.implementation,
            test_results=flow.state.test_results,
            final_review=flow.state.final_review,
        ))

    return tasks
