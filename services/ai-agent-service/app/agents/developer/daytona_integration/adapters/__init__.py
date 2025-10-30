"""
Daytona Adapters Module

Abstraction layer cho filesystem và git operations.

Adapters:
- FilesystemAdapter: Abstract base class cho filesystem operations
- GitAdapter: Abstract base class cho git operations
- LocalFilesystemAdapter: Local filesystem implementation
- DaytonaFilesystemAdapter: Daytona sandbox filesystem implementation
- LocalGitAdapter: Local git implementation (GitPython)
- DaytonaGitAdapter: Daytona sandbox git implementation

Factory Functions:
- get_filesystem_adapter(): Get filesystem adapter based on config
- get_git_adapter(): Get git adapter based on config
"""

from .base import FilesystemAdapter, GitAdapter
from .filesystem_adapter import (
    DaytonaFilesystemAdapter,
    LocalFilesystemAdapter,
    get_filesystem_adapter,
)
from .git_adapter import DaytonaGitAdapter, LocalGitAdapter, get_git_adapter

__all__ = [
    # Abstract base classes
    "FilesystemAdapter",
    "GitAdapter",
    # Filesystem implementations
    "LocalFilesystemAdapter",
    "DaytonaFilesystemAdapter",
    "get_filesystem_adapter",
    # Git implementations
    "LocalGitAdapter",
    "DaytonaGitAdapter",
    "get_git_adapter",
]
