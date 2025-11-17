"""CrewAI integration package.

Provides CrewAI-based workflows and agent configurations
for AI-powered Scrum/Kanban automation.
"""

from app.crews.flows import SprintPlanningFlow, StoryGenerationFlow

__all__ = [
    "StoryGenerationFlow",
    "SprintPlanningFlow",
]
