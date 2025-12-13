import asyncio
from typing import TypeVar, Callable, Any
from sqlmodel import Session
from app.core.db import engine

T = TypeVar('T')


async def run_in_thread(func: Callable[..., T], *args, **kwargs) -> T:
    return await asyncio.to_thread(func, *args, **kwargs)


class AsyncDB:
    @staticmethod
    async def execute(func: Callable[[Session], T]) -> T:
        def _wrapper():
            with Session(engine) as session:
                return func(session)
        return await asyncio.to_thread(_wrapper)
    
    @staticmethod
    async def execute_many(funcs: list[Callable[[Session], T]]) -> list[T]:
        def _wrapper():
            with Session(engine) as session:
                return [func(session) for func in funcs]
        return await asyncio.to_thread(_wrapper)


class AsyncServiceWrapper:
    @staticmethod
    async def _wrap_call(service_class, method_name: str, *args, **kwargs):
        def _execute(session: Session):
            service = service_class(session)
            method = getattr(service, method_name)
            return method(*args, **kwargs)
        return await AsyncDB.execute(_execute)
