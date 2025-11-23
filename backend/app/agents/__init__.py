"""
VibeSDLC Agent System - NEW ARCHITECTURE

Centralized routing with specialized agents using BaseAgent pattern.

Architecture:
    User Message → Central Router → Agent (via AGENT_TASKS topic)
                        ↓
                   (via Kafka)

NEW PATTERN (ALL MIGRATED):
- TeamLeader: Merged BaseAgent class (no delegation, provides guidance)
- Developer: Merged BaseAgent class (code implementation)
- Tester: Merged BaseAgent class (QA and testing)
- BusinessAnalyst: Merged BaseAgent class (requirements analysis)
- Router: Handles all message routing based on @mentions

Usage:
    # Agents are managed by AgentPoolManager (started in main.py)
    # Router started automatically in main.py lifespan

    # To spawn agents:
    from app.api.routes.agent_management import initialize_default_pools
    await initialize_default_pools()
"""

from app.agents.team_leader import TeamLeader
from app.agents.roles.developer import Developer
from app.agents.roles.tester import Tester
from app.agents.roles.business_analyst import BusinessAnalyst
from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult


__all__ = [
    # New Architecture
    "BaseAgent",
    "TaskContext",
    "TaskResult",
    "TeamLeader",
    "Developer",
    "Tester",
    "BusinessAnalyst",
]
