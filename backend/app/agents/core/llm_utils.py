"""LLM utilities with token tracking.

Provides wrapper functions to track token usage from LLM calls.
"""

import logging
from typing import Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)


async def tracked_ainvoke(
    llm: Any,
    messages: List[Any],
    agent: Optional["BaseAgent"] = None,
    config: Optional[dict] = None,
) -> Any:
    """Invoke LLM and track token usage.
    
    Wrapper around llm.ainvoke() that extracts and tracks token usage.
    
    Args:
        llm: LangChain LLM instance (ChatOpenAI, etc.)
        messages: List of messages to send
        agent: Optional BaseAgent instance to track tokens on
        config: Optional config dict for the LLM call
        
    Returns:
        LLM response
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
    """Extract token count from LLM response.
    
    Supports multiple LLM providers (OpenAI, Anthropic, etc.)
    
    Args:
        response: LLM response object
        
    Returns:
        Total tokens used, or 0 if not available
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
