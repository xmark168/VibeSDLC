"""Subprocess utilities for process management.

This module consolidates subprocess-related helper functions used across
the application, particularly for managing dev servers and git operations.
"""

import asyncio
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == 'win32'


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill a process by PID.
    
    Args:
        pid: Process ID to kill
        force: Whether to force kill (SIGKILL vs SIGTERM)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if IS_WINDOWS:
            cmd = f"taskkill /F /PID {pid} /T" if force else f"taskkill /PID {pid} /T"
            subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
        else:
            import signal
            os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
        return True
    except (ProcessLookupError, OSError, subprocess.TimeoutExpired) as e:
        logger.debug(f"Failed to kill process {pid}: {e}")
        return False


def kill_process_on_port(port: int) -> bool:
    """Kill process(es) listening on a specific port.
    
    Args:
        port: Port number
        
    Returns:
        True if any process was killed, False otherwise
    """
    try:
        if IS_WINDOWS:
            result = subprocess.run(
                f'netstat -ano | findstr :{port} | findstr LISTENING',
                shell=True, capture_output=True, text=True, timeout=10
            )
            killed_pids = set()
            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        target_pid = int(parts[-1])
                        if target_pid not in killed_pids:
                            subprocess.run(
                                f"taskkill /F /PID {target_pid} /T",
                                shell=True, capture_output=True, timeout=10
                            )
                            killed_pids.add(target_pid)
                    except ValueError:
                        pass
            return bool(killed_pids)
        else:
            result = subprocess.run(
                f'lsof -ti:{port}',
                shell=True, capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                for pid_str in result.stdout.strip().split('\n'):
                    try:
                        os.kill(int(pid_str), 9)
                    except (ProcessLookupError, ValueError):
                        pass
                return True
    except Exception as e:
        logger.debug(f"Failed to kill process on port {port}: {e}")
    return False


def kill_node_processes_in_directory(directory: Path | str) -> int:
    """Kill node processes that might be locking files in a directory.
    
    Windows only - on other platforms this is a no-op.
    
    Args:
        directory: Directory path
        
    Returns:
        Number of processes killed
    """
    if not IS_WINDOWS:
        return 0
    
    killed = 0
    try:
        # Kill all node.exe processes
        subprocess.run(
            ["taskkill", "/F", "/IM", "node.exe"],
            capture_output=True, timeout=10
        )
        killed += 1
    except Exception:
        pass
    
    return killed


def force_remove_directory(
    path: Path | str,
    max_retries: int = 3,
    retry_delay: float = 0.5
) -> bool:
    """Force remove a directory with multiple strategies.
    
    Handles Windows-specific issues like locked files and long paths.
    
    Args:
        path: Directory path to remove
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries (exponential backoff)
        
    Returns:
        True if successfully removed, False otherwise
    """
    path = Path(path)
    if not path.exists():
        return True
    
    def remove_readonly(func, fpath, excinfo):
        """Handle Windows readonly files."""
        import stat
        try:
            os.chmod(fpath, stat.S_IWRITE | stat.S_IREAD)
            func(fpath)
        except Exception:
            pass
    
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path, onerror=remove_readonly)
            if not path.exists():
                return True
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                kill_node_processes_in_directory(path)
            elif IS_WINDOWS:
                # Last resort: use robocopy to mirror an empty dir
                try:
                    empty_dir = tempfile.mkdtemp()
                    subprocess.run(
                        ["robocopy", empty_dir, str(path), "/mir", "/r:0", "/w:0",
                         "/njh", "/njs", "/nc", "/ns", "/np", "/nfl", "/ndl"],
                        capture_output=True, timeout=15  # Reduced from 60s to 15s
                    )
                    shutil.rmtree(empty_dir, ignore_errors=True)
                    shutil.rmtree(path, ignore_errors=True)
                    if not path.exists():
                        return True
                except Exception:
                    pass
            logger.warning(f"Failed to remove directory {path} after {max_retries} attempts: {e}")
    
    return not path.exists()


async def run_subprocess_async(
    cmd: list[str] | str,
    cwd: str | Path | None = None,
    capture_output: bool = True,
    timeout: int = 60,
    shell: bool | None = None,
    text: bool = True,
    **kwargs
) -> subprocess.CompletedProcess:
    """Run subprocess command asynchronously.
    
    Args:
        cmd: Command to run (list or string)
        cwd: Working directory
        capture_output: Whether to capture stdout/stderr
        timeout: Timeout in seconds
        shell: Whether to use shell (defaults to True on Windows for string cmd)
        text: Whether to decode output as text
        **kwargs: Additional subprocess.run kwargs
        
    Returns:
        CompletedProcess result
    """
    if shell is None:
        shell = IS_WINDOWS and isinstance(cmd, str)
    
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
