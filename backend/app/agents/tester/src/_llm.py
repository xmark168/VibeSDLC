"""LLM instances for Tester agent (aligned with Developer V2).

Provides:
- Step-specific LLM instances (plan, implement, review, analyze)
- Skill-based model selection (get_llm_for_skills)
- Centralized retry logic (invoke_with_retry)
"""
import asyncio
import logging
import os
from functools import wraps
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.agents.tester.src.config import (
    MAX_RETRIES,
    RETRY_WAIT_MAX,
    RETRY_WAIT_MIN,
    DEFAULT_MODEL,
    FAST_MODEL,
    COMPLEX_MODEL,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Model Configuration (aligned with Developer V2)
# =============================================================================

MODELS = {
    "fast": FAST_MODEL,
    "medium": DEFAULT_MODEL,
    "complex": COMPLEX_MODEL,
}

# Default model configs per step
LLM_CONFIG = {
    "plan": {"model": MODELS["medium"], "temperature": 0.2, "timeout": 60},
    "implement": {"model": MODELS["medium"], "temperature": 0, "timeout": 90},
    "review": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30},
    "analyze": {"model": MODELS["medium"], "temperature": 0.2, "timeout": 40},
    "default": {"model": MODELS["medium"], "temperature": 0, "timeout": 40},
}

# Model selection by skill type (aligned with Developer V2)
SKILL_MODEL_MAP = {
    "unit-test": MODELS["complex"],      # Complex for component understanding
    "integration-test": MODELS["medium"], # Medium for API testing
    "debugging": MODELS["medium"],
}


# =============================================================================
# Model Selection Functions
# =============================================================================

def get_model_for_skills(skills: List[str]) -> str:
    """Select best model based on skills required for a task.
    
    Priority: complex > medium > fast
    If any skill requires complex model, use complex.
    """
    if not skills:
        return MODELS["medium"]
    
    has_complex = any(SKILL_MODEL_MAP.get(s) == MODELS["complex"] for s in skills)
    has_medium = any(SKILL_MODEL_MAP.get(s) == MODELS["medium"] for s in skills)
    
    if has_complex:
        return MODELS["complex"]
    elif has_medium:
        return MODELS["medium"]
    else:
        return MODELS["medium"]


def get_llm(step: str = "default") -> BaseChatModel:
    """Get LLM for a specific step.
    
    Uses ChatAnthropic for Claude models, ChatOpenAI for GPT models.
    Supports env var overrides: TESTER_MODEL_PLAN, TESTER_MODEL_IMPLEMENT, etc.
    """
    config = LLM_CONFIG.get(step, LLM_CONFIG["default"])
    
    # Allow env override: TESTER_MODEL_PLAN=gpt-4o
    env_model = os.getenv(f"TESTER_MODEL_{step.upper()}")
    if env_model:
        config = {**config, "model": env_model}
    
    model = config["model"]
    timeout = config.get("timeout", 40)
    
    return _create_llm(model, config.get("temperature", 0.2), timeout)


def get_llm_for_skills(skills: List[str], temperature: float = 0) -> BaseChatModel:
    """Get LLM based on skills required for a task (Developer V2 pattern).
    
    Selects model tier based on skill complexity:
    - unit-test -> complex (better component understanding)
    - integration-test -> medium (API testing)
    
    Args:
        skills: List of skill IDs for the task
        temperature: Temperature for generation (default 0 for code)
    
    Returns:
        LLM instance configured for the task
    """
    model = get_model_for_skills(skills)
    logger.info(f"[LLM] Selected {model} for skills: {skills}")
    return _create_llm(model, temperature, timeout=90)


def _create_llm(model: str, temperature: float, timeout: int) -> BaseChatModel:
    """Create LLM instance for given model."""
    # API keys and base URLs
    openai_base_url = os.getenv("TESTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    openai_api_key = os.getenv("TESTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    anthropic_base_url = os.getenv("TESTER_ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_API_BASE")
    anthropic_api_key = os.getenv("TESTER_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or openai_api_key
    
    # Use ChatAnthropic for Claude models
    if "claude" in model.lower():
        kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": 16384,
            "timeout": timeout,
            "max_retries": MAX_RETRIES,
        }
        if anthropic_base_url:
            kwargs["base_url"] = anthropic_base_url
        if anthropic_api_key:
            kwargs["api_key"] = anthropic_api_key
        return ChatAnthropic(**kwargs)
    
    # Use ChatOpenAI for GPT models (default)
    kwargs = {
        "model": model,
        "temperature": temperature,
        "timeout": timeout,
        "max_retries": MAX_RETRIES,
    }
    if openai_base_url:
        kwargs["base_url"] = openai_base_url
    if openai_api_key:
        kwargs["api_key"] = openai_api_key
    
    return ChatOpenAI(**kwargs)


# =============================================================================
# Retry Utilities (aligned with Developer V2)
# =============================================================================

async def invoke_with_retry(
    llm: BaseChatModel,
    messages: list,
    config: dict = None,
    max_retries: int = MAX_RETRIES,
):
    """Invoke LLM with retry mechanism (Developer V2 pattern).
    
    Args:
        llm: The LLM instance to use
        messages: List of messages to send
        config: Optional config dict (e.g., for langfuse)
        max_retries: Number of retry attempts (default: 3)
    
    Returns:
        LLM response
    """
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            if config:
                response = await llm.ainvoke(messages, config=config)
            else:
                response = await llm.ainvoke(messages)
            return response
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = min(RETRY_WAIT_MAX, RETRY_WAIT_MIN * (2 ** (attempt - 1)))
                logger.warning(f"[LLM] Attempt {attempt}/{max_retries} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[LLM] All {max_retries} attempts failed. Last error: {e}")
    
    raise last_error


async def invoke_structured_with_retry(
    llm: BaseChatModel,
    schema,
    messages: list,
    config: dict = None,
    max_retries: int = MAX_RETRIES,
):
    """Invoke LLM with structured output and retry.
    
    Args:
        llm: The LLM instance to use
        schema: Pydantic model for structured output
        messages: List of messages to send
        config: Optional config dict
        max_retries: Number of retry attempts
    
    Returns:
        Parsed structured output
    """
    structured_llm = llm.with_structured_output(schema)
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            if config:
                result = await structured_llm.ainvoke(messages, config=config)
            else:
                result = await structured_llm.ainvoke(messages)
            
            # Validate result
            if result and hasattr(result, 'content') and len(result.content) < 50:
                raise ValueError("Generated content too short")
            
            return result
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = min(RETRY_WAIT_MAX, RETRY_WAIT_MIN * (2 ** (attempt - 1)))
                logger.warning(f"[LLM] Structured attempt {attempt}/{max_retries} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[LLM] All {max_retries} structured attempts failed. Last error: {e}")
    
    raise last_error


# =============================================================================
# Pre-instantiated LLMs (backward compatibility)
# =============================================================================

plan_llm = get_llm("plan")
implement_llm = get_llm("implement")
review_llm = get_llm("review")
analyze_llm = get_llm("analyze")
default_llm = get_llm("default")

# Fast LLM for quick operations
fast_llm = _create_llm(MODELS["fast"], 0.1, 30)
