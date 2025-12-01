"""LLM instances for Developer V2 nodes."""
import os
from langchain_openai import ChatOpenAI

# Default model configs per step
LLM_CONFIG = {
    # Fast tasks (simple routing/response)
    "router": {"model": "gpt-4o-mini", "temperature": 0.1, "timeout": 20},
    "clarify": {"model": "gpt-4o-mini", "temperature": 0.1, "timeout": 20},
    "respond": {"model": "gpt-4o-mini", "temperature": 0.1, "timeout": 20},
    
    # Complex tasks (code generation)
    "analyze": {"model": "gpt-4.1", "temperature": 0.2, "timeout": 120},
    "plan": {"model": "gpt-4.1", "temperature": 0.2, "timeout": 120},
    "implement": {"model": "gpt-4.1", "temperature": 0.2, "timeout": 120},
    "debug": {"model": "gpt-4.1", "temperature": 0.2, "timeout": 120},
}


def get_llm(step: str) -> ChatOpenAI:
    """Get LLM for a specific step. Supports env override."""
    config = LLM_CONFIG.get(step, LLM_CONFIG["implement"])
    
    # Allow env override: DEVV2_MODEL_PLAN=gpt-4o
    env_model = os.getenv(f"DEVV2_MODEL_{step.upper()}")
    if env_model:
        config = {**config, "model": env_model}
    
    return ChatOpenAI(**config)


# Pre-instantiated for backward compatibility
fast_llm = get_llm("router")
code_llm = get_llm("implement")

# Step-specific LLMs (optional, for fine-tuning)
router_llm = get_llm("router")
analyze_llm = get_llm("analyze")
plan_llm = get_llm("plan")
implement_llm = get_llm("implement")
debug_llm = get_llm("debug")
