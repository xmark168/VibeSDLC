"""Developer V2 Source Package.

Uses lazy imports to avoid loading heavy dependencies (langchain, langgraph) at import time.
"""

__all__ = [
    "DeveloperGraph",
    "DeveloperState",
    "StoryAnalysis",
    "ImplementationPlan",
    "PlanStep",
    "StoryInput",
    "WorkspaceState",
    "PlanState",
    "ReviewState",
    "DebugState",
    "SummarizeState",
    "RunCodeState",
    "unpack_story",
    "unpack_workspace",
    "unpack_plan",
    "unpack_review",
    "unpack_debug",
    "unpack_summarize",
    "unpack_run_code",
    "pack_story",
    "pack_workspace",
    "pack_plan",
    "pack_review",
    "pack_debug",
    "pack_summarize",
    "pack_run_code",
]


def __getattr__(name: str):
    """Lazy import to avoid loading heavy dependencies at import time."""
    if name == "DeveloperGraph":
        from app.agents.developer_v2.src.graph import DeveloperGraph
        return DeveloperGraph
    elif name == "DeveloperState":
        from app.agents.developer_v2.src.state import DeveloperState
        return DeveloperState
    elif name in ("StoryAnalysis", "ImplementationPlan", "PlanStep", "StoryInput",
                  "WorkspaceState", "PlanState", "ReviewState", "DebugState",
                  "SummarizeState", "RunCodeState"):
        from app.agents.developer_v2.src import schemas
        return getattr(schemas, name)
    elif name.startswith(("unpack_", "pack_")):
        from app.agents.developer_v2.src import state_helpers
        return getattr(state_helpers, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
