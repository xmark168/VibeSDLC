"""Subprocess utilities for process management.

This module consolidates subprocess-related helper functions used across
the application, particularly for managing dev servers and git operations.
"""

import asyncio
import logging
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill a process by PID."""
    try:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
        return True
    except (ProcessLookupError, OSError) as e:
        logger.debug(f"Failed to kill process {pid}: {e}")
        return False


def kill_process_on_port(port: int) -> bool:
    """Kill process(es) listening on a specific port."""
    try:
        result = subprocess.run(
            f'lsof -ti:{port}',
            shell=True, capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            for pid_str in result.stdout.strip().split('\n'):
                try:
                    os.kill(int(pid_str), signal.SIGKILL)
                except (ProcessLookupError, ValueError):
                    pass
            return True
    except Exception as e:
        logger.debug(f"Failed to kill process on port {port}: {e}")
    return False


def force_remove_directory(
    path: Path | str,
    max_retries: int = 2,
    retry_delay: float = 0.1
) -> bool:
    """Force remove a directory with retries. """
    path = Path(path)
    if not path.exists():
        return True
    
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path)
            if not path.exists():
                return True
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.warning(f"Failed to remove directory {path}: {e}")
    
    return not path.exists()


async def run_subprocess_async(
    cmd: list[str] | str,
    cwd: str | Path | None = None,
    capture_output: bool = True,
    timeout: int = 60,
    shell: bool = False,
    text: bool = True,
    **kwargs
) -> subprocess.CompletedProcess:
    """Run subprocess command asynchronously. """
    cwd_str = str(cwd) if cwd else None
    
    def _run():
        return subprocess.run(
            cmd,
            cwd=cwd_str,
            capture_output=capture_output,
            timeout=timeout,
            shell=shell,
            text=text,
            **kwargs
        )
    
    return await asyncio.to_thread(_run)


def cleanup_dev_server(
    workspace_path: Path | str | None = None,
    port: int | None = None,
    pid: int | None = None
) -> None:
    """Clean up dev server processes and lock files.
    
    Args:
        workspace_path: Path to workspace (for cleaning lock files)
        port: Port to kill processes on
        pid: Process ID to kill
    """
    # Kill by PID
    if pid:
        kill_process(pid, force=True)
    
    # Kill by port
    if port:
        kill_process_on_port(port)
    
    # Clean up Next.js artifacts
    if workspace_path:
        workspace_path = Path(workspace_path)
        if workspace_path.exists():
            # Remove lock file
            lock_file = workspace_path / ".next" / "dev" / "lock"
            if lock_file.exists():
                try:
                    lock_file.unlink()
                    logger.debug("Removed Next.js lock file")
                except Exception as e:
                    logger.warning(f"Failed to remove lock file: {e}")
            
            # Remove trace directory
            trace_dir = workspace_path / ".next" / "trace"
            if trace_dir.exists():
                try:
                    shutil.rmtree(trace_dir, ignore_errors=True)
                    logger.debug("Removed Next.js trace directory")
                except Exception:
                    pass


def find_free_port() -> int:
    """Find a free port on the system.
    
    Returns:
        Available port number
    """
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


async def wait_for_port(port: int, timeout: float = 30.0, interval: float = 0.5) -> bool:
    """Wait for a port to become available (something listening).
    
    Args:
        port: Port number to check
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds
        
    Returns:
        True if port is available, False if timeout
    """
    import socket
    
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(('127.0.0.1', port))
                return True
        except (socket.error, socket.timeout):
            await asyncio.sleep(interval)
    return False

