"""Agent core components.

This module exports the agent pool manager.

ARCHITECTURE:
- AgentPoolManager: In-memory single-process pool management
- BaseAgent pattern: All agents (TeamLeader, Developer, Tester, BusinessAnalyst)
  inherit from BaseAgent directly

REMOVED (old multiprocessing architecture):
- AgentPool (382 lines) - merged into AgentPoolManager
- MultiprocessingAgentPoolManager (512 lines) - replaced by current AgentPoolManager
- AgentPoolWorker (536 lines) - no longer needed (no multiprocessing)
- RedisClient (625 lines) - no longer needed (no IPC coordination)
- AgentRegistry/ProcessRegistry (406 lines) - no longer needed
- AgentMonitor (323 lines) - monitoring built into AgentPoolManager

Total removed: ~2,784 lines of complex multiprocessing code
"""

from .agent_pool_manager import AgentPoolManager

# Import AgentStatus from models for convenience
from app.models import AgentStatus

__all__ = [
    "AgentStatus",
    "AgentPoolManager",
]
