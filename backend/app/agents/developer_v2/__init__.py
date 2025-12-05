"""Developer V2 Agent Package.

Story-driven developer agent using LangGraph router pattern.
Handles story events from Todo -> InProgress and processes user stories
through analyze, design, plan, implement, and code review phases.
"""

__all__ = ["DeveloperV2"]


def __getattr__(name: str):
    """Lazy import to avoid loading heavy dependencies at import time."""
    if name == "DeveloperV2":
        from app.agents.developer_v2.developer_v2 import DeveloperV2
        return DeveloperV2
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
