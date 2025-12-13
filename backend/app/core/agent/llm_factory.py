"""Centralized LLM factory with LangChain callback-based token tracking.
"""

import logging
from contextvars import ContextVar
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

MODELS = {
    "fast": "claude-haiku-4-5-20251001",
    "medium": "claude-sonnet-4-5-20250929",
    "complex": "claude-opus-4-5-20251101",
}

STEP_CONFIG = {
    # Fast tier
    "router": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30, "max_tokens": 4096},
    "clarify": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30, "max_tokens": 4096},
    "respond": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30, "max_tokens": 4096},
    "review": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30, "max_tokens": 8192},
    
    # Medium tier
    "analyze": {"model": MODELS["medium"], "temperature": 0.1, "timeout": 60, "max_tokens": 8192},
    "plan": {"model": MODELS["medium"], "temperature": 0.1, "timeout": 90, "max_tokens": 8192},
    "implement": {"model": MODELS["medium"], "temperature": 0, "timeout": 120, "max_tokens": 16384},
    "debug": {"model": MODELS["medium"], "temperature": 0.2, "timeout": 90, "max_tokens": 16384},
    
    # Complex tier
    "complex": {"model": MODELS["complex"], "temperature": 0, "timeout": 180, "max_tokens": 16384},
    
    # Default
    "default": {"model": MODELS["medium"], "temperature": 0.2, "timeout": 60, "max_tokens": 8192},
}

MAX_RETRIES = 3

# =============================================================================
# TOKEN TRACKING (thread-safe with ContextVar)
# =============================================================================

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
    temperature: float = 0.2,
    max_tokens: int = 8192,
    timeout: int = 60,
    max_retries: int = MAX_RETRIES,
    track_tokens: bool = True,
) -> BaseChatModel:
    """Create ChatAnthropic instance.
    
    Args:
        model: Model name
        temperature: Sampling temperature
        max_tokens: Max tokens in response
        timeout: Request timeout
        max_retries: Retry attempts
        track_tokens: Whether to inject token tracking callback
    """
    from app.core.config import settings
    
    callbacks = [_token_callback] if track_tokens else None
    
    return ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        base_url=settings.ANTHROPIC_API_BASE,
        api_key=settings.ANTHROPIC_API_KEY,
        callbacks=callbacks,
    )


def get_llm(step: str) -> BaseChatModel:
    """Get LLM for a step with automatic token tracking.
    
    Args:
        step: Step name (router, plan, implement, etc.)
    """
    config = STEP_CONFIG.get(step, STEP_CONFIG["default"])
    return create_llm(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        timeout=config["timeout"],
    )


def get_raw_llm(step: str) -> BaseChatModel:
    """Get LLM without token tracking (for special cases)."""
    config = STEP_CONFIG.get(step, STEP_CONFIG["default"])
    return create_llm(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        timeout=config["timeout"],
        track_tokens=False,
    )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_fast_llm(**kwargs) -> BaseChatModel:
    """Create fast (Haiku) LLM."""
    defaults = {"temperature": 0.1, "timeout": 30, "max_tokens": 4096}
    defaults.update(kwargs)
    return create_llm(MODELS["fast"], **defaults)


def create_medium_llm(**kwargs) -> BaseChatModel:
    """Create medium (Sonnet) LLM."""
    defaults = {"temperature": 0.2, "timeout": 60, "max_tokens": 8192}
    defaults.update(kwargs)
    return create_llm(MODELS["medium"], **defaults)


def create_complex_llm(**kwargs) -> BaseChatModel:
    """Create complex (Opus) LLM."""
    defaults = {"temperature": 0.2, "timeout": 120, "max_tokens": 16384}
    defaults.update(kwargs)
    return create_llm(MODELS["complex"], **defaults)
