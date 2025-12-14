"""LLM instances for developer_v2 agent.

Re-exports from centralized llm_factory.
Token tracking is automatic via LangChain callback in factory.
"""
from app.core.agent.llm_factory import (
    MODELS,
    STEP_CONFIG,
    MAX_RETRIES,
    get_llm,
    get_raw_llm,
    create_llm,
    create_fast_llm,
    create_medium_llm,
    create_complex_llm,
)

# Pre-created instances
fast_llm = get_llm("router")
router_llm = get_llm("router")
analyze_llm = get_llm("analyze")
plan_llm = get_llm("plan")
implement_llm = get_llm("implement")
code_llm = get_llm("implement")
debug_llm = get_llm("debug")
review_llm = get_llm("review")
