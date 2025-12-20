"""Credit and token activity endpoints."""

from fastapi import APIRouter, Query, HTTPException
from sqlmodel import Session, select, col, func
from app.api.deps import CurrentUser, SessionDep
from app.models import CreditActivity, Agent, Project, Story
from app.models.base import Role
from datetime import datetime, timezone, timedelta
from typing import Any
from app.schemas.credits import (
    CreditActivityItem,
    CreditActivityResponse,
    TokenMonitoringStats,
)
from app.utils.analytics import (
    get_top_users,
    get_top_projects,
    get_model_breakdown,
)

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/activities", response_model=CreditActivityResponse)
def get_user_credit_activities(
    current_user: CurrentUser,
    session: SessionDep,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    project_id: str | None = Query(default=None, description="Filter by project ID"),
) -> Any:
    """Get user's credit activities with token details.
    
    Args:
        project_id: Optional project ID to filter activities
    
    Returns:
    - Paginated activity list
    - Summary stats (total spent, tokens used, etc.)
    """
    # Query activities with pagination
    statement = (
        select(CreditActivity)
        .where(CreditActivity.user_id == current_user.id)
    )
    
    # Add project filter if provided
    if project_id:
        from uuid import UUID
        try:
            project_uuid = UUID(project_id)
            statement = statement.where(CreditActivity.project_id == project_uuid)
        except (ValueError, AttributeError):
            pass  # Invalid UUID, skip filter
    
    statement = (
        statement
        .order_by(col(CreditActivity.created_at).desc())
        .offset(offset)
        .limit(limit)
    )
    activities = session.exec(statement).all()
    
    # Get total count with same filters
    count_statement = select(func.count()).select_from(CreditActivity).where(
        CreditActivity.user_id == current_user.id
    )
    
    # Apply project filter to count as well
    if project_id:
        from uuid import UUID
        try:
            project_uuid = UUID(project_id)
            count_statement = count_statement.where(CreditActivity.project_id == project_uuid)
        except (ValueError, AttributeError):
            pass
    
    total = session.exec(count_statement).one()
    
    # Format items with related data
    items = []
    for activity in activities:
        agent = session.get(Agent, activity.agent_id) if activity.agent_id else None
        project = session.get(Project, activity.project_id) if activity.project_id else None
        story = session.get(Story, activity.story_id) if activity.story_id else None
        
        items.append(CreditActivityItem(
            id=str(activity.id),
            created_at=activity.created_at,
            activity_type=activity.activity_type or "unknown",
            amount=activity.amount or 0,
            tokens_used=activity.tokens_used,
            model_used=activity.model_used,
            llm_calls=activity.llm_calls,
            reason=activity.reason or "",
            agent_name=agent.human_name if agent else None,
            project_name=project.name if project else None,
            story_title=story.title if story else None,
            task_type=activity.task_type,
        ))
    
    # Calculate summary from all activities
    all_activities_stmt = select(CreditActivity).where(
        CreditActivity.user_id == current_user.id
    )
    all_activities = session.exec(all_activities_stmt).all()
    
    # Get top agent by token usage
    agent_usage = {}
    for a in all_activities:
        if a.agent_id and a.tokens_used:
            agent_usage[a.agent_id] = agent_usage.get(a.agent_id, 0) + (a.tokens_used or 0)
    
    top_agent_name = None
    if agent_usage:
        top_agent_id = max(agent_usage, key=agent_usage.get)
        top_agent = session.get(Agent, top_agent_id)
        top_agent_name = top_agent.human_name if top_agent else None
    
    # Get top model by usage
    model_usage = {}
    for a in all_activities:
        if a.model_used and a.tokens_used:
            model_usage[a.model_used] = model_usage.get(a.model_used, 0) + (a.tokens_used or 0)
    
    top_model = max(model_usage, key=model_usage.get) if model_usage else None
    
    summary = {
        "total_credits_spent": sum(abs(a.amount or 0) for a in all_activities if (a.amount or 0) < 0),
        "total_tokens_used": sum(a.tokens_used or 0 for a in all_activities),
        "total_llm_calls": sum(a.llm_calls or 0 for a in all_activities),
        "top_agent": top_agent_name,
        "top_model": top_model,
    }
    
    return CreditActivityResponse(
        total=total,
        items=items,
        summary=summary
    )


# Admin monitoring endpoints

@router.get("/monitoring/stats", response_model=TokenMonitoringStats)
def get_token_monitoring_stats(
    current_user: CurrentUser,
    session: SessionDep,
) -> Any:
    """Get system-wide token usage stats (Admin only).
    
    Returns:
    - Daily/monthly totals
    - Top users by token usage
    - Top projects by token usage
    - Model usage breakdown
    """
    # Check admin permission
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Today's stats
    today_activities = session.exec(
        select(CreditActivity)
        .where(CreditActivity.created_at >= today_start)
    ).all()
    
    # Month's stats
    month_activities = session.exec(
        select(CreditActivity)
        .where(CreditActivity.created_at >= month_start)
    ).all()
    
    return TokenMonitoringStats(
        today={
            "tokens": sum(a.tokens_used or 0 for a in today_activities),
            "credits": sum(abs(a.amount or 0) for a in today_activities if (a.amount or 0) < 0),
            "llm_calls": sum(a.llm_calls or 0 for a in today_activities),
        },
        this_month={
            "tokens": sum(a.tokens_used or 0 for a in month_activities),
            "credits": sum(abs(a.amount or 0) for a in month_activities if (a.amount or 0) < 0),
            "llm_calls": sum(a.llm_calls or 0 for a in month_activities),
        },
        top_users=get_top_users(month_activities, session),
        top_projects=get_top_projects(month_activities, session),
        model_breakdown=get_model_breakdown(month_activities),
    )
