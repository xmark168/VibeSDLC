"""LLM instances for Developer V2 nodes."""
import os
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

# Default model configs per step
LLM_CONFIG = {
    # Fast tasks (simple routing/response)
    "router": {"model": "gpt-4o-mini", "temperature": 0.1, "timeout": 20},
    "clarify": {"model": "gpt-4o-mini", "temperature": 0.1, "timeout": 20},
    "respond": {"model": "gpt-4o-mini", "temperature": 0.1, "timeout": 20},
    
    # Complex tasks (code generation)
    "analyze": {"model": "gpt-4.1", "temperature": 0.2, "timeout": 120},
    "plan": {"model": "gpt-4.1", "temperature": 0.2, "timeout": 120},
    "implement": {"model": "claude-sonnet-4-5-20250929", "temperature": 0.2, "timeout": 120},
    "debug": {"model": "gpt-4.1", "temperature": 0.2, "timeout": 120},
}


def get_llm(step: str) -> BaseChatModel:
    """Get LLM for a specific step. Uses ChatAnthropic for Claude, ChatOpenAI for GPT."""
    config = LLM_CONFIG.get(step, LLM_CONFIG["implement"])
    
    # Allow env override: DEVV2_MODEL_PLAN=gpt-4o
    env_model = os.getenv(f"DEVV2_MODEL_{step.upper()}")
    if env_model:
        config = {**config, "model": env_model}
    
    model = config["model"]
    
    # Use OPENAI_API_BASE and OPENAI_API_KEY for all models (proxy)
    base_url = os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Use ChatAnthropic for Claude models
    if "claude" in model.lower():
        kwargs = {
            "model": model,
            "temperature": config.get("temperature", 0.2),
            "max_tokens": 8192,
        }
        if base_url:
            kwargs["base_url"] = base_url
        if api_key:
            kwargs["api_key"] = api_key
        return ChatAnthropic(**kwargs)
    
    # Use ChatOpenAI for GPT models
    kwargs = {**config}
    if base_url:
        kwargs["base_url"] = base_url
    if api_key:
        kwargs["api_key"] = api_key
    return ChatOpenAI(**kwargs)


# Pre-instantiated for backward compatibility
fast_llm = get_llm("router")
code_llm = get_llm("implement")

# Step-specific LLMs (optional, for fine-tuning)
router_llm = get_llm("router")
analyze_llm = get_llm("analyze")
plan_llm = get_llm("plan")
implement_llm = get_llm("implement")
debug_llm = get_llm("debug")
