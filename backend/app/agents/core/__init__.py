"""Agent core components.

This module exports the simplified agent pool manager.

ARCHITECTURE:
- SimplifiedAgentPoolManager: In-memory single-process pool management
- BaseAgent pattern: All agents (TeamLeader, Developer, Tester, BusinessAnalyst)
  inherit from BaseAgent directly

REMOVED (old multiprocessing architecture):
- AgentPool (382 lines) - merged into SimplifiedAgentPoolManager
- AgentPoolManager (512 lines) - replaced by SimplifiedAgentPoolManager
- AgentPoolWorker (536 lines) - no longer needed (no multiprocessing)
- RedisClient (625 lines) - no longer needed (no IPC coordination)
- AgentRegistry/ProcessRegistry (406 lines) - no longer needed
- AgentMonitor (323 lines) - monitoring built into SimplifiedAgentPoolManager

Total removed: ~2,784 lines of complex multiprocessing code
"""

from .simple_pool_manager import SimplifiedAgentPoolManager

# Import AgentStatus from models for convenience
from app.models import AgentStatus

__all__ = [
    "AgentStatus",
    "SimplifiedAgentPoolManager",
]
