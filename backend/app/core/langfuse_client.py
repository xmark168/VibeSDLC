"""Langfuse client singleton for agent tracing."""

import logging
from typing import Optional
from langfuse import Langfuse
from app.core.config import settings

logger = logging.getLogger(__name__)

_langfuse_client: Optional[Langfuse] = None


def get_langfuse_client() -> Optional[Langfuse]:
    """Get or create Langfuse client singleton.
    
    Returns None if Langfuse is disabled or not configured.
    """
    global _langfuse_client
    
    if not settings.LANGFUSE_ENABLED:
        return None
    
    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        logger.warning("Langfuse keys not configured, tracing disabled")
        return None
    
    if _langfuse_client is None:
        try:
            _langfuse_client = Langfuse(
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                host=settings.LANGFUSE_HOST,
            )
            logger.info("Langfuse client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            return None
    
    return _langfuse_client


def flush_langfuse():
    """Flush pending Langfuse events."""
    if _langfuse_client:
        _langfuse_client.flush()
