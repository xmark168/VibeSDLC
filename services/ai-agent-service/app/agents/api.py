"""API endpoints for AI Agent Service."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.task_agent import TaskAgent

logger = logging.getLogger(__name__)

router = APIRouter()
task_agent = TaskAgent()


class TaskRequest(BaseModel):
    user_id: str
    task_description: str


class TaskResponse(BaseModel):
    analysis: str
    suggestions: list[str]
    priority: str
    next_action: str
    processed_at: str


@router.post("/analyze-task", response_model=TaskResponse)
async def analyze_task(request: TaskRequest) -> TaskResponse:
    """Analyze a task using AI agent."""
    try:
        result = await task_agent.process_task(
            user_id=request.user_id,
            task_description=request.task_description
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return TaskResponse(**result)

    except Exception as e:
        logger.error(f"Error in analyze_task endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check():
    """Health check for AI Agent service."""
    return {
        "status": "healthy",
        "service": "ai-agent-service",
        "agent_status": "active"
    }