"""LLM utilities with token tracking.
"""

import logging
from typing import Any, Optional, List
from app.agents.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


async def tracked_ainvoke(
    llm: Any,
    messages: List[Any],
    agent: Optional["BaseAgent"] = None,
    config: Optional[dict] = None,
) -> Any:
    """Invoke LLM and track token usage.
    """
    response = await llm.ainvoke(messages, config=config)
    
    # Extract token usage from response metadata
    tokens = 0
    if hasattr(response, 'response_metadata'):
        metadata = response.response_metadata
        
        # OpenAI format
        if 'token_usage' in metadata:
            usage = metadata['token_usage']
            tokens = usage.get('total_tokens', 0)
        # Anthropic format
        elif 'usage' in metadata:
            usage = metadata['usage']
            tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
    
    # Track on agent if provided
    if agent and tokens > 0:
        agent.track_llm_usage(tokens, 1)
        
    return response


def extract_tokens_from_response(response: Any) -> int:
    """
    Extract token count from LLM response.
    """
    if not hasattr(response, 'response_metadata'):
        return 0
    
    metadata = response.response_metadata
    
    # OpenAI format
    if 'token_usage' in metadata:
        usage = metadata['token_usage']
        return usage.get('total_tokens', 0)
    
    # Anthropic format
    if 'usage' in metadata:
        usage = metadata['usage']
        return usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
    
    return 0
