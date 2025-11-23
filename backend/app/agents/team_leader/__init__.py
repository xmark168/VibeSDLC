"""Team Leader Agent - Crew-based implementation.

Architecture:
- BaseAgent pattern (inherits from BaseAgent)
- Crew with multiple specialist agents
- Kafka integration for task routing
"""

from app.agents.team_leader.team_leader import TeamLeader

__all__ = ["TeamLeader"]
