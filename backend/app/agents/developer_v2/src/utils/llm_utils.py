"""LLM execution utilities for Developer V2."""

import logging
import time
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class FileCache:
    """Simple in-memory file cache."""
    _cache: Dict[str, Tuple[str, float]] = {}
    TTL = 120
    
    @classmethod
    def get(cls, file_path: str) -> Optional[str]:
        if file_path in cls._cache:
            content, timestamp = cls._cache[file_path]
            if time.time() - timestamp < cls.TTL:
                return content
            del cls._cache[file_path]
        return None
    
    @classmethod
    def set(cls, file_path: str, content: str) -> None:
        cls._cache[file_path] = (content, time.time())
    
    @classmethod
    def invalidate(cls, file_path: str) -> None:
        if file_path in cls._cache:
            del cls._cache[file_path]
    
    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()


file_cache = FileCache()


def get_langfuse_config(state: dict, run_name: str) -> dict:
    handler = state.get("langfuse_handler")
    if handler:
        return {"callbacks": [handler], "run_name": run_name}
    return {"run_name": run_name}


def flush_langfuse(state: dict) -> None:
    langfuse_client = state.get("langfuse_client")
    if langfuse_client:
        try:
            langfuse_client.flush()
        except Exception:
            pass


def get_langfuse_span(state: dict, name: str, input_data: dict = None):
    """Get Langfuse span if handler available."""
    if not state.get("langfuse_handler"):
        return None
    try:
        from langfuse import get_client
        return get_client().span(name=name, input=input_data or {})
    except Exception:
        return None
