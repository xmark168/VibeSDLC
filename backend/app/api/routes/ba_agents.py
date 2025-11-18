"""Business Analyst API endpoints.

Endpoints for BA workflow: requirements → backlog
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from pydantic import BaseModel, Field

from app.api.deps import SessionDep, CurrentUser
from app.agents.roles.business_analyst.crew import BusinessAnalystCrew
from app.models import (
    BASession, BASessionStatus, Requirement, ProductBrief, BusinessFlow,
    Epic, Story, Project
)

router = APIRouter()


# ==================== PYDANTIC SCHEMAS ====================

class CreateSessionRequest(BaseModel):
    """Request to create a new BA session"""
    project_id: UUID


class CreateSessionResponse(BaseModel):
    """Response with created session info"""
    session_id: UUID
    status: str
    current_phase: str


class SendMessageRequest(BaseModel):
    """Request to send a message in analysis phase"""
    message: str


class SendMessageResponse(BaseModel):
    """Response with extracted requirements and assistant response"""
    success: bool
    assistant_response: str
    extracted_requirements: dict
    turn_count: int
    total_requirements: int


class PhaseExecutionRequest(BaseModel):
    """Request to execute a phase (with optional revision feedback)"""
    revision_feedback: Optional[str] = None


class PhaseExecutionResponse(BaseModel):
    """Response from phase execution"""
    success: bool
    phase: str
    output: str
    message: str


class SessionStatusResponse(BaseModel):
    """Response with session status and progress"""
    session_id: UUID
    status: str
    current_phase: str
    turn_count: int
    requirements_count: int
    has_brief: bool
    flows_count: int
    epics_count: int
    stories_count: int


class RequirementsResponse(BaseModel):
    """Response with requirements list"""
    problem_goals: list[str]
    users_stakeholders: list[str]
    features_scope: list[str]
    total: int


class ProductBriefResponse(BaseModel):
    """Response with Product Brief"""
    product_summary: str
    problem_statement: str
    target_users: str
    product_goals: str
    scope: str
    revision_count: int


class ApproveRequest(BaseModel):
    """Request to approve or refine phase output"""
    approved: bool
    feedback: Optional[str] = None


# ==================== API ENDPOINTS ====================

@router.post("/sessions", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_ba_session(
    request: CreateSessionRequest,
    session: SessionDep,
    current_user: CurrentUser
):
    """Create a new BA analysis session for a project.

    This starts the requirements gathering workflow.
    """
    # Verify project exists and user has access
    project = session.get(Project, request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project"
        )

    # Check for existing active session
    existing = session.query(BASession).filter(
        BASession.project_id == request.project_id,
        BASession.status.notin_([BASessionStatus.COMPLETED, BASessionStatus.CANCELLED])
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Active BA session already exists: {existing.id}"
        )

    # Create crew and session
    crew = BusinessAnalystCrew(db_session=session)
    ba_session = crew.create_session(request.project_id, current_user.id)

    return CreateSessionResponse(
        session_id=ba_session.id,
        status=ba_session.status.value,
        current_phase=ba_session.current_phase
    )


@router.get("/sessions/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: UUID,
    session: SessionDep,
    current_user: CurrentUser
):
    """Get status and progress of a BA session."""
    ba_session = session.get(BASession, session_id)
    if not ba_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get counts
    req_count = session.query(Requirement).filter(
        Requirement.session_id == session_id
    ).count()

    brief = session.query(ProductBrief).filter(
        ProductBrief.session_id == session_id
    ).first()

    flows_count = session.query(BusinessFlow).filter(
        BusinessFlow.session_id == session_id
    ).count()

    epics_count = session.query(Epic).filter(
        Epic.project_id == ba_session.project_id
    ).count()

    stories_count = session.query(Story).filter(
        Story.project_id == ba_session.project_id
    ).count()

    return SessionStatusResponse(
        session_id=ba_session.id,
        status=ba_session.status.value,
        current_phase=ba_session.current_phase,
        turn_count=ba_session.turn_count,
        requirements_count=req_count,
        has_brief=brief is not None,
        flows_count=flows_count,
        epics_count=epics_count,
        stories_count=stories_count
    )


@router.post("/sessions/{session_id}/message", response_model=SendMessageResponse)
async def send_message(
    session_id: UUID,
    request: SendMessageRequest,
    session: SessionDep,
    current_user: CurrentUser
):
    """Send a message during analysis phase.

    This extracts requirements from the message and returns assistant response.
    """
    ba_session = session.get(BASession, session_id)
    if not ba_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if ba_session.current_phase != "analysis":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is in {ba_session.current_phase} phase, not analysis"
        )

    # Execute analysis
    crew = BusinessAnalystCrew(db_session=session)
    crew.load_session(session_id)

    result = await crew.execute_analysis(
        user_message=request.message,
        project_id=ba_session.project_id,
        user_id=current_user.id
    )

    # Get updated counts
    req_count = session.query(Requirement).filter(
        Requirement.session_id == session_id
    ).count()

    return SendMessageResponse(
        success=result.get("success", False),
        assistant_response=result.get("assistant_response", ""),
        extracted_requirements=result.get("extracted_requirements", {}),
        turn_count=ba_session.turn_count,
        total_requirements=req_count
    )


@router.get("/sessions/{session_id}/requirements", response_model=RequirementsResponse)
async def get_requirements(
    session_id: UUID,
    session: SessionDep,
    current_user: CurrentUser
):
    """Get all requirements collected in the session."""
    ba_session = session.get(BASession, session_id)
    if not ba_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    reqs = session.query(Requirement).filter(
        Requirement.session_id == session_id
    ).all()

    # Group by category
    result = {
        "problem_goals": [],
        "users_stakeholders": [],
        "features_scope": []
    }

    for req in reqs:
        result[req.category.value].append(req.content)

    return RequirementsResponse(
        problem_goals=result["problem_goals"],
        users_stakeholders=result["users_stakeholders"],
        features_scope=result["features_scope"],
        total=len(reqs)
    )


@router.post("/sessions/{session_id}/create-brief", response_model=PhaseExecutionResponse)
async def create_product_brief(
    session_id: UUID,
    request: PhaseExecutionRequest,
    session: SessionDep,
    current_user: CurrentUser
):
    """Execute brief phase to create Product Brief.

    Can also be used to revise the brief with feedback.
    """
    ba_session = session.get(BASession, session_id)
    if not ba_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    crew = BusinessAnalystCrew(db_session=session)
    crew.load_session(session_id)

    result = await crew.execute_brief_phase(
        revision_feedback=request.revision_feedback,
        project_id=ba_session.project_id,
        user_id=current_user.id
    )

    return PhaseExecutionResponse(
        success=result.get("success", False),
        phase="brief",
        output=result.get("output", ""),
        message="Product Brief created successfully" if result.get("success") else "Failed to create brief"
    )


@router.get("/sessions/{session_id}/brief", response_model=ProductBriefResponse)
async def get_product_brief(
    session_id: UUID,
    session: SessionDep,
    current_user: CurrentUser
):
    """Get the Product Brief for a session."""
    brief = session.query(ProductBrief).filter(
        ProductBrief.session_id == session_id
    ).first()

    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product Brief not found"
        )

    return ProductBriefResponse(
        product_summary=brief.product_summary,
        problem_statement=brief.problem_statement,
        target_users=brief.target_users,
        product_goals=brief.product_goals,
        scope=brief.scope,
        revision_count=brief.revision_count
    )


@router.post("/sessions/{session_id}/design-solution", response_model=PhaseExecutionResponse)
async def design_solution(
    session_id: UUID,
    request: PhaseExecutionRequest,
    session: SessionDep,
    current_user: CurrentUser
):
    """Execute solution phase to design business flows.

    Can also be used to revise the solution with feedback.
    """
    ba_session = session.get(BASession, session_id)
    if not ba_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    crew = BusinessAnalystCrew(db_session=session)
    crew.load_session(session_id)

    result = await crew.execute_solution_phase(
        revision_feedback=request.revision_feedback,
        project_id=ba_session.project_id,
        user_id=current_user.id
    )

    return PhaseExecutionResponse(
        success=result.get("success", False),
        phase="solution",
        output=result.get("output", ""),
        message="Business flows designed successfully" if result.get("success") else "Failed to design solution"
    )


@router.post("/sessions/{session_id}/create-backlog", response_model=PhaseExecutionResponse)
async def create_backlog(
    session_id: UUID,
    request: PhaseExecutionRequest,
    session: SessionDep,
    current_user: CurrentUser
):
    """Execute backlog phase to create Epics & Stories.

    Can also be used to revise the backlog with feedback.
    """
    ba_session = session.get(BASession, session_id)
    if not ba_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    crew = BusinessAnalystCrew(db_session=session)
    crew.load_session(session_id)

    result = await crew.execute_backlog_phase(
        revision_feedback=request.revision_feedback,
        project_id=ba_session.project_id,
        user_id=current_user.id
    )

    return PhaseExecutionResponse(
        success=result.get("success", False),
        phase="backlog",
        output=result.get("output", ""),
        message="Backlog created successfully" if result.get("success") else "Failed to create backlog"
    )


@router.post("/sessions/{session_id}/approve-brief")
async def approve_brief(
    session_id: UUID,
    request: ApproveRequest,
    session: SessionDep,
    current_user: CurrentUser
):
    """Approve or request revision of Product Brief."""
    brief = session.query(ProductBrief).filter(
        ProductBrief.session_id == session_id
    ).first()

    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product Brief not found"
        )

    if request.approved:
        from datetime import datetime, timezone
        brief.approved = True
        brief.approved_at = datetime.now(timezone.utc)
        session.commit()
        return {"message": "Brief approved", "next_step": "design-solution"}
    else:
        return {
            "message": "Brief needs revision",
            "feedback": request.feedback,
            "next_step": "create-brief with revision_feedback"
        }


@router.post("/sessions/{session_id}/cancel")
async def cancel_session(
    session_id: UUID,
    session: SessionDep,
    current_user: CurrentUser
):
    """Cancel a BA session."""
    ba_session = session.get(BASession, session_id)
    if not ba_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    ba_session.status = BASessionStatus.CANCELLED
    session.commit()

    return {"message": "Session cancelled"}


@router.get("/projects/{project_id}/sessions")
async def list_project_sessions(
    project_id: UUID,
    session: SessionDep,
    current_user: CurrentUser
):
    """List all BA sessions for a project."""
    sessions = session.query(BASession).filter(
        BASession.project_id == project_id
    ).order_by(BASession.created_at.desc()).all()

    return [
        {
            "session_id": s.id,
            "status": s.status.value,
            "current_phase": s.current_phase,
            "turn_count": s.turn_count,
            "created_at": s.created_at.isoformat(),
            "completed_at": s.completed_at.isoformat() if s.completed_at else None
        }
        for s in sessions
    ]
