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


# =============================================================================
# Standalone log_to_story function (for use in nodes without StoryLogger class)
# =============================================================================

async def log_to_story(
    story_id: str,
    project_id: str,
    message: str,
    level: str = "info",
    node: str = "",
) -> None:
    """Log message to story - saves to DB and broadcasts via WebSocket.
    
    This is a standalone function that can be used in nodes without
    needing to create a StoryLogger instance.
    
    Args:
        story_id: Story UUID as string
        project_id: Project UUID as string  
        message: Log message content
        level: Log level (debug, info, warning, error, success)
        node: Node name for context (e.g., "run_code", "implement")
    
    Usage:
        await log_to_story(
            story_id=state.get("story_id"),
            project_id=state.get("project_id"),
            message="Starting build...",
            level="info",
            node="run_code"
        )
    """
    from app.websocket.connection_manager import connection_manager
    from app.models.story_log import StoryLog, LogLevel as DBLogLevel
    from sqlmodel import Session
    from app.core.db import engine
    
    try:
        # Format message with node prefix
        formatted_content = f"[{node}] {message}" if node else message
        
        # 1. Save to database (story_logs table)
        try:
            with Session(engine) as session:
                log_entry = StoryLog(
                    story_id=UUID(story_id),
                    content=formatted_content,
                    level=DBLogLevel(level) if level in ["debug", "info", "warning", "error"] else DBLogLevel.INFO,
                    node=node or "agent"
                )
                session.add(log_entry)
                session.commit()
        except Exception as e:
            logger.debug(f"[log_to_story] Failed to save log to DB: {e}")
        
        # 2. Broadcast via WebSocket (use story_log type, not story_message)
        await connection_manager.broadcast_to_project({
            "type": "story_log",
            "story_id": story_id,
            "content": formatted_content,
            "level": level,
            "node": node,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, UUID(project_id))
        
        # 3. Also log to standard logger for debugging
        log_func = getattr(logger, level if level in ["debug", "info", "warning", "error"] else "info")
        log_func(f"[Story:{story_id[:8]}] {formatted_content}")
        
    except Exception as e:
        logger.debug(f"[log_to_story] Failed: {e}")
        # Fallback to standard logging
        logger.info(f"[Fallback] [{node}] {message}")


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
            
            # Also store project_id from state for fallback
            instance = cls(story_id=story_id, agent=agent)
            instance._state_project_id = state.get("project_id")
            return instance
        except Exception:
            return cls.noop()
    
    def with_node(self, node_name: str) -> "StoryLogger":
        """Create a new logger with node context."""
        new_logger = StoryLogger(
            story_id=self.story_id,
            agent=self.agent,
            node_name=node_name
        )
        # Preserve state project_id
        if hasattr(self, '_state_project_id'):
            new_logger._state_project_id = self._state_project_id
        return new_logger
    
    async def _send_log(
        self,
        level: LogLevel,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        exc: Optional[Exception] = None
    ) -> None:
        """Send log entry to story (logs tab, not chat)."""
        try:
            # Format message with node prefix
            formatted_msg = f"[{self.node_name}] {message}" if self.node_name else message
            
            # Add exception info if present
            if exc:
                formatted_msg += f"\n  Error: {type(exc).__name__}: {str(exc)}"
            
            # Get project_id from agent
            project_id = self._get_project_id()
            if project_id:
                # Use log_to_story (saves to story_logs, broadcasts story_log event)
                await log_to_story(
                    story_id=str(self.story_id),
                    project_id=str(project_id),
                    message=formatted_msg,
                    level=level.value,
                    node=self.node_name
                )
            else:
                # Fallback to standard logging
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
    
    # =========================================================================
    # Chat Tab Messages (for user visibility)
    # =========================================================================
    
    def _get_project_id(self) -> Optional[UUID]:
        """Get project_id from agent or state."""
        # Try agent first
        if self.agent and hasattr(self.agent, 'project_id'):
            return self.agent.project_id
        # Fallback to state project_id
        if hasattr(self, '_state_project_id') and self._state_project_id:
            pid = self._state_project_id
            if isinstance(pid, str):
                try:
                    return UUID(pid)
                except:
                    pass
            elif isinstance(pid, UUID):
                return pid
        return None
    
    async def task(self, message: str, progress: float = None) -> None:
        """Send transient task update via WebSocket - NOT saved to DB.
        
        Use for: step-by-step progress, actions being performed.
        Frontend displays this in shadcn/ai Task component (ephemeral).
        
        Args:
            message: Task description (e.g., "Installing dependencies...")
            progress: Optional progress 0.0-1.0 for progress bar
        """
        try:
            from app.websocket.connection_manager import connection_manager
            
            project_id = self._get_project_id()
            if not project_id:
                logger.debug(f"[StoryLogger] task() skipped: no project_id")
                return
            
            # Broadcast directly via WebSocket - NOT through message_story (no DB save)
            await connection_manager.broadcast_to_project({
                "type": "story_task",
                "story_id": str(self.story_id),
                "content": message,
                "node": self.node_name,
                "progress": progress,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, project_id)
            
            # Also log to standard logger for debugging
            progress_str = f" ({int(progress * 100)}%)" if progress is not None else ""
            logger.debug(f"[Story:{str(self.story_id)[:8]}] [TASK] {message}{progress_str}")
            
        except Exception as e:
            logger.debug(f"[StoryLogger] task() failed: {e}")
    
    async def message(self, message: str) -> None:
        """Send milestone message to Chat tab - SAVED to DB.
        
        Use for: important updates, milestone completions, errors.
        This appears in chat history and persists.
        """
        try:
            await self.agent.message_story(
                self.story_id,
                message,
                message_type="text",
                details={"node": self.node_name}
            )
        except Exception as e:
            logger.debug(f"[StoryLogger] message() failed: {e}")
    
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
    
    def _get_project_id(self) -> Optional[UUID]:
        return None
    
    async def _send_log(self, level: LogLevel, message: str, details=None, exc=None) -> None:
        # Just log to standard logger
        formatted_msg = f"[{self.node_name}] {message}" if self.node_name else message
        log_func = getattr(logger, level.value if level.value != "success" else "info")
        log_func(formatted_msg)
    
    async def task(self, message: str, progress: float = None) -> None:
        # Just log to standard logger (no WebSocket)
        progress_str = f" ({int(progress * 100)}%)" if progress is not None else ""
        formatted_msg = f"[{self.node_name}] [TASK] {message}{progress_str}" if self.node_name else f"[TASK] {message}{progress_str}"
        logger.info(formatted_msg)
    
    async def message(self, message: str) -> None:
        # Just log to standard logger (no DB save)
        formatted_msg = f"[{self.node_name}] {message}" if self.node_name else message
        logger.info(formatted_msg)
    
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
    if not cwd:
        cwd = "."
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
        OSError: If cwd is invalid
    """
    # Validate and normalize cwd
    if not cwd:
        raise OSError("Working directory (cwd) cannot be empty")
    
    cwd_path = Path(cwd)
    if not cwd_path.exists():
        raise OSError(f"Working directory does not exist: {cwd}")
    
    # Normalize path for Windows compatibility
    cwd = str(cwd_path.resolve())
    
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
