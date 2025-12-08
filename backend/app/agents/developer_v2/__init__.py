"""Developer V2 Agent Package.

Story-driven developer agent with two implementations:
1. DeveloperV2 - LangGraph state machine (6 nodes)
2. DeveloperV2DeepAgent - DeepAgents framework (simpler, with memory)

Set USE_DEEPAGENTS=true to use the DeepAgents implementation.
"""

import os

from app.agents.developer_v2.developer_v2 import DeveloperV2

# Try to import DeepAgents version (may fail if deepagents not installed)
try:
    from app.agents.developer_v2.developer_v2_deepagents import DeveloperV2DeepAgent
    DEEPAGENTS_AVAILABLE = True
except ImportError:
    DeveloperV2DeepAgent = None
    DEEPAGENTS_AVAILABLE = False


def get_developer_agent():
    """Get the appropriate developer agent based on configuration.
    
    Returns DeveloperV2DeepAgent if USE_DEEPAGENTS=true and deepagents is installed,
    otherwise returns DeveloperV2 (LangGraph version).
    """
    use_deepagents = os.getenv("USE_DEEPAGENTS", "false").lower() == "true"
    
    if use_deepagents and DEEPAGENTS_AVAILABLE:
        return DeveloperV2DeepAgent
    return DeveloperV2


__all__ = ["DeveloperV2", "DeveloperV2DeepAgent", "get_developer_agent", "DEEPAGENTS_AVAILABLE"]
