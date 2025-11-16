"""API routes for Retro Coordinator Agent."""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.deps import CurrentUser, SessionDep
from app.models import Sprint, Project

router = APIRouter(prefix="/retro-coordinator", tags=["retro-coordinator"])


class RetroAnalyzeRequest(BaseModel):
    """Request to analyze sprint retrospective."""
    sprint_id: str
    project_id: str
    user_feedback: Optional[str] = None


class RetroAnalyzeResponse(BaseModel):
    """Response from retrospective analysis."""
    status: str
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/analyze", response_model=RetroAnalyzeResponse)
def analyze_retrospective(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    request: RetroAnalyzeRequest,
) -> RetroAnalyzeResponse:
    """Analyze sprint retrospective and generate project rules.

    This endpoint:
    1. Gets sprint metrics and blockers from DB
    2. Analyzes with LLM to generate rules
    3. Saves rules to ProjectRules table
    4. Returns summary for frontend
    """
    try:
        # Validate sprint exists
        sprint = session.get(Sprint, UUID(request.sprint_id))
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")

        # Validate project exists
        project = session.get(Project, UUID(request.project_id))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Import and run agent
        from app.agents.scrum_master.retro_coordinator.agent_simplified import create_retro_coordinator_agent

        agent = create_retro_coordinator_agent(session=session)
        result = agent.run(
            sprint_id=request.sprint_id,
            project_id=request.project_id,
            user_feedback=request.user_feedback
        )

        return RetroAnalyzeResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
