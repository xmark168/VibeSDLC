"""
VibeSDLC Agent System

Unified event-driven agent architecture with Team Leader orchestrator
and modular specialist crews (Business Analyst, Developer, Tester).

Architecture:
    User Message → Team Leader → Specialist Crews → Response
                        ↓
                   (via Kafka)

Usage:
    # Start all crews (automatic with FastAPI app)
    from app.agents.orchestrator import start_orchestrator
    await start_orchestrator()

    # Get orchestrator status
    from app.agents.orchestrator import get_orchestrator
    orchestrator = await get_orchestrator()
    status = orchestrator.get_crew_status()

    # Access individual crews
    from app.agents.roles import (
        TeamLeaderCrew,
        BusinessAnalystCrew,
        DeveloperCrew,
        TesterCrew,
    )
"""

from app.agents.orchestrator import (
    AgentOrchestrator,
    get_orchestrator,
    start_orchestrator,
    stop_orchestrator,
)
from app.agents.roles import (
    TeamLeaderCrew,
    BusinessAnalystCrew,
    TesterCrew,
)

__all__ = [
    # Orchestrator
    "AgentOrchestrator",
    "get_orchestrator",
    "start_orchestrator",
    "stop_orchestrator",
    "TeamLeaderCrew",
    "BusinessAnalystCrew",
    "TesterCrew",
]
