"""
Team Leader Agent Module

Combines Router Agent, Insights Agent, and Team Leader Agent into one intelligent orchestrator
that uses CrewAI for all analysis and delegation decisions.
"""

from app.agents.team_leader.team_leader_consumer import (
    team_leader_consumer,
)

__all__ = ["team_leader_consumer"]
