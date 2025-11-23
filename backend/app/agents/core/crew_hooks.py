"""Crew AI Integration Hooks.

Provides decorators to auto-trigger Crew AI flows when tasks are received.
"""

import logging
from typing import Any, Callable, Dict
from functools import wraps

from crewai import Crew

logger = logging.getLogger(__name__)


def on_task(task_type: str):
    """Decorator to register a Crew factory for a specific task type.

    Usage:
        @on_task("implement_story")
        def create_implementation_crew(self, task_context):
            return Crew(
                agents=[self.create_agent()],
                tasks=self.create_tasks(task_context),
                ...
            )

    Args:
        task_type: Task type to handle (e.g., "implement_story", "user_story")

    Returns:
        Decorated function that will be called when task type is received
    """
    def decorator(crew_factory: Callable):
        @wraps(crew_factory)
        async def wrapper(agent_self, task_event):
            # Convert task to crew context
            context = _build_crew_context(task_event)

            # Call factory to create crew
            crew = crew_factory(agent_self, context)

            # Kickoff crew (async wrapper)
            result = await agent_self._kickoff_crew(crew, context)

            return result

        # Mark this method as a task handler
        wrapper._task_type = task_type
        wrapper._is_task_handler = True

        return wrapper

    return decorator


def _build_crew_context(task_event) -> Dict[str, Any]:
    """Build crew execution context from task event.

    Args:
        task_event: AgentTaskAssignedEvent or dict

    Returns:
        Context dictionary for crew execution
    """
    if hasattr(task_event, 'model_dump'):
        event_data = task_event.model_dump()
    else:
        event_data = task_event

    context = {
        "task_id": str(event_data.get("task_id", "")),
        "task_type": event_data.get("task_type", ""),
        "title": event_data.get("title", ""),
        "description": event_data.get("description", ""),
        "priority": event_data.get("priority", "medium"),
        "story_id": event_data.get("story_id"),
        "epic_id": event_data.get("epic_id"),
        "project_id": event_data.get("project_id"),
    }

    # Merge custom context from task
    task_context = event_data.get("context", {})
    if task_context:
        context.update(task_context)

    return context
