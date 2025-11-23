"""Tester Agent - QA, testing, and validation.

NEW ARCHITECTURE:
- Tester: Merged BaseAgent class (replaces TesterRole + TesterConsumer)
- TesterCrew: Legacy crew class (kept for reference)
"""

from .tester import Tester
from .crew import TesterCrew

__all__ = ["Tester", "TesterCrew"]
