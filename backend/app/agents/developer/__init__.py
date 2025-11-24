"""Developer Agent - Code implementation and development tasks.

NEW ARCHITECTURE:
- Developer: Merged BaseAgent class (replaces DeveloperRole + DeveloperConsumer)
- DeveloperCrew: Legacy crew class (kept for BA workflow if needed)
"""

from .developer import Developer

__all__ = ["Developer"]
