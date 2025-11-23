"""Business Analyst Agent - Requirements analysis and business documentation.

NEW ARCHITECTURE:
- BusinessAnalyst: Simple BaseAgent class for chat/task handling
- Handles @BusinessAnalyst mentions in chat
- Provides requirements analysis and PRD generation
"""

from .business_analyst import BusinessAnalyst

__all__ = ["BusinessAnalyst"]
