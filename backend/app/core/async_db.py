"""Async database operations wrapper.

This module provides async-safe database access by wrapping sync SQLModel
operations in thread pool execution.
"""

import asyncio
from typing import TypeVar, Callable, Any
from sqlmodel import Session
from app.core.db import engine

T = TypeVar('T')


async def run_in_thread(func: Callable[..., T], *args, **kwargs) -> T:
    """Execute sync function in thread pool.
    
    Args:
        func: Sync function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Result from function
        
    Example:
        result = await run_in_thread(some_sync_function, arg1, arg2)
    """
    return await asyncio.to_thread(func, *args, **kwargs)


class AsyncDB:
    """Async database operations wrapper.
    
    Wraps sync SQLModel/SQLAlchemy operations in asyncio.to_thread()
    to prevent blocking the event loop.
    """
    
    @staticmethod
    async def execute(func: Callable[[Session], T]) -> T:
        """Execute function with fresh session in thread pool.
        
        Creates a new session, passes it to function, and ensures
        proper cleanup after execution.
        
        Args:
            func: Function that takes Session and returns result
            
        Returns:
            Result from function
            
        Example:
            def _create_user(session: Session) -> User:
                user = User(name="Alice")
                session.add(user)
                session.commit()
                session.refresh(user)
                return user
            
            user = await AsyncDB.execute(_create_user)
        """
        def _wrapper():
            with Session(engine) as session:
                return func(session)
        
        return await asyncio.to_thread(_wrapper)
    
    @staticmethod
    async def execute_many(funcs: list[Callable[[Session], T]]) -> list[T]:
        """Execute multiple functions with same session in thread pool.
        
        Useful for related operations that should share a session/transaction.
        
        Args:
            funcs: List of functions that take Session
            
        Returns:
            List of results from each function
            
        Example:
            results = await AsyncDB.execute_many([
                lambda s: service1.operation(s),
                lambda s: service2.operation(s),
            ])
        """
        def _wrapper():
            with Session(engine) as session:
                return [func(session) for func in funcs]
        
        return await asyncio.to_thread(_wrapper)


class AsyncServiceWrapper:
    """Base class for async service wrappers.
    
    Subclass this to create async wrappers for sync services.
    """
    
    @staticmethod
    async def _wrap_call(service_class, method_name: str, *args, **kwargs):
        """Generic wrapper for service method calls.
        
        Args:
            service_class: Service class to instantiate
            method_name: Method name to call
            *args: Arguments for the method
            **kwargs: Keyword arguments for the method
            
        Returns:
            Result from service method
        """
        def _execute(session: Session):
            service = service_class(session)
            method = getattr(service, method_name)
            return method(*args, **kwargs)
        
        return await AsyncDB.execute(_execute)
