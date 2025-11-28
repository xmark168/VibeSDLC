"""Langfuse utilities for backward compatibility."""

import logging

logger = logging.getLogger(__name__)


def get_langfuse_client():
    """Get Langfuse client instance."""
    try:
        from langfuse import get_client
        return get_client()
    except Exception:
        return None


def get_langfuse_handler():
    """Get Langfuse CallbackHandler for LangChain."""
    try:
        from langfuse.langchain import CallbackHandler
        return CallbackHandler()
    except Exception:
        return None


def flush_langfuse():
    """Flush pending events."""
    try:
        from langfuse import get_client
        get_client().flush()
    except Exception:
        pass


def shutdown_langfuse():
    """Shutdown Langfuse."""
    try:
        from langfuse import get_client
        get_client().shutdown()
    except Exception:
        pass


# Stubs for backward compatibility
def get_langfuse_context():
    return None

def update_current_trace(**kwargs):
    return False

def update_current_observation(**kwargs):
    return False

def score_current(name, value, **kwargs):
    return False

def create_session_id(project_id, conversation_id=None):
    return f"proj_{project_id[:50]}" if project_id else "unknown"

def format_llm_usage(response):
    return {}

def format_chat_messages(messages):
    return []

def get_langchain_callback(**kwargs):
    return get_langfuse_handler()
