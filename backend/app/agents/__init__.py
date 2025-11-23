"""
VibeSDLC Agent System - NEW ARCHITECTURE

Centralized routing with specialized agents using BaseAgent pattern.

Architecture:
    User Message → Central Router → Agent (via AGENT_TASKS topic)
                        ↓
                   (via Kafka)

NEW PATTERN:
- TeamLeader: Merged BaseAgent class (no delegation, provides guidance)
- BA/Developer/Tester: To be migrated to BaseAgent (currently old architecture)
- Router: Handles all message routing based on @mentions

Usage:
    # Agents are managed by AgentPoolManager (started in main.py)
    # Router started automatically in main.py lifespan

    # To spawn agents:
    from app.api.routes.agent_management import initialize_default_pools
    await initialize_default_pools()
"""

# NEW ARCHITECTURE exports
from app.agents.team_leader import TeamLeader
from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult

# OLD ARCHITECTURE exports (will be deprecated after migration)
from app.agents.roles.business_analyst import BusinessAnalystRole
from app.agents.roles.developer import DeveloperRole
from app.agents.roles.tester import TesterRole

__all__ = [
    # New Architecture
    "BaseAgent",
    "TaskContext",
    "TaskResult",
    "TeamLeader",
    # Old Architecture (deprecated, will be removed)
    "BusinessAnalystRole",
    "DeveloperRole",
    "TesterRole",
]
