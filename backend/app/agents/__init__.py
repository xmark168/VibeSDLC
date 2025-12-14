"""

"""

__all__ = [
    "BaseAgent",
    "TaskContext",
    "TaskResult",
    "TeamLeader",
    "Developer",
    "Tester",
    "BusinessAnalyst",
]


def __getattr__(name: str):
    """Lazy import agents to avoid loading heavy dependencies at import time."""
    if name == "TeamLeader":
        from app.agents.team_leader import TeamLeader
        return TeamLeader
    elif name == "Developer":
        from app.agents.developer import Developer
        return Developer
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
