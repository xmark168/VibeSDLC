"""Story Logger - Send logs to frontend story detail view.

Replaces print/logger statements with WebSocket-enabled logging
that shows up in the story's Logging tab in frontend.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.agents.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class StoryLogger:
    """Logger that sends logs to story detail view in frontend.
    
    Usage in nodes:
        async def implement(state, agent=None, story_logger=None):
            log = story_logger or StoryLogger.noop()
            await log.info("[implement] Starting step 1")
            await log.debug("[implement] Context loaded")
            await log.error("[implement] LLM call failed", exc=e)
    """
    story_id: UUID
    agent: "BaseAgent"
    node_name: str = ""
    _buffer: list = None
    _flush_interval: float = 0.5  # Batch logs every 0.5s
    _last_flush: float = 0
    
    def __post_init__(self):
        self._buffer = []
        self._last_flush = 0
    
    @classmethod
    def noop(cls) -> "StoryLogger":
        """Create a no-op logger for testing/fallback."""
        return NoOpLogger()
    
    @classmethod
    def from_state(cls, state: Dict, agent: "BaseAgent") -> "StoryLogger":
        """Create logger from graph state."""
        story_id = state.get("story_id")
        if not story_id:
            return cls.noop()
        
        try:
            if isinstance(story_id, str):
                story_id = UUID(story_id)
            return cls(story_id=story_id, agent=agent)
        except Exception:
            return cls.noop()
    
    def with_node(self, node_name: str) -> "StoryLogger":
        """Create a new logger with node context."""
        return StoryLogger(
            story_id=self.story_id,
            agent=self.agent,
            node_name=node_name
        )
    
    async def _send_log(
        self,
        level: LogLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        exc: Optional[Exception] = None
    ) -> None:
        """Send log entry to story."""
        try:
            # Format message with node prefix
            formatted_msg = f"[{self.node_name}] {message}" if self.node_name else message
            
            # Add exception info if present
            if exc:
                formatted_msg += f"\n  Error: {type(exc).__name__}: {str(exc)}"
            
            # Send to story via agent's message_story method
            await self.agent.message_story(
                story_id=self.story_id,
                content=formatted_msg,
                message_type="log",
                details={
                    "level": level.value,
                    "node": self.node_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **(details or {})
                }
            )
            
            # Also log to standard logger for debugging
            log_func = getattr(logger, level.value if level.value != "success" else "info")
            log_func(f"[Story:{str(self.story_id)[:8]}] {formatted_msg}")
            
        except Exception as e:
            # Fallback to standard logging if story logging fails
            logger.error(f"[StoryLogger] Failed to send log: {e}")
            logger.info(f"[Fallback] {message}")
    
    async def debug(self, message: str, **details) -> None:
        """Log debug message."""
        await self._send_log(LogLevel.DEBUG, message, details)
    
    async def info(self, message: str, **details) -> None:
        """Log info message."""
        await self._send_log(LogLevel.INFO, message, details)
    
    async def warning(self, message: str, exc: Exception = None, **details) -> None:
        """Log warning message."""
        await self._send_log(LogLevel.WARNING, message, details, exc)
    
    async def error(self, message: str, exc: Exception = None, **details) -> None:
        """Log error message."""
        await self._send_log(LogLevel.ERROR, message, details, exc)
    
    async def success(self, message: str, **details) -> None:
        """Log success message."""
        await self._send_log(LogLevel.SUCCESS, message, details)
    
    # Sync versions for non-async code (buffers and flushes later)
    def debug_sync(self, message: str, **details) -> None:
        """Sync version - logs immediately to standard logger."""
        formatted_msg = f"[{self.node_name}] {message}" if self.node_name else message
        logger.debug(f"[Story:{str(self.story_id)[:8]}] {formatted_msg}")
    
    def info_sync(self, message: str, **details) -> None:
        """Sync version - logs immediately to standard logger."""
        formatted_msg = f"[{self.node_name}] {message}" if self.node_name else message
        logger.info(f"[Story:{str(self.story_id)[:8]}] {formatted_msg}")
    
    def warning_sync(self, message: str, **details) -> None:
        """Sync version - logs immediately to standard logger."""
        formatted_msg = f"[{self.node_name}] {message}" if self.node_name else message
        logger.warning(f"[Story:{str(self.story_id)[:8]}] {formatted_msg}")
    
    def error_sync(self, message: str, **details) -> None:
        """Sync version - logs immediately to standard logger."""
        formatted_msg = f"[{self.node_name}] {message}" if self.node_name else message
        logger.error(f"[Story:{str(self.story_id)[:8]}] {formatted_msg}")


class NoOpLogger(StoryLogger):
    """No-op logger for testing or when story_id is not available."""
    
    def __init__(self):
        self.story_id = None
        self.agent = None
        self.node_name = ""
        self._buffer = []
    
    async def _send_log(self, level: LogLevel, message: str, details=None, exc=None) -> None:
        # Just log to standard logger
        formatted_msg = f"[{self.node_name}] {message}" if self.node_name else message
        log_func = getattr(logger, level.value if level.value != "success" else "info")
        log_func(formatted_msg)
    
    def with_node(self, node_name: str) -> "NoOpLogger":
        noop = NoOpLogger()
        noop.node_name = node_name
        return noop


# =============================================================================
# Node Timeout Wrapper
# =============================================================================

NODE_TIMEOUT_SECONDS = 90  # 1 minute 30 seconds


class NodeTimeoutError(Exception):
    """Raised when a node exceeds its timeout."""
    def __init__(self, node_name: str, timeout: int):
        self.node_name = node_name
        self.timeout = timeout
        super().__init__(f"Node '{node_name}' timed out after {timeout}s")


async def with_timeout(
    coro,
    timeout: int = NODE_TIMEOUT_SECONDS,
    node_name: str = "unknown"
) -> Any:
    """Wrap a coroutine with timeout.
    
    Args:
        coro: Async coroutine to execute
        timeout: Timeout in seconds (default: 90s)
        node_name: Name of node for error message
    
    Returns:
        Result of coroutine
    
    Raises:
        NodeTimeoutError: If timeout exceeded
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise NodeTimeoutError(node_name, timeout)


def node_with_timeout(timeout: int = NODE_TIMEOUT_SECONDS):
    """Decorator to add timeout to a node function.
    
    Usage:
        @node_with_timeout(90)
        async def implement(state, agent=None):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            node_name = func.__name__
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                raise NodeTimeoutError(node_name, timeout)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


# =============================================================================
# Git Retry Helper with Lock
# =============================================================================

import subprocess
import time
import threading
from pathlib import Path

# Per-directory locks to serialize git operations
_git_locks: dict = {}
_git_locks_lock = threading.Lock()


def _get_git_lock(cwd: str) -> threading.Lock:
    """Get or create a lock for a specific git working directory."""
    # Normalize path to avoid duplicate locks for same dir
    cwd_normalized = str(Path(cwd).resolve())
    
    with _git_locks_lock:
        if cwd_normalized not in _git_locks:
            _git_locks[cwd_normalized] = threading.Lock()
        return _git_locks[cwd_normalized]


def git_with_retry(
    cmd: list,
    cwd: str,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    timeout: int = 30
) -> subprocess.CompletedProcess:
    """Execute git command with retry, exponential backoff, and directory lock.
    
    Uses per-directory locking to prevent concurrent git operations in the same
    working directory which can cause index.lock conflicts.
    
    Args:
        cmd: Git command as list (e.g., ["git", "add", "."])
        cwd: Working directory
        max_retries: Maximum retry attempts
        backoff_base: Base for exponential backoff (seconds)
        timeout: Command timeout
    
    Returns:
        CompletedProcess result
    
    Raises:
        subprocess.CalledProcessError: If all retries fail
    """
    lock = _get_git_lock(cwd)
    last_error = None
    
    with lock:  # Serialize git operations for this directory
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    timeout=timeout,
                    check=True
                )
                return result
            except subprocess.CalledProcessError as e:
                last_error = e
                # Check if it's a retryable error (e.g., lock)
                stderr = e.stderr.decode() if e.stderr else ""
                if "lock" in stderr.lower() or "index.lock" in stderr.lower():
                    wait_time = backoff_base * (2 ** attempt)
                    logger.warning(f"[git] Retry {attempt + 1}/{max_retries} after {wait_time}s: {stderr[:100]}")
                    time.sleep(wait_time)
                    # Try to remove stale lock file
                    lock_file = Path(cwd) / ".git" / "index.lock"
                    if lock_file.exists():
                        try:
                            lock_file.unlink()
                            logger.warning(f"[git] Removed stale index.lock")
                        except Exception:
                            pass
                else:
                    # Non-retryable error
                    raise
            except subprocess.TimeoutExpired as e:
                last_error = e
                wait_time = backoff_base * (2 ** attempt)
                logger.warning(f"[git] Timeout, retry {attempt + 1}/{max_retries} after {wait_time}s")
                time.sleep(wait_time)
    
    # All retries failed
    raise last_error


# =============================================================================
# Auto-fix Improvements
# =============================================================================

def analyze_error_type(error_logs: str) -> Dict[str, Any]:
    """Analyze error logs to determine error type and best fix strategy.
    
    Returns:
        {
            "error_type": "import" | "typescript" | "prisma" | "npm" | "runtime" | "unknown",
            "is_local_import": bool,  # True if it's a local @/ or ./ import
            "auto_fixable": bool,
            "fix_strategy": str,
            "files_mentioned": list[str]
        }
    """
    import re
    
    result = {
        "error_type": "unknown",
        "is_local_import": False,
        "auto_fixable": False,
        "fix_strategy": None,
        "files_mentioned": []
    }
    
    # Extract file paths mentioned in errors
    file_patterns = [
        r'([^\s(]+\.tsx?)\((\d+),(\d+)\)',  # file.tsx(line,col)
        r'\./([^\s:]+\.tsx?):(\d+):(\d+)',   # ./src/file.tsx:line:col
        r"(?:in|at)\s+([^\s]+\.tsx?)",       # in src/file.tsx
    ]
    for pattern in file_patterns:
        for match in re.finditer(pattern, error_logs):
            result["files_mentioned"].append(match.group(1))
    
    # Analyze error type
    
    # 1. Prisma errors
    prisma_patterns = [
        r"Cannot find module '@prisma/client'",
        r"PrismaClient is unable to run",
        r"Error: P\d{4}",  # Prisma error codes
        r"prisma generate",
    ]
    if any(re.search(p, error_logs) for p in prisma_patterns):
        result["error_type"] = "prisma"
        result["auto_fixable"] = True
        result["fix_strategy"] = "prisma_regenerate"
        return result
    
    # 2. Import errors - distinguish local vs npm
    import_patterns = [
        (r"Cannot find module ['\"](@/[^'\"]+)['\"]", True),   # Local @/ import
        (r"Can't resolve ['\"](@/[^'\"]+)['\"]", True),        # Local @/ import
        (r"Cannot find module ['\"](\.{1,2}/[^'\"]+)['\"]", True),  # Relative import
        (r"Cannot find module ['\"]([^'\"@./][^'\"]*)['\"]", False),  # NPM package
        (r"Module not found.*['\"]([^'\"]+)['\"]", False),
    ]
    for pattern, is_local in import_patterns:
        if re.search(pattern, error_logs):
            result["error_type"] = "import"
            result["is_local_import"] = is_local
            if not is_local:
                result["auto_fixable"] = True
                result["fix_strategy"] = "npm_install"
            else:
                result["auto_fixable"] = False
                result["fix_strategy"] = "fix_local_import"
            return result
    
    # 3. TypeScript type errors
    ts_patterns = [
        r"error TS\d+:",
        r"Type '.*' is not assignable to type",
        r"Property '.*' does not exist on type",
        r"Argument of type '.*' is not assignable",
    ]
    if any(re.search(p, error_logs) for p in ts_patterns):
        result["error_type"] = "typescript"
        result["auto_fixable"] = False
        result["fix_strategy"] = "fix_type_error"
        return result
    
    # 4. Runtime errors
    runtime_patterns = [
        r"TypeError:",
        r"ReferenceError:",
        r"Cannot read property",
        r"undefined is not",
    ]
    if any(re.search(p, error_logs) for p in runtime_patterns):
        result["error_type"] = "runtime"
        result["auto_fixable"] = False
        result["fix_strategy"] = "fix_runtime_error"
        return result
    
    return result


async def try_auto_fix(
    error_analysis: Dict[str, Any],
    workspace_path: str,
    story_logger: StoryLogger = None
) -> bool:
    """Attempt automatic fix based on error analysis.
    
    Args:
        error_analysis: Result from analyze_error_type()
        workspace_path: Path to workspace
        story_logger: Optional logger
    
    Returns:
        True if auto-fix was attempted and likely succeeded
    """
    log = story_logger or StoryLogger.noop()
    
    if not error_analysis.get("auto_fixable"):
        return False
    
    strategy = error_analysis.get("fix_strategy")
    
    try:
        if strategy == "prisma_regenerate":
            await log.info("Auto-fix: Regenerating Prisma client...")
            subprocess.run(
                "pnpm exec prisma generate",
                cwd=workspace_path,
                shell=True,
                capture_output=True,
                timeout=60
            )
            subprocess.run(
                "pnpm exec prisma db push --accept-data-loss",
                cwd=workspace_path,
                shell=True,
                capture_output=True,
                timeout=60
            )
            await log.success("Auto-fix: Prisma regenerated")
            return True
        
        elif strategy == "npm_install":
            await log.info("Auto-fix: Running pnpm install...")
            result = subprocess.run(
                "pnpm install --frozen-lockfile",
                cwd=workspace_path,
                shell=True,
                capture_output=True,
                timeout=120
            )
            if result.returncode == 0:
                await log.success("Auto-fix: Dependencies installed")
                return True
            else:
                await log.warning("Auto-fix: pnpm install failed")
                return False
        
        return False
        
    except Exception as e:
        await log.error(f"Auto-fix failed: {e}", exc=e)
        return False
