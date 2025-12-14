"""Async database utilities for running sync DB operations in thread pool.

This module provides utilities to safely run synchronous database operations
from async contexts without blocking the event loop.
"""

import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TypeVar, Callable, Any, ParamSpec

from sqlmodel import Session
from app.core.db import engine

T = TypeVar('T')
P = ParamSpec('P')

# Shared thread pool for DB operations
_db_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="db_worker")


async def run_in_thread(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """Run a sync function in thread pool.
    
    Args:
        func: Synchronous function to run
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Function result
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_db_executor, partial(func, *args, **kwargs))


async def run_subprocess_async(
    cmd: list[str] | str,
    cwd: str | None = None,
    capture_output: bool = True,
    timeout: int = 60,
    shell: bool = False,
    **kwargs
) -> subprocess.CompletedProcess:
    """Run subprocess command asynchronously.
    
    Args:
        cmd: Command to run (list or string)
        cwd: Working directory
        capture_output: Whether to capture stdout/stderr
        timeout: Timeout in seconds
        shell: Whether to use shell
        **kwargs: Additional subprocess.run kwargs
        
    Returns:
        CompletedProcess result
    """
    def _run():
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            timeout=timeout,
            shell=shell,
            **kwargs
        )
    
    return await run_in_thread(_run)


class AsyncDB:
    """Async wrapper for synchronous database operations."""
    
    @staticmethod
    async def execute(func: Callable[[Session], T]) -> T:
        """Execute a function with a database session.
        
        Args:
            func: Function that takes a Session and returns a result
            
        Returns:
            Function result
        """
        def _wrapper():
            with Session(engine) as session:
                return func(session)
        return await run_in_thread(_wrapper)
    
    @staticmethod
    async def execute_many(funcs: list[Callable[[Session], T]]) -> list[T]:
        """Execute multiple functions with a shared session.
        
        Args:
            funcs: List of functions that take a Session
            
        Returns:
            List of results
        """
        def _wrapper():
            with Session(engine) as session:
                return [func(session) for func in funcs]
        return await run_in_thread(_wrapper)
    
    @staticmethod
    async def execute_with_commit(func: Callable[[Session], T]) -> T:
        """Execute a function and commit the transaction.
        
        Args:
            func: Function that takes a Session and returns a result
            
        Returns:
            Function result
        """
        def _wrapper():
            with Session(engine) as session:
                result = func(session)
                session.commit()
                return result
        return await run_in_thread(_wrapper)


class AsyncServiceWrapper:
    """Wrapper to call sync service methods from async context."""
    
    @staticmethod
    async def call(service_class, method_name: str, *args, **kwargs) -> Any:
        """Call a service method asynchronously.
        
        Args:
            service_class: Service class (e.g., UserService)
            method_name: Method name to call
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method
            
        Returns:
            Method result
        """
        def _execute(session: Session):
            service = service_class(session)
            method = getattr(service, method_name)
            return method(*args, **kwargs)
        return await AsyncDB.execute(_execute)


def cleanup_executor():
    """Shutdown the thread pool executor. Call on app shutdown."""
    _db_executor.shutdown(wait=True)
