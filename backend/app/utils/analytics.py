"""Analytics and aggregation utilities."""

from collections import Counter
from typing import Optional
from uuid import UUID
from sqlmodel import Session


def get_top_agent(activities: list, session: Session) -> Optional[str]:
    """Get agent name with most usage from activities."""
    from app.models import Agent
    
    agent_ids = [a.agent_id for a in activities if a.agent_id]
    if not agent_ids:
        return None
    
    top_agent_id = Counter(agent_ids).most_common(1)[0][0]
    agent = session.get(Agent, top_agent_id)
    return agent.human_name if agent else None


def get_top_model(activities: list) -> Optional[str]:
    """Get most-used model from activities."""
    models = [a.model_used for a in activities if a.model_used]
    if not models:
        return None
    
    return Counter(models).most_common(1)[0][0]


def get_top_users(activities: list, session: Session, limit: int = 10) -> list[dict]:
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


def get_top_projects(activities: list, session: Session, limit: int = 10) -> list[dict]:
    """Get top projects by token usage.
    
    Args:
        activities: List of CreditActivity objects
        session: Database session
        limit: Maximum number of projects to return
        
    Returns:
        List of project dictionaries with usage stats
    """
    from app.models import Project
    
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


def get_model_breakdown(activities: list) -> dict:
    """Get model usage breakdown with counts and token totals.
    
    Args:
        activities: List of CreditActivity objects
        
    Returns:
        Dictionary mapping model names to usage stats
    """
    model_counts = Counter(a.model_used for a in activities if a.model_used)
    model_tokens = {}
    
    for activity in activities:
        if activity.model_used and activity.tokens_used:
            model_tokens[activity.model_used] = model_tokens.get(activity.model_used, 0) + activity.tokens_used
    
    breakdown = {}
    for model in model_counts:
        breakdown[model] = {
            "count": model_counts[model],
            "tokens": model_tokens.get(model, 0),
        }
    
    return breakdown
