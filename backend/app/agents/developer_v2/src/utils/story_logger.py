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
        # Don't prefix content with node - frontend displays node separately
        # 1. Save to database (story_logs table)
        try:
            with Session(engine) as session:
                log_entry = StoryLog(
                    story_id=UUID(story_id),
                    content=message,  # Raw message, no prefix
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
            "content": message,  # Raw message, no prefix
            "level": level,
            "node": node,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, UUID(project_id))
        
        # 3. Also log to standard logger for debugging
        log_func = getattr(logger, level if level in ["debug", "info", "warning", "error"] else "info")
        log_func(f"[Story:{story_id[:8]}] [{node}] {message}")
        
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
            "error_type": str,
            "is_local_import": bool,
            "auto_fixable": bool,
            "fix_strategy": str,
            "files_mentioned": list[str],
            "details": dict  # Additional context for fix
        }
    """
    import re
    
    result = {
        "error_type": "unknown",
        "is_local_import": False,
        "auto_fixable": False,
        "fix_strategy": None,
        "files_mentioned": [],
        "details": {}
    }
    
    # Extract file paths mentioned in errors
    file_patterns = [
        r'([^\s(]+\.tsx?)\((\d+),(\d+)\)',  # file.tsx(line,col)
        r'\./([^\s:]+\.tsx?):(\d+):(\d+)',   # ./src/file.tsx:line:col
        r"(?:in|at)\s+([^\s]+\.tsx?)",       # in src/file.tsx
        r"Error: (.+\.tsx?):",               # Error: src/file.tsx:
        r"'([^']+\.tsx?)'",                  # 'src/file.tsx'
    ]
    for pattern in file_patterns:
        for match in re.finditer(pattern, error_logs):
            file_path = match.group(1)
            if file_path and file_path not in result["files_mentioned"]:
                result["files_mentioned"].append(file_path)
    
    # =========================================================================
    # 1. 'use client' directive errors (AUTO-FIXABLE)
    # =========================================================================
    use_client_patterns = [
        (r"(useState|useEffect|useContext|useReducer|useCallback|useMemo|useRef|useLayoutEffect|useImperativeHandle|useDebugValue)\s+only works in a Client Component", "hook"),
        (r"useActionState only works in a Client Component", "hook"),
        (r"Event handlers cannot be passed to Client Component props", "event_handler"),
        (r"You're importing a component that needs (useState|useEffect|useContext|useReducer)", "hook"),
        (r"createContext only works in a Client Component", "context"),
        (r"onClick.*cannot be passed to.*Server Component", "event_handler"),
        (r"onChange.*cannot be passed to.*Server Component", "event_handler"),
        (r"onSubmit.*cannot be passed to.*Server Component", "event_handler"),
    ]
    for pattern, reason in use_client_patterns:
        match = re.search(pattern, error_logs, re.IGNORECASE)
        if match:
            result["error_type"] = "use_client_missing"
            result["auto_fixable"] = True
            result["fix_strategy"] = "add_use_client"
            result["details"]["reason"] = reason
            result["details"]["hook_or_event"] = match.group(1) if match.lastindex else reason
            return result
    
    # =========================================================================
    # 2. ESLint fixable errors (AUTO-FIXABLE)
    # =========================================================================
    eslint_fixable_patterns = [
        (r"'([^']+)' is defined but never used", "unused_var"),
        (r"'([^']+)' is assigned a value but never used", "unused_var"),
        (r"Unexpected console statement", "console_statement"),
        (r"Missing semicolon", "semicolon"),
        (r"Extra semicolon", "semicolon"),
        (r"Strings must use (singlequote|doublequote)", "quotes"),
        (r"Expected indentation of (\d+) spaces", "indentation"),
        (r"Trailing spaces not allowed", "trailing_spaces"),
        (r"Newline required at end of file", "newline_eof"),
        (r"More than (\d+) blank lines not allowed", "blank_lines"),
        (r"@typescript-eslint/no-unused-vars", "unused_var"),
        (r"react-hooks/exhaustive-deps", "deps_array"),
        (r"prefer-const", "prefer_const"),
        (r"no-var", "no_var"),
    ]
    eslint_errors_found = []
    for pattern, error_type in eslint_fixable_patterns:
        if re.search(pattern, error_logs, re.IGNORECASE):
            eslint_errors_found.append(error_type)
    
    if eslint_errors_found:
        result["error_type"] = "eslint_fixable"
        result["auto_fixable"] = True
        result["fix_strategy"] = "eslint_fix"
        result["details"]["eslint_errors"] = eslint_errors_found
        return result
    
    # =========================================================================
    # 3. Prettier/Format errors (AUTO-FIXABLE)
    # =========================================================================
    prettier_patterns = [
        r"Code style issues found",
        r"Forgot to run Prettier",
        r"Replace .* with",
        r"Delete .* ⏎",
        r"Insert .* ⏎",
    ]
    if any(re.search(p, error_logs, re.IGNORECASE) for p in prettier_patterns):
        result["error_type"] = "prettier"
        result["auto_fixable"] = True
        result["fix_strategy"] = "prettier_fix"
        return result
    
    # =========================================================================
    # 4. Missing/unused imports (AUTO-FIXABLE with organize-imports)
    # =========================================================================
    import_organize_patterns = [
        (r"'([^']+)' is defined but never used.*@typescript-eslint/no-unused-vars", "unused_import"),
        (r"import.*'([^']+)'.*is defined but never used", "unused_import"),
        (r"Cannot find name '([^']+)'.*Did you mean", "missing_import"),
    ]
    for pattern, import_type in import_organize_patterns:
        match = re.search(pattern, error_logs)
        if match:
            result["error_type"] = "import_organize"
            result["auto_fixable"] = True
            result["fix_strategy"] = "organize_imports"
            result["details"]["import_type"] = import_type
            result["details"]["identifier"] = match.group(1)
            return result
    
    # =========================================================================
    # 5. Next.js cache/build issues (AUTO-FIXABLE)
    # =========================================================================
    nextjs_cache_patterns = [
        r"Module not found.*in.*\.next",
        r"Cannot find module.*\.next/types",
        r"ENOENT.*\.next",
        r"Build failed because of webpack errors",
        r"Failed to compile.*Module build failed",
    ]
    if any(re.search(p, error_logs, re.IGNORECASE) for p in nextjs_cache_patterns):
        result["error_type"] = "nextjs_cache"
        result["auto_fixable"] = True
        result["fix_strategy"] = "clear_nextjs_cache"
        return result
    
    # =========================================================================
    # 6. TypeScript strict null checks (PARTIALLY AUTO-FIXABLE)
    # =========================================================================
    null_check_patterns = [
        (r"Object is possibly 'undefined'", "undefined"),
        (r"Object is possibly 'null'", "null"),
        (r"Cannot read propert(?:y|ies) of undefined", "undefined_access"),
        (r"Cannot read propert(?:y|ies) of null", "null_access"),
        (r"'([^']+)' is possibly 'undefined'", "undefined"),
        (r"'([^']+)' is possibly 'null'", "null"),
    ]
    for pattern, null_type in null_check_patterns:
        if re.search(pattern, error_logs):
            result["error_type"] = "null_check"
            result["auto_fixable"] = False  # Needs LLM to add proper null checks
            result["fix_strategy"] = "add_null_checks"
            result["details"]["null_type"] = null_type
            # Don't return - continue checking for more specific errors
            break
    
    # =========================================================================
    # 7. Seed unique constraint errors (P2002) - NOT auto-fixable
    # =========================================================================
    seed_unique_patterns = [
        r"Unique constraint failed on the fields:",
        r"PrismaClientKnownRequestError:.*Unique constraint",
        r"code: 'P2002'",
        r"Error: P2002",
    ]
    if any(re.search(p, error_logs) for p in seed_unique_patterns):
        result["error_type"] = "seed_unique_constraint"
        result["auto_fixable"] = False
        result["fix_strategy"] = "fix_seed_unique_constraint"
        result["files_mentioned"].append("prisma/seed.ts")
        return result
    
    # =========================================================================
    # 8. Prisma client errors (AUTO-FIXABLE)
    # =========================================================================
    prisma_patterns = [
        r"Cannot find module '@prisma/client'",
        r"PrismaClient is unable to run",
        r"prisma generate",
        r"@prisma/client did not initialize yet",
        r"PrismaClientInitializationError",
    ]
    if any(re.search(p, error_logs) for p in prisma_patterns):
        result["error_type"] = "prisma"
        result["auto_fixable"] = True
        result["fix_strategy"] = "prisma_regenerate"
        return result
    
    # =========================================================================
    # 9. Import errors - distinguish local vs npm
    # =========================================================================
    import_patterns = [
        (r"Cannot find module ['\"](@/[^'\"]+)['\"]", True),
        (r"Can't resolve ['\"](@/[^'\"]+)['\"]", True),
        (r"Cannot find module ['\"](\.{1,2}/[^'\"]+)['\"]", True),
        (r"Cannot find module ['\"]([^'\"@./][^'\"]*)['\"]", False),
        (r"Module not found.*['\"]([^'\"]+)['\"]", False),
    ]
    for pattern, is_local in import_patterns:
        match = re.search(pattern, error_logs)
        if match:
            result["error_type"] = "import"
            result["is_local_import"] = is_local
            result["missing_package"] = match.group(1)  # Extract package name
            if not is_local:
                result["auto_fixable"] = True
                result["fix_strategy"] = "pnpm_add"  # Use pnpm add instead of install
            else:
                result["auto_fixable"] = False
                result["fix_strategy"] = "fix_local_import"
            return result
    
    # =========================================================================
    # 10. TypeScript type errors (NOT auto-fixable, needs LLM)
    # =========================================================================
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
    
    # =========================================================================
    # 11. Runtime errors (NOT auto-fixable)
    # =========================================================================
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


def _add_use_client_to_file(file_path: str) -> bool:
    """Add 'use client' directive to the top of a file.
    
    Returns True if file was modified, False otherwise.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return False
        
        content = path.read_text(encoding="utf-8")
        
        # Check if already has 'use client'
        if content.strip().startswith("'use client'") or content.strip().startswith('"use client"'):
            return False
        
        # Add 'use client' at the top
        new_content = "'use client';\n\n" + content
        path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        logger.warning(f"[auto-fix] Failed to add 'use client' to {file_path}: {e}")
        return False


def _find_files_needing_use_client(error_logs: str, workspace_path: str) -> list:
    """Extract file paths that need 'use client' from error logs."""
    import re
    
    files = []
    
    # Pattern: Error in specific file
    patterns = [
        r"Error:.*?([^\s]+\.tsx?)(?:\(|\:)",
        r"in ([^\s]+\.tsx?)",
        r"'([^\s']+\.tsx?)'",
        r"([^\s]+\.tsx?)\s*\n.*(?:useState|useEffect|onClick)",
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, error_logs):
            file_path = match.group(1)
            # Normalize path
            if file_path.startswith("./"):
                file_path = file_path[2:]
            if file_path.startswith("src/") or file_path.startswith("app/"):
                full_path = Path(workspace_path) / file_path
                if full_path.exists() and str(full_path) not in files:
                    files.append(str(full_path))
    
    return files


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
    details = error_analysis.get("details", {})
    files_mentioned = error_analysis.get("files_mentioned", [])
    
    try:
        # =====================================================================
        # Strategy: Add 'use client' directive
        # =====================================================================
        if strategy == "add_use_client":
            await log.info("Auto-fix: Adding 'use client' directive...")
            
            fixed_count = 0
            for file_path in files_mentioned:
                # Resolve full path
                if not Path(file_path).is_absolute():
                    full_path = Path(workspace_path) / file_path
                else:
                    full_path = Path(file_path)
                
                if full_path.exists() and _add_use_client_to_file(str(full_path)):
                    await log.info(f"  Added 'use client' to {file_path}")
                    fixed_count += 1
            
            if fixed_count > 0:
                await log.success(f"Auto-fix: Added 'use client' to {fixed_count} file(s)")
                return True
            else:
                await log.warning("Auto-fix: No files needed 'use client'")
                return False
        
        # =====================================================================
        # Strategy: ESLint --fix
        # =====================================================================
        elif strategy == "eslint_fix":
            await log.info("Auto-fix: Running ESLint --fix...")
            
            # Try pnpm lint:fix first (common script name)
            result = subprocess.run(
                "pnpm run lint:fix",
                cwd=workspace_path,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                await log.success("Auto-fix: ESLint fixes applied")
                return True
            
            # Fallback to direct eslint command
            result = subprocess.run(
                "pnpm exec eslint . --fix --ext .ts,.tsx,.js,.jsx",
                cwd=workspace_path,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 or "problems" in result.stdout.lower():
                await log.success("Auto-fix: ESLint fixes applied")
                return True
            
            await log.warning(f"Auto-fix: ESLint fix had issues: {result.stderr[:200] if result.stderr else ''}")
            return False
        
        # =====================================================================
        # Strategy: Prettier format
        # =====================================================================
        elif strategy == "prettier_fix":
            await log.info("Auto-fix: Running Prettier...")
            
            # Try pnpm format first
            result = subprocess.run(
                "pnpm run format",
                cwd=workspace_path,
                shell=True,
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                await log.success("Auto-fix: Prettier formatting applied")
                return True
            
            # Fallback to direct prettier
            result = subprocess.run(
                "pnpm exec prettier --write .",
                cwd=workspace_path,
                shell=True,
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                await log.success("Auto-fix: Prettier formatting applied")
                return True
            
            await log.warning("Auto-fix: Prettier formatting failed")
            return False
        
        # =====================================================================
        # Strategy: Organize imports (remove unused)
        # =====================================================================
        elif strategy == "organize_imports":
            await log.info("Auto-fix: Organizing imports...")
            
            # Use eslint with specific rule
            result = subprocess.run(
                "pnpm exec eslint . --fix --rule '@typescript-eslint/no-unused-vars: error'",
                cwd=workspace_path,
                shell=True,
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                await log.success("Auto-fix: Imports organized")
                return True
            
            # Try TypeScript organize imports via tsc
            await log.warning("Auto-fix: Import organization via ESLint failed, trying alternative...")
            return False
        
        # =====================================================================
        # Strategy: Clear Next.js cache
        # =====================================================================
        elif strategy == "clear_nextjs_cache":
            await log.info("Auto-fix: Clearing Next.js cache...")
            
            import shutil
            next_dir = Path(workspace_path) / ".next"
            
            if next_dir.exists():
                try:
                    shutil.rmtree(next_dir)
                    await log.info("  Removed .next directory")
                except Exception as e:
                    await log.warning(f"  Failed to remove .next: {e}")
            
            # Also clear node_modules/.cache
            cache_dir = Path(workspace_path) / "node_modules" / ".cache"
            if cache_dir.exists():
                try:
                    shutil.rmtree(cache_dir)
                    await log.info("  Removed node_modules/.cache")
                except Exception:
                    pass
            
            await log.success("Auto-fix: Next.js cache cleared")
            return True
        
        # =====================================================================
        # Strategy: Prisma regenerate
        # =====================================================================
        elif strategy == "prisma_regenerate":
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
        
        elif strategy == "pnpm_add":
            missing_package = error_analysis.get("missing_package", "")
            if not missing_package:
                await log.warning("Auto-fix: No package name found")
                return False
            
            await log.info(f"Auto-fix: Running pnpm add {missing_package}...")
            result = subprocess.run(
                f"pnpm add {missing_package}",
                cwd=workspace_path,
                shell=True,
                capture_output=True,
                timeout=120
            )
            if result.returncode == 0:
                await log.success(f"Auto-fix: Installed {missing_package}")
                return True
            else:
                stderr = result.stderr.decode() if result.stderr else ""
                await log.warning(f"Auto-fix: pnpm add failed - {stderr[:200]}")
                return False
        
        return False
        
    except subprocess.TimeoutExpired:
        await log.error("Auto-fix: Command timed out")
        return False
    except Exception as e:
        await log.error(f"Auto-fix failed: {e}", exc=e)
        return False


async def try_multiple_auto_fixes(
    error_logs: str,
    workspace_path: str,
    story_logger: StoryLogger = None,
    max_attempts: int = 3
) -> bool:
    """Try multiple auto-fix strategies in sequence.
    
    This is useful when multiple issues might exist.
    
    Args:
        error_logs: Raw error logs
        workspace_path: Path to workspace
        story_logger: Optional logger
        max_attempts: Max fix attempts
    
    Returns:
        True if any fix was successful
    """
    log = story_logger or StoryLogger.noop()
    any_fixed = False
    
    for attempt in range(max_attempts):
        analysis = analyze_error_type(error_logs)
        
        if not analysis.get("auto_fixable"):
            break
        
        await log.info(f"Auto-fix attempt {attempt + 1}: {analysis.get('fix_strategy')}")
        
        fixed = await try_auto_fix(analysis, workspace_path, story_logger)
        if fixed:
            any_fixed = True
            # Re-analyze to see if more fixes needed
            # In real usage, you'd re-run the build and get new error_logs
            break
        else:
            break
    
    return any_fixed
