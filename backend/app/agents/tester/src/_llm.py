"""LLM instances for Tester agent."""
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

# Default model - can be overridden by TESTER_MODEL env var
DEFAULT_MODEL = os.getenv("TESTER_MODEL", "gpt-4.1")

# Default model configs per step
LLM_CONFIG = {
    # Planning tasks
    "plan": {"model": DEFAULT_MODEL, "temperature": 0.2, "timeout": 60},
    
    # Implementation tasks (code generation)
    "implement": {"model": DEFAULT_MODEL, "temperature": 0, "timeout": 60},
    
    # Review tasks
    "review": {"model": DEFAULT_MODEL, "temperature": 0.1, "timeout": 30},
    
    # Analysis tasks
    "analyze": {"model": DEFAULT_MODEL, "temperature": 0.2, "timeout": 40},
    
    # Summarize tasks
    "summarize": {"model": DEFAULT_MODEL, "temperature": 0.1, "timeout": 30},
    
    # General/default
    "default": {"model": DEFAULT_MODEL, "temperature": 0, "timeout": 40},
}


def get_llm(step: str = "default") -> BaseChatModel:
    """Get LLM for a specific step with timeout. Uses ChatAnthropic for Claude, ChatOpenAI for GPT."""
    config = LLM_CONFIG.get(step, LLM_CONFIG["default"])
    
    # Allow env override: TESTER_MODEL_PLAN=gpt-4o
    env_model = os.getenv(f"TESTER_MODEL_{step.upper()}")
    if env_model:
        config = {**config, "model": env_model}
    
    model = config["model"]
    timeout = config.get("timeout", 40)
    
    # API keys and base URLs
    openai_base_url = os.getenv("TESTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    openai_api_key = os.getenv("TESTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    anthropic_base_url = os.getenv("TESTER_ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_API_BASE")
    anthropic_api_key = os.getenv("TESTER_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or openai_api_key
    
    # Use ChatAnthropic for Claude models
    if "claude" in model.lower():
        kwargs = {
            "model": model,
            "temperature": config.get("temperature", 0.2),
            "max_tokens": 16384,  # Claude requires max_tokens
            "timeout": timeout,
            "max_retries": MAX_RETRIES,
        }
        if anthropic_base_url:
            kwargs["base_url"] = anthropic_base_url
        if anthropic_api_key:
            kwargs["api_key"] = anthropic_api_key
        return ChatAnthropic(**kwargs)
    
    # Use ChatOpenAI for GPT models
    kwargs = {
        "model": model,
        "temperature": config.get("temperature", 0.2),
        "timeout": timeout,
        "max_retries": MAX_RETRIES,
    }
    if openai_base_url:
        kwargs["base_url"] = openai_base_url
    if openai_api_key:
        kwargs["api_key"] = openai_api_key
    return ChatOpenAI(**kwargs)


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
                f"[Tester LLM] Retry {retry_state.attempt_number}/{max_attempts} after error: {retry_state.outcome.exception()}"
            ),
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def invoke_with_retry(llm: BaseChatModel, messages: list, config: dict = None, max_retries: int = MAX_RETRIES):
    """Invoke LLM with retry mechanism."""
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
                logger.warning(f"[Tester LLM] Attempt {attempt}/{max_retries} failed: {e}. Retrying in {wait_time}s...")
                import asyncio
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[Tester LLM] All {max_retries} attempts failed. Last error: {e}")
    
    raise last_error


# Pre-instantiated LLMs for each step
plan_llm = get_llm("plan")
implement_llm = get_llm("implement")
review_llm = get_llm("review")
analyze_llm = get_llm("analyze")
summarize_llm = get_llm("summarize")
default_llm = get_llm("default")
