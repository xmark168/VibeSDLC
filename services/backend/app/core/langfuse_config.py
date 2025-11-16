"""LangFuse configuration and integration."""

import logging
from typing import Optional

try:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None
    CallbackHandler = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class LangFuseManager:
    """Manager for LangFuse integration."""

    def __init__(self):
        self.client: Optional[Langfuse] = None
        self.callback_handler: Optional[CallbackHandler] = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize LangFuse client and callback handler."""
        if self._initialized:
            return True

        if not LANGFUSE_AVAILABLE:
            logger.warning("LangFuse library not available. Tracing disabled.")
            return False

        if not all([settings.LANGFUSE_SECRET_KEY, settings.LANGFUSE_PUBLIC_KEY]):
            logger.warning("LangFuse credentials not provided. Tracing disabled.")
            return False

        try:
            self.client = Langfuse(
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                host=settings.LANGFUSE_HOST,
            )

            self.callback_handler = CallbackHandler(
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                host=settings.LANGFUSE_HOST,
            )

            self._initialized = True
            logger.info("LangFuse initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize LangFuse: {e}")
            return False

    def get_callback_handler(self) -> Optional[CallbackHandler]:
        """Get the LangFuse callback handler for LangChain."""
        if not self._initialized:
            self.initialize()
        return self.callback_handler

    def create_trace(self, name: str, **kwargs):
        """Create a new trace in LangFuse."""
        if not self.client:
            return None
        return self.client.trace(name=name, **kwargs)

    def flush(self):
        """Flush pending traces to LangFuse."""
        if self.client:
            self.client.flush()


# Global LangFuse manager instance
langfuse_manager = LangFuseManager()
