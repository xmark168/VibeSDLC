"""Business Analyst Agent - Requirements analysis and business documentation.

NEW ARCHITECTURE:
- BusinessAnalyst: Merged BaseAgent class for chat/task handling
- BusinessAnalystCrew: Complex workflow class (used by ba_agents.py API)
"""

from .business_analyst import BusinessAnalyst

__all__ = ["BusinessAnalyst"]
