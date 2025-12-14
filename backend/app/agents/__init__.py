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

__all__ = [
    "BaseAgent",
    "TaskContext",
    "TaskResult",
    "TeamLeader",
    "DeveloperV2",
    "Tester",
    "BusinessAnalyst",
]


def __getattr__(name: str):
    """Lazy import agents to avoid loading heavy dependencies at import time."""
    if name == "TeamLeader":
        from app.agents.team_leader import TeamLeader
        return TeamLeader
    elif name == "DeveloperV2":
        from app.agents.developer_v2 import DeveloperV2
        return DeveloperV2
    elif name == "Tester":
        from app.agents.tester import Tester
        return Tester
    elif name == "BusinessAnalyst":
        from app.agents.business_analyst import BusinessAnalyst
        return BusinessAnalyst
    elif name in ("BaseAgent", "TaskContext", "TaskResult"):
        from app.core.agent.base_agent import BaseAgent, TaskContext, TaskResult
        if name == "BaseAgent":
            return BaseAgent
        elif name == "TaskContext":
            return TaskContext
        elif name == "TaskResult":
            return TaskResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
