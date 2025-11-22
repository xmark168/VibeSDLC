"""
Modular agent roles package.

Each role is a self-contained CrewAI Crew with:
- crew.py: Crew definition and execution logic
- tasks.py: Task definitions
- tools.py: Role-specific tools (if needed)
- config.yaml: Agent configuration
- consumer.py: Kafka event consumer
"""

from .team_leader.crew import TeamLeaderCrew
from .business_analyst.crew import BusinessAnalystCrew
from .tester.crew import TesterCrew

__all__ = [
    "TeamLeaderCrew",
    "BusinessAnalystCrew",
    "TesterCrew",
]
