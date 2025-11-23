"""Tester Agent - QA, testing, and validation.

NEW ARCHITECTURE:
- Tester: Merged BaseAgent class (replaces TesterRole + TesterConsumer)
- TesterCrew: Legacy crew class (kept for reference)
"""

from .tester import Tester

__all__ = ["Tester"]
