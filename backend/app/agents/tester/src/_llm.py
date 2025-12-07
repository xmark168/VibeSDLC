"""LLM instances for Tester agent.

Provides configured LLM instances for each step:
- plan_llm: For test planning (low temp for consistent plans)
- implement_llm: For test generation (0 temp for deterministic output)
- review_llm: For code review (low temp)
- analyze_llm: For error analysis
"""
import os
import logging
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

# Retry config
MAX_RETRIES = 3

# Default model - can be overridden by TESTER_MODEL env var
DEFAULT_MODEL = os.getenv("TESTER_MODEL", "gpt-4.1")

# LLM configs per step
LLM_CONFIG = {
    "plan": {"model": DEFAULT_MODEL, "temperature": 0.2, "timeout": 60},
    "implement": {"model": DEFAULT_MODEL, "temperature": 0, "timeout": 90},
    "review": {"model": DEFAULT_MODEL, "temperature": 0.1, "timeout": 30},
    "analyze": {"model": DEFAULT_MODEL, "temperature": 0.2, "timeout": 40},
    "default": {"model": DEFAULT_MODEL, "temperature": 0, "timeout": 40},
}


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
        "temperature": config.get("temperature", 0.2),
        "timeout": timeout,
        "max_retries": MAX_RETRIES,
    }
    if openai_base_url:
        kwargs["base_url"] = openai_base_url
    if openai_api_key:
        kwargs["api_key"] = openai_api_key
    
    return ChatOpenAI(**kwargs)


# Pre-instantiated LLMs for each step
plan_llm = get_llm("plan")
implement_llm = get_llm("implement")
review_llm = get_llm("review")
analyze_llm = get_llm("analyze")
default_llm = get_llm("default")
