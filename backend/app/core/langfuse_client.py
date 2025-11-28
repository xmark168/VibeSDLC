"""Langfuse client singleton for agent tracing.

Provides:
- Singleton client management (Langfuse v3 API)
- Helper functions for tracing, generations, scoring
- Session-based conversation tracking

Langfuse v3 uses OpenTelemetry-based API:
- langfuse.start_as_current_span() for spans
- langfuse.start_as_current_generation() for LLM generations
- @observe decorator for automatic tracing
"""

import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None

from app.core.config import settings

logger = logging.getLogger(__name__)

_langfuse_client: Optional[Langfuse] = None
_langfuse_initialized: bool = False


def get_langfuse_client() -> Optional[Langfuse]:
    global _langfuse_client, _langfuse_initialized
    
    if _langfuse_initialized:
        return _langfuse_client
    
    _langfuse_initialized = True
    
    if not settings.LANGFUSE_ENABLED:
        return None

    try:
        _langfuse_client = Langfuse(
            secret_key=settings.LANGFUSE_SECRET_KEY,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            host=settings.LANGFUSE_BASE_URL,
        )
        logger.info("Langfuse client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse: {e}")
        _langfuse_client = None
    
    return _langfuse_client


def flush_langfuse():
    """Flush pending Langfuse events."""
    if _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception as e:
            logger.warning(f"Failed to flush Langfuse: {e}")


def create_session_id(project_id: str, conversation_id: str = None) -> str:
    """Create a session ID for conversation tracking.
    
    Session groups related traces together in Langfuse UI.
    
    Args:
        project_id: Project UUID string
        conversation_id: Optional conversation/thread ID
        
    Returns:
        Session ID string (max 200 chars, US-ASCII)
    """
    if conversation_id:
        return f"conv_{conversation_id[:50]}"
    return f"proj_{project_id[:50]}"


def score_trace(
    trace_id: str,
    name: str,
    value: float,
    comment: str = None,
    data_type: str = "NUMERIC"
) -> bool:
    """Score a trace for evaluation.
    """
    client = get_langfuse_client()
    if not client:
        return False
    
    try:
        client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
            data_type=data_type
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to score trace {trace_id}: {e}")
        return False


def format_llm_usage(response) -> Dict[str, Any]:
    """Extract token usage from LLM response.
    """
    usage = {"unit": "TOKENS"}
    
    # OpenAI response format
    if hasattr(response, "usage") and response.usage:
        usage["input"] = getattr(response.usage, "prompt_tokens", 0)
        usage["output"] = getattr(response.usage, "completion_tokens", 0)
        usage["total"] = getattr(response.usage, "total_tokens", 0)
    # LangChain AIMessage format
    elif hasattr(response, "response_metadata"):
        meta = response.response_metadata
        if "token_usage" in meta:
            usage["input"] = meta["token_usage"].get("prompt_tokens", 0)
            usage["output"] = meta["token_usage"].get("completion_tokens", 0)
            usage["total"] = meta["token_usage"].get("total_tokens", 0)
    # Dict format
    elif isinstance(response, dict):
        if "usage" in response:
            usage["input"] = response["usage"].get("prompt_tokens", 0)
            usage["output"] = response["usage"].get("completion_tokens", 0)
            usage["total"] = response["usage"].get("total_tokens", 0)
    
    return usage


def format_chat_messages(messages: List[Any]) -> List[Dict[str, str]]:
    """Format messages for Langfuse generation input.
    """
    formatted = []
    for msg in messages:
        if isinstance(msg, dict):
            formatted.append(msg)
        elif hasattr(msg, "type") and hasattr(msg, "content"):
            # LangChain message
            role_map = {"human": "user", "ai": "assistant", "system": "system"}
            role = role_map.get(msg.type, msg.type)
            formatted.append({"role": role, "content": msg.content})
        elif hasattr(msg, "role") and hasattr(msg, "content"):
            formatted.append({"role": msg.role, "content": msg.content})
    return formatted
