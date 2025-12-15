import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TypeVar, Callable, Any, ParamSpec

from sqlmodel import Session
from app.core.db import engine

T = TypeVar('T')
P = ParamSpec('P')

_db_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="db_worker")


async def run_in_thread(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
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


class DB:
    @staticmethod
    async def execute(func: Callable[[Session], T]) -> T:
        def _wrapper():
            with Session(engine) as session:
                return func(session)
        return await run_in_thread(_wrapper)
    
    @staticmethod
    async def execute_many(funcs: list[Callable[[Session], T]]) -> list[T]:
        def _wrapper():
            with Session(engine) as session:
                return [func(session) for func in funcs]
        return await run_in_thread(_wrapper)
    
    @staticmethod
    async def execute_with_commit(func: Callable[[Session], T]) -> T:
        def _wrapper():
            with Session(engine) as session:
                result = func(session)
                session.commit()
                return result
        return await run_in_thread(_wrapper)


class AsyncServiceWrapper:
    @staticmethod
    async def call(service_class, method_name: str, *args, **kwargs) -> Any:
        def _execute(session: Session):
            service = service_class(session)
            method = getattr(service, method_name)
            return method(*args, **kwargs)
        return await DB.execute(_execute)


def cleanup_executor():
    _db_executor.shutdown(wait=True)
