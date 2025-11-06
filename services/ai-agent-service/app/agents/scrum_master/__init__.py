"""Scrum Master Agent module.

Main exports:
- ScrumMasterAgent: Supervisor Agent that routes to Daily/Retro coordinators
- create_scrum_master_agent: Convenience function

Note: Sprint Planning is now handled by Product Owner Agent.
      Sprint Planner subagent has been removed.
"""

# Lazy imports to avoid deepagents dependency issues
def __getattr__(name):
    if name == "ScrumMasterAgent":
        from .scrum_master_agent import ScrumMasterAgent
        return ScrumMasterAgent
    elif name == "create_scrum_master_agent":
        from .scrum_master_agent import create_scrum_master_agent
        return create_scrum_master_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ScrumMasterAgent",
    "create_scrum_master_agent"
]
