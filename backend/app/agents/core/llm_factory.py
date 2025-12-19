"""Centralized LLM factory with LangChain callback-based token tracking.
"""

import logging
from contextvars import ContextVar
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

_token_count: ContextVar[int] = ContextVar('token_count', default=0)
_llm_call_count: ContextVar[int] = ContextVar('llm_call_count', default=0)


def get_token_count() -> int:
    """Get total tokens used in current context."""
    return _token_count.get()


def get_llm_call_count() -> int:
    """Get total LLM calls in current context."""
    return _llm_call_count.get()


def reset_token_count() -> None:
    """Reset token counter for new task."""
    _token_count.set(0)
    _llm_call_count.set(0)


class TokenTrackingCallback(BaseCallbackHandler):
    """LangChain callback to track token usage from all LLM calls."""
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM call ends - extract and track tokens."""
        tokens = 0
        
        # Try to get tokens from llm_output (standard location)
        if response.llm_output:
            usage = response.llm_output.get('usage', {})
            tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
        
        # Fallback: try to get from generations metadata
        if tokens == 0 and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, 'generation_info') and gen.generation_info:
                        usage = gen.generation_info.get('usage', {})
                        tokens += usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
        
        # Update counters
        if tokens > 0:
            current = _token_count.get()
            _token_count.set(current + tokens)
        
        current_calls = _llm_call_count.get()
        _llm_call_count.set(current_calls + 1)
        
        logger.debug(f"[TOKEN] LLM call tracked: +{tokens} tokens (total: {_token_count.get()})")


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
