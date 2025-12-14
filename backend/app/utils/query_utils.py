"""Query utilities for optimized database access.

This module provides reusable eager loading options and query patterns
to prevent N+1 query problems.
"""

from sqlalchemy.orm import selectinload, joinedload

from app.models import Story, Project, Agent, Message, Epic


# Eager loading options for common query patterns
class EagerLoad:
    """Predefined eager loading options for models."""
    
    # Story with all commonly needed relationships
    STORY_FULL = [
        selectinload(Story.epic),
        selectinload(Story.assigned_agent),
        selectinload(Story.project),
    ]
    
    # Story with epic only (for list views)
    STORY_WITH_EPIC = [
        selectinload(Story.epic),
    ]
    
    # Story with messages (for detail view)
    STORY_WITH_MESSAGES = [
        selectinload(Story.epic),
        selectinload(Story.messages),
        selectinload(Story.logs),
    ]
    
    # Project with all relationships
    PROJECT_FULL = [
        selectinload(Project.stories),
        selectinload(Project.agents),
        selectinload(Project.epics),
    ]
    
    # Project with stories only
    PROJECT_WITH_STORIES = [
        selectinload(Project.stories).selectinload(Story.epic),
    ]
    
    # Agent with project
    AGENT_WITH_PROJECT = [
        selectinload(Agent.project),
        selectinload(Agent.persona_template),
    ]
    
    # Message with agent
    MESSAGE_WITH_AGENT = [
        selectinload(Message.agent),
    ]


def apply_eager_loading(statement, options: list):
    """Apply eager loading options to a SQLAlchemy statement.
    
    Args:
        statement: SQLAlchemy select statement
        options: List of eager loading options from EagerLoad class
        
    Returns:
        Statement with eager loading applied
    """
    for option in options:
        statement = statement.options(option)
    return statement
