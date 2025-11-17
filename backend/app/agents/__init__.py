"""
VibeSDLC Agent System

MetaGPT-inspired multi-agent system with single process,
in-memory message passing, and Observe-Think-Act cycle.

Usage:
    # Start all agents
    python -m app.agents

    # Use in code
    from app.agents import AgentTeam
    from app.agents.implementations import TeamLeaderAgent

    team = AgentTeam()
    team.hire([TeamLeaderAgent()])
    await team.start("Build a feature")
"""

from app.agents.team import AgentTeam
from app.agents.implementations import (
    TeamLeaderAgent,
    BusinessAnalystAgent,
    DeveloperAgent,
    TesterAgent,
)

__all__ = [
    "AgentTeam",
    "TeamLeaderAgent",
    "BusinessAnalystAgent",
    "DeveloperAgent",
    "TesterAgent",
]

