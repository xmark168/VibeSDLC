"""Credit and token activity endpoints."""

from fastapi import APIRouter, Query, HTTPException
from sqlmodel import Session, select, col, func
from app.api.deps import CurrentUser, SessionDep
from app.models import CreditActivity, Agent, Project, Story
from app.models.base import Role
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Any
from collections import Counter

router = APIRouter()


class CreditActivityItem(BaseModel):
    """Credit activity item for user display."""
    id: str
    created_at: datetime
    activity_type: str
    amount: int  # Credits
    tokens_used: int | None
    model_used: str | None
    llm_calls: int | None
    reason: str
    agent_name: str | None
    project_name: str | None
    story_title: str | None
    task_type: str | None


class CreditActivityResponse(BaseModel):
    """Paginated credit activity response."""
    total: int
    items: list[CreditActivityItem]
    summary: dict


@router.get("/activities", response_model=CreditActivityResponse)
def get_user_credit_activities(
    current_user: CurrentUser,
    session: SessionDep,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> Any:
    """Get user's credit activities with token details.
    
    Returns:
    - Paginated activity list
    - Summary stats (total spent, tokens used, etc.)
    """
    # Query activities with pagination
    statement = (
        select(CreditActivity)
        .where(CreditActivity.user_id == current_user.id)
        .order_by(col(CreditActivity.created_at).desc())
        .offset(offset)
        .limit(limit)
    )
    activities = session.exec(statement).all()
    
    # Get total count
    count_statement = select(func.count()).select_from(CreditActivity).where(
        CreditActivity.user_id == current_user.id
    )
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
    
    summary = {
        "total_credits_spent": sum(abs(a.amount or 0) for a in all_activities if (a.amount or 0) < 0),
        "total_tokens_used": sum(a.tokens_used or 0 for a in all_activities),
        "total_llm_calls": sum(a.llm_calls or 0 for a in all_activities),
        "top_agent": _get_top_agent(all_activities, session),
        "top_model": _get_top_model(all_activities),
    }
    
    return CreditActivityResponse(
        total=total,
        items=items,
        summary=summary
    )


def _get_top_agent(activities: list, session: Session) -> str | None:
    """Get agent name with most usage."""
    agent_ids = [a.agent_id for a in activities if a.agent_id]
    if not agent_ids:
        return None
    
    top_agent_id = Counter(agent_ids).most_common(1)[0][0]
    agent = session.get(Agent, top_agent_id)
    return agent.human_name if agent else None


def _get_top_model(activities: list) -> str | None:
    """Get most-used model."""
    models = [a.model_used for a in activities if a.model_used]
    if not models:
        return None
    
    return Counter(models).most_common(1)[0][0]


# Admin monitoring endpoints

class TokenMonitoringStats(BaseModel):
    """System-wide token monitoring stats."""
    today: dict
    this_month: dict
    top_users: list[dict]
    top_projects: list[dict]
    model_breakdown: dict


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
        top_users=_get_top_users(month_activities, session),
        top_projects=_get_top_projects(month_activities, session),
        model_breakdown=_get_model_breakdown(month_activities),
    )


def _get_top_users(activities: list, session: Session, limit: int = 10) -> list[dict]:
    """Get top users by token usage."""
    from app.models import User
    
    user_tokens = {}
    for activity in activities:
        if activity.user_id and activity.tokens_used:
            user_tokens[activity.user_id] = user_tokens.get(activity.user_id, 0) + activity.tokens_used
    
    top_users = []
    for user_id, tokens in sorted(user_tokens.items(), key=lambda x: x[1], reverse=True)[:limit]:
        user = session.get(User, user_id)
        if user:
            top_users.append({
                "user_id": str(user_id),
                "username": user.username,
                "email": user.email,
                "tokens_used": tokens,
            })
    
    return top_users


def _get_top_projects(activities: list, session: Session, limit: int = 10) -> list[dict]:
    """Get top projects by token usage."""
    project_tokens = {}
    for activity in activities:
        if activity.project_id and activity.tokens_used:
            project_tokens[activity.project_id] = project_tokens.get(activity.project_id, 0) + activity.tokens_used
    
    top_projects = []
    for project_id, tokens in sorted(project_tokens.items(), key=lambda x: x[1], reverse=True)[:limit]:
        project = session.get(Project, project_id)
        if project:
            top_projects.append({
                "project_id": str(project_id),
                "project_name": project.name,
                "tokens_used": tokens,
            })
    
    return top_projects


def _get_model_breakdown(activities: list) -> dict:
    """Get model usage breakdown."""
    model_counts = Counter(a.model_used for a in activities if a.model_used)
    model_tokens = {}
    
    for activity in activities:
        if activity.model_used and activity.tokens_used:
            model_tokens[activity.model_used] = model_tokens.get(activity.model_used, 0) + activity.tokens_used
    
    breakdown = {}
    for model in model_counts:
        breakdown[model] = {
            "calls": model_counts[model],
            "tokens": model_tokens.get(model, 0),
        }
    
    return breakdown
