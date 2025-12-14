"""
LLM instances for Tester agent.
"""
import asyncio
import logging

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
from app.agents.tester.src.config import RETRY_WAIT_MAX, RETRY_WAIT_MIN

logger = logging.getLogger(__name__)


async def invoke_with_retry(llm, messages: list, config: dict = None, max_retries: int = MAX_RETRIES):
    """Invoke LLM with retry mechanism."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return await llm.ainvoke(messages, config=config) if config else await llm.ainvoke(messages)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait_time = min(RETRY_WAIT_MAX, RETRY_WAIT_MIN * (2 ** (attempt - 1)))
                logger.warning(f"[LLM] Attempt {attempt}/{max_retries} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[LLM] All {max_retries} attempts failed: {e}")
    raise last_error


async def invoke_structured_with_retry(llm, schema, messages: list, config: dict = None, max_retries: int = MAX_RETRIES):
    """Invoke LLM with structured output and retry."""
    structured_llm = llm.with_structured_output(schema)
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            result = await structured_llm.ainvoke(messages, config=config) if config else await structured_llm.ainvoke(messages)
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
                logger.error(f"[LLM] All {max_retries} structured attempts failed: {e}")
    raise last_error


# Pre-created instances
plan_llm = get_llm("plan")
implement_llm = get_llm("implement")
review_llm = get_llm("review")
analyze_llm = get_llm("analyze")
default_llm = get_llm("default")
fast_llm = get_llm("router")
