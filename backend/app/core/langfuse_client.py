"""Langfuse client for LangChain tracing.

Simple usage:
    from langfuse.langchain import CallbackHandler
    
    handler = CallbackHandler()
    response = chain.invoke({"input": "..."}, config={"callbacks": [handler]})
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Check if Langfuse is available
LANGFUSE_AVAILABLE = False
_CallbackHandler = None

try:
    from langfuse.langchain import CallbackHandler as _CallbackHandler
    LANGFUSE_AVAILABLE = True
    logger.info("Langfuse CallbackHandler loaded")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Langfuse not available: {e}")


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def get_langfuse_client():
    """Get Langfuse client instance.
    
    Returns:
        Langfuse client or None
    """
    if not LANGFUSE_AVAILABLE:
        return None
    
    try:
        from langfuse import get_client
        return get_client()
    except Exception as e:
        logger.debug(f"get_langfuse_client: {e}")
        return None


def get_langfuse_handler():
    """Get a new Langfuse CallbackHandler for LangChain tracing.
    
    Returns:
        CallbackHandler or None if not available
    """
    if not LANGFUSE_AVAILABLE or _CallbackHandler is None:
        return None
    
    try:
        return _CallbackHandler()
    except Exception as e:
        logger.debug(f"Failed to create CallbackHandler: {e}")
        return None


def get_langchain_callback(
    trace_name: str = None,
    user_id: str = None,
    session_id: str = None,
    tags: List[str] = None,
    metadata: Dict[str, Any] = None,
):
    """Get LangChain callback handler (alias for get_langfuse_handler).
    
    Returns:
        CallbackHandler or None
    """
    return get_langfuse_handler()


def flush_langfuse():
    """Flush pending Langfuse events."""
    try:
        from langfuse import get_client
        client = get_client()
        if client:
            client.flush()
    except Exception as e:
        logger.debug(f"Langfuse flush: {e}")


def shutdown_langfuse():
    """Shutdown Langfuse client."""
    try:
        from langfuse import get_client
        client = get_client()
        if client:
            client.shutdown()
    except Exception as e:
        logger.debug(f"Langfuse shutdown: {e}")


# =============================================================================
# CONTEXT FUNCTIONS (stubs for backward compatibility)
# =============================================================================

def get_langfuse_context():
    """Get current Langfuse context (stub).
    
    Returns:
        None - context is managed automatically by CallbackHandler
    """
    return None


def update_current_trace(
    name: str = None,
    user_id: str = None,
    session_id: str = None,
    metadata: Dict[str, Any] = None,
    tags: List[str] = None,
    **kwargs
) -> bool:
    """Update current trace (stub - not needed with CallbackHandler).
    
    Returns:
        False - use metadata in config instead
    """
    return False


def update_current_observation(
    output: Any = None,
    metadata: Dict[str, Any] = None,
    **kwargs
) -> bool:
    """Update current observation (stub - not needed with CallbackHandler).
    
    Returns:
        False - CallbackHandler handles this automatically
    """
    return False


def score_current(
    name: str,
    value: float,
    comment: str = None,
    data_type: str = "NUMERIC"
) -> bool:
    """Score current trace (stub).
    
    Returns:
        False - use langfuse client directly for scoring
    """
    return False


def create_session_id(project_id: str, conversation_id: str = None) -> str:
    """Create session ID for grouping traces.
    
    Args:
        project_id: Project UUID string
        conversation_id: Optional conversation ID
        
    Returns:
        Session ID string
    """
    if conversation_id:
        return f"conv_{conversation_id[:50]}"
    return f"proj_{project_id[:50]}"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_llm_usage(response) -> Dict[str, Any]:
    """Extract token usage from LLM response."""
    usage = {}
    
    if hasattr(response, "usage") and response.usage:
        usage["input"] = getattr(response.usage, "prompt_tokens", 0)
        usage["output"] = getattr(response.usage, "completion_tokens", 0)
        usage["total"] = getattr(response.usage, "total_tokens", 0)
    elif hasattr(response, "response_metadata"):
        meta = response.response_metadata
        if "token_usage" in meta:
            usage["input"] = meta["token_usage"].get("prompt_tokens", 0)
            usage["output"] = meta["token_usage"].get("completion_tokens", 0)
            usage["total"] = meta["token_usage"].get("total_tokens", 0)
    
    return usage


def format_chat_messages(messages: List[Any]) -> List[Dict[str, str]]:
    """Format messages for Langfuse input."""
    formatted = []
    for msg in messages:
        if isinstance(msg, dict):
            formatted.append(msg)
        elif hasattr(msg, "type") and hasattr(msg, "content"):
            role_map = {"human": "user", "ai": "assistant", "system": "system"}
            role = role_map.get(msg.type, msg.type)
            formatted.append({"role": role, "content": str(msg.content)})
        elif hasattr(msg, "role") and hasattr(msg, "content"):
            formatted.append({"role": msg.role, "content": str(msg.content)})
    return formatted
