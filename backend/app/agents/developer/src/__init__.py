"""Developer V2 Source Package."""

__all__ = [
    "DeveloperGraph",
    "DeveloperState",
]


def __getattr__(name: str):
    """Lazy import to avoid loading heavy dependencies at import time."""
    if name == "DeveloperGraph":
        from app.agents.developer.src.graph import DeveloperGraph
        return DeveloperGraph
    elif name == "DeveloperState":
        from app.agents.developer.src.state import DeveloperState
        return DeveloperState
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
