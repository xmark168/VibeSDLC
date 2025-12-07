"""LLM instances with model selection by task/skill type."""
import os
import logging
from functools import wraps
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Retry config
MAX_RETRIES = 3
RETRY_WAIT_MIN = 1  
RETRY_WAIT_MAX = 10  

# Model tiers
MODELS = {
    "fast": "claude-sonnet-4-5-20250929",      # Simple/fast tasks
    "medium": "claude-sonnet-4-5-20250929",   # Standard tasks (API, DB)
    "complex": "claude-opus-4-5-20251101",    # Complex tasks (UI design, debug)
}

# Default model configs per step
LLM_CONFIG = {
    # Fast tasks - use haiku
    "router": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30},
    "clarify": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30},
    "respond": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30},
    
    # Planning - use medium (sonnet)
    "analyze": {"model": MODELS["medium"], "temperature": 0.2, "timeout": 40},
    "plan": {"model": MODELS["medium"], "temperature": 0.2, "timeout": 60},
    
    # Implementation - default medium, can be overridden by skill type
    "implement": {"model": MODELS["medium"], "temperature": 0, "timeout": 60},
    "debug": {"model": MODELS["complex"], "temperature": 0.2, "timeout": 40},
    
    # Structured output tasks
    "structured": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 35},
    "review": {"model": MODELS["medium"], "temperature": 0.1, "timeout": 30},
    "summarize": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30},
}

# Model selection by skill type (for implement step)
SKILL_MODEL_MAP = {
    # Complex UI tasks -> opus (best quality)
    "frontend-design": MODELS["complex"],
    "frontend-component": MODELS["complex"],
    
    # Standard tasks -> sonnet (good balance)
    "api-route": MODELS["medium"],
    "database-model": MODELS["medium"],
    "server-action": MODELS["medium"],
    "authentication": MODELS["medium"],
    "state-management": MODELS["medium"],
    
    # Debug needs complex reasoning
    "debugging": MODELS["complex"],
}


def get_model_for_skills(skills: list[str]) -> str:
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
        return MODELS["medium"]  # Default to medium


def get_llm(step: str) -> BaseChatModel:
    """Get LLM for a specific step with timeout. Uses ChatAnthropic for Claude, ChatOpenAI for GPT."""
    config = LLM_CONFIG.get(step, LLM_CONFIG["implement"])
    
    # Allow env override: DEVV2_MODEL_PLAN=gpt-4o
    env_model = os.getenv(f"DEVV2_MODEL_{step.upper()}")
    if env_model:
        config = {**config, "model": env_model}
    
    model = config["model"]
    timeout = config.get("timeout", 40)
    
    # API keys and base URLs
    openai_base_url = os.getenv("OPENAI_API_BASE")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_base_url = os.getenv("ANTHROPIC_API_BASE", "https://ai.megallm.io")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or openai_api_key
    
    # Use ChatAnthropic for Claude models
    if "claude" in model.lower():
        kwargs = {
            "model": model,
            "temperature": config.get("temperature", 0.2),
            "max_tokens": 16384,  # Claude requires max_tokens, set high
            "timeout": timeout,
            "max_retries": MAX_RETRIES,
        }
        if anthropic_base_url:
            kwargs["base_url"] = anthropic_base_url
        if anthropic_api_key:
            kwargs["api_key"] = anthropic_api_key
        return ChatAnthropic(**kwargs)
    
    # Use ChatOpenAI for GPT models - no max_tokens limit
    kwargs = {
        "model": model,
        "temperature": config.get("temperature", 0.2),
        "timeout": timeout,
        "max_retries": MAX_RETRIES,
        # No max_tokens - let model use its full capacity
    }
    if openai_base_url:
        kwargs["base_url"] = openai_base_url
    if openai_api_key:
        kwargs["api_key"] = openai_api_key
    return ChatOpenAI(**kwargs)


def get_llm_for_skills(skills: list[str], temperature: float = 0) -> BaseChatModel:
    """Get LLM based on skills required for a task.
    
    Selects model tier based on skill complexity:
    - frontend-design, frontend-component, debugging -> opus (complex)
    - api-route, database-model, etc. -> sonnet (medium)
    
    Args:
        skills: List of skill IDs for the task
        temperature: Temperature for generation (default 0 for code)
    
    Returns:
        LLM instance configured for the task
    """
    model = get_model_for_skills(skills)
    
    # API keys and base URLs
    anthropic_base_url = os.getenv("ANTHROPIC_API_BASE", "https://ai.megallm.io")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    kwargs = {
        "model": model,
        "temperature": temperature,
        "max_tokens": 16384,
        "timeout": 60,
        "max_retries": MAX_RETRIES,
    }
    if anthropic_base_url:
        kwargs["base_url"] = anthropic_base_url
    if anthropic_api_key:
        kwargs["api_key"] = anthropic_api_key
    
    logger.info(f"[LLM] Selected {model} for skills: {skills}")
    return ChatAnthropic(**kwargs)


# Retry decorator for LLM calls
def with_retry(max_attempts: int = MAX_RETRIES):
    """Decorator to add retry logic to async LLM calls."""
    def decorator(func):
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
            retry=retry_if_exception_type((TimeoutError, ConnectionError, Exception)),
            before_sleep=lambda retry_state: logger.warning(
                f"[LLM] Retry {retry_state.attempt_number}/{max_attempts} after error: {retry_state.outcome.exception()}"
            ),
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def invoke_with_retry(llm: BaseChatModel, messages: list, config: dict = None, max_retries: int = MAX_RETRIES):
    """Invoke LLM with retry mechanism.
    
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
                import asyncio
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[LLM] All {max_retries} attempts failed. Last error: {e}")
    
    raise last_error


# Pre-instantiated for backward compatibility
fast_llm = get_llm("router")
code_llm = get_llm("implement")

# Step-specific LLMs (optional, for fine-tuning)
router_llm = get_llm("router")
analyze_llm = get_llm("analyze")
plan_llm = get_llm("plan")
implement_llm = get_llm("implement")
debug_llm = get_llm("debug")
