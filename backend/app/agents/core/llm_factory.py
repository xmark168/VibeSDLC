"""Centralized LLM factory with LangChain callback-based token tracking.
"""

import logging
import threading
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import LLMResult

from app.core.config import llm_settings

logger = logging.getLogger(__name__)

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

MODELS = {
    "fast": "claude-haiku-4-5-20251001",
    "medium": "claude-sonnet-4-5-20250929",
    "complex": "claude-opus-4-5-20251101",
}

# =============================================================================
# TOKEN TRACKING - Thread-Safe Global Counter
# =============================================================================
# FIXED: Replaced ContextVar with global counter to work across async contexts
# ContextVar was causing token loss when LLM callbacks ran in different context

class TokenCounter:
    """Thread-safe global token counter that works across async contexts."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._tokens = 0
        self._calls = 0
    
    def reset(self):
        """Reset counters to zero."""
        with self._lock:
            self._tokens = 0
            self._calls = 0
    
    def add_tokens(self, tokens: int):
        """Add tokens and increment call count."""
        with self._lock:
            self._tokens += tokens
            self._calls += 1
    
    def get_tokens(self) -> int:
        """Get total tokens counted."""
        with self._lock:
            return self._tokens
    
    def get_calls(self) -> int:
        """Get total LLM calls counted."""
        with self._lock:
            return self._calls

# Global singleton counter
_token_counter = TokenCounter()


def get_token_count() -> int:
    """Get total tokens used (thread-safe, works across async contexts)."""
    count = _token_counter.get_tokens()
    logger.info(f"[TOKEN_DEBUG] get_token_count() → {count}")
    return count


def get_llm_call_count() -> int:
    """Get total LLM calls (thread-safe, works across async contexts)."""
    count = _token_counter.get_calls()
    logger.info(f"[TOKEN_DEBUG] get_llm_call_count() → {count}")
    return count


def reset_token_count() -> None:
    """Reset token counter for new task."""
    logger.info(f"[TOKEN_DEBUG] reset_token_count() BEFORE → tokens={_token_counter.get_tokens()}, calls={_token_counter.get_calls()}")
    _token_counter.reset()
    logger.info(f"[TOKEN_DEBUG] reset_token_count() AFTER → tokens={_token_counter.get_tokens()}, calls={_token_counter.get_calls()}")


class TokenTrackingCallback(BaseCallbackHandler):
    """LangChain callback to track token usage from all LLM calls."""
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM call ends - extract and track tokens."""
        tokens = 0
        
        # DEBUG: Log callback execution
        logger.info(f"[TOKEN_DEBUG] on_llm_end called")
        
        # Try to get tokens from llm_output (standard location)
        if response.llm_output:
            usage = response.llm_output.get('usage', {})
            tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
            logger.info(f"[TOKEN_DEBUG] llm_output.usage: {usage}, tokens={tokens}")
        
        # Fallback: try to get from generations metadata
        if tokens == 0 and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, 'generation_info') and gen.generation_info:
                        usage = gen.generation_info.get('usage', {})
                        tokens += usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
                        if tokens > 0:
                            logger.info(f"[TOKEN_DEBUG] generation_info.usage: {usage}, tokens={tokens}")
        
        # DEBUG: Log extraction result
        logger.info(f"[TOKEN_DEBUG] Extracted {tokens} tokens from LLM response")
        
        # Update global counter (thread-safe, works across async contexts)
        if tokens > 0:
            before_tokens = _token_counter.get_tokens()
            logger.info(f"[TOKEN_DEBUG] TokenCounter BEFORE: {before_tokens}")
            _token_counter.add_tokens(tokens)
            after_tokens = _token_counter.get_tokens()
            logger.info(f"[TOKEN_DEBUG] TokenCounter AFTER: {after_tokens}")
        else:
            # Still increment call count even if no tokens
            _token_counter.add_tokens(0)
        
        logger.info(f"[TOKEN_DEBUG] LLM call tracked: +{tokens} tokens (total: {_token_counter.get_tokens()}, calls: {_token_counter.get_calls()})")


# Singleton callback instance
_token_callback = TokenTrackingCallback()


# =============================================================================
# LLM CREATION FUNCTIONS
# =============================================================================

def create_llm(
    model: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
    track_tokens: bool = True,
) -> BaseChatModel:
    """Create ChatAnthropic instance. """
    # Apply defaults from settings
    if temperature is None:
        temperature = llm_settings.DEFAULT_TEMPERATURE
    if max_tokens is None:
        max_tokens = llm_settings.DEFAULT_MAX_TOKENS
    if timeout is None:
        timeout = llm_settings.DEFAULT_TIMEOUT
    if max_retries is None:
        max_retries = llm_settings.MAX_RETRIES
    
    from app.core.config import settings
    
    callbacks = [_token_callback] if track_tokens else None
    
    return ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        base_url=llm_settings.API_BASE or settings.ANTHROPIC_API_BASE,
        api_key=llm_settings.API_KEY or settings.ANTHROPIC_API_KEY,
        callbacks=callbacks,
    )


def create_fast_llm(**kwargs) -> BaseChatModel:
    """Create fast (Haiku) LLM."""
    defaults = {"temperature": 0.1, "timeout": 30, "max_tokens": 4096}
    defaults.update(kwargs)
    return create_llm(MODELS["fast"], **defaults)


def create_medium_llm(**kwargs) -> BaseChatModel:
    """Create medium (Sonnet) LLM."""
    defaults = {"temperature": 0.1, "timeout": 60, "max_tokens": 8192}
    defaults.update(kwargs)
    return create_llm(MODELS["medium"], **defaults)


def create_complex_llm(**kwargs) -> BaseChatModel:
    """Create complex (Opus) LLM."""
    defaults = {"temperature": 0.1, "timeout": 120, "max_tokens": 16384}
    defaults.update(kwargs)
    return create_llm(MODELS["complex"], **defaults)
