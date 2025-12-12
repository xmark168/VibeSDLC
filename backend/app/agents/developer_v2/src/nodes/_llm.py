"""LLM instances with model selection."""
import os
import logging
from functools import wraps
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.agents.developer_v2.src.config import MAX_RETRIES, RETRY_WAIT_MIN, RETRY_WAIT_MAX
from app.core.config import settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_BASE = settings.ANTHROPIC_API_BASE
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY 

MODELS = {
    "fast": "claude-haiku-4-5-20251001",  
    "medium": "claude-sonnet-4-5-20250929",
    "complex": "claude-opus-4-5-20251101",
}

LLM_CONFIG = {
    "router": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30},
    "clarify": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30},
    "respond": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30},
    "analyze": {"model": MODELS["medium"], "temperature": 0.1, "timeout": 40},
    "plan": {"model": MODELS["medium"], "temperature": 0.1, "timeout": 60},
    "implement": {"model": MODELS["medium"], "temperature": 0, "timeout": 60},
    "debug": {"model": MODELS["medium"], "temperature": 0.2, "timeout": 40},
    "review": {"model": MODELS["fast"], "temperature": 0.1, "timeout": 30},
}

SKILL_MODEL_MAP = {
    "frontend-design": MODELS["medium"],
    "frontend-component": MODELS["medium"],
    "api-route": MODELS["medium"],
    "database-model": MODELS["medium"],
    "database-seed": MODELS["medium"],
    "server-action": MODELS["medium"],
    "authentication": MODELS["medium"],
    "state-management": MODELS["medium"],
    "debugging": MODELS["medium"],
}


def get_model_for_skills(skills: list[str]) -> str:
    """Select model based on skills. Priority: complex > medium > fast."""
    if not skills:
        return MODELS["medium"]
    if any(SKILL_MODEL_MAP.get(s) == MODELS["complex"] for s in skills):
        return MODELS["complex"]
    if any(SKILL_MODEL_MAP.get(s) == MODELS["medium"] for s in skills):
        return MODELS["medium"]
    return MODELS["medium"]


def get_llm(step: str) -> BaseChatModel:
    """Get LLM for a specific step."""
    config = LLM_CONFIG.get(step, LLM_CONFIG["implement"])
    env_model = os.getenv(f"DEVV2_MODEL_{step.upper()}")
    if env_model:
        config = {**config, "model": env_model}
    
    kwargs = {
        "model": config["model"],
        "temperature": config.get("temperature", 0.2),
        "max_tokens": 8192,
        "timeout": config.get("timeout", 40),
        "max_retries": MAX_RETRIES,
        "base_url": ANTHROPIC_API_BASE,
        "api_key": ANTHROPIC_API_KEY,
    }
    return ChatAnthropic(**kwargs)


def get_llm_for_skills(skills: list[str], temperature: float = 0) -> BaseChatModel:
    """Get LLM based on skills required."""
    model = get_model_for_skills(skills)
    
    kwargs = {
        "model": model,
        "temperature": temperature,
        "max_tokens": 16384,
        "timeout": 60,
        "max_retries": MAX_RETRIES,
        "base_url": ANTHROPIC_API_BASE,
        "api_key": ANTHROPIC_API_KEY,
    }
    
    logger.info(f"[LLM] Selected {model} for skills: {skills}")
    return ChatAnthropic(**kwargs)


def with_retry(max_attempts: int = MAX_RETRIES):
    """Decorator for retry logic on async LLM calls."""
    def decorator(func):
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
            retry=retry_if_exception_type((TimeoutError, ConnectionError, Exception)),
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def invoke_with_retry(llm: BaseChatModel, messages: list, config: dict = None, max_retries: int = MAX_RETRIES):
    """Invoke LLM with retry."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return await llm.ainvoke(messages, config=config) if config else await llm.ainvoke(messages)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                import asyncio
                await asyncio.sleep(min(RETRY_WAIT_MAX, RETRY_WAIT_MIN * (2 ** (attempt - 1))))
            else:
                logger.error(f"[LLM] All {max_retries} attempts failed: {e}")
    raise last_error


fast_llm = get_llm("router")
code_llm = get_llm("implement")
router_llm = get_llm("router")
exploration_llm = get_llm("exploration")
analyze_llm = get_llm("analyze")
plan_llm = get_llm("plan")
implement_llm = get_llm("implement")
debug_llm = get_llm("debug")
review_llm = get_llm("review")
