"""Message compression utilities for LangChain message lists (MetaGPT-style)."""
import logging
from enum import Enum
from typing import List
from langchain_core.messages import BaseMessage, SystemMessage

from .token_utils import count_tokens

logger = logging.getLogger(__name__)


class CompressType(Enum):
    """Message compression strategies. KEEP_RECENT=recent only, KEEP_FIRST_LAST=first+recent."""
    NO_COMPRESS = ""
    KEEP_RECENT = "keep_recent"
    KEEP_FIRST_LAST = "first_last"
    SUMMARIZE = "summarize"


def compress_messages(
    messages: List[BaseMessage],
    max_tokens: int,
    compress_type: CompressType = CompressType.KEEP_RECENT
) -> List[BaseMessage]:
    """Compress messages to fit within token limit.
    
    Args:
        messages: List of messages to compress
        max_tokens: Maximum total tokens allowed
        compress_type: Compression strategy
        
    Returns:
        Compressed list of messages
    """
    if compress_type == CompressType.NO_COMPRESS:
        return messages
    
    if not messages:
        return messages
    
    # Separate system messages (always keep)
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]
    
    # Calculate available tokens for non-system messages
    system_tokens = sum(count_tokens(m.content) for m in system_msgs)
    available = max_tokens - system_tokens
    
    if available <= 0:
        logger.warning("[compress] System messages exceed max_tokens!")
        return system_msgs
    
    # Check if compression needed
    other_tokens = sum(count_tokens(m.content) for m in other_msgs)
    if other_tokens <= available:
        return messages  # No compression needed
    
    logger.info(f"[compress] Compressing {other_tokens} -> {available} tokens ({compress_type.value})")
    
    if compress_type == CompressType.KEEP_RECENT:
        return system_msgs + _keep_recent(other_msgs, available)
    
    elif compress_type == CompressType.KEEP_FIRST_LAST:
        return system_msgs + _keep_first_last(other_msgs, available)
    
    return messages


def _keep_recent(messages: List[BaseMessage], max_tokens: int) -> List[BaseMessage]:
    """Keep most recent messages that fit within token limit."""
    result = []
    total = 0
    
    for msg in reversed(messages):
        msg_tokens = count_tokens(msg.content)
        if total + msg_tokens <= max_tokens:
            result.insert(0, msg)
            total += msg_tokens
        else:
            break
    
    logger.info(f"[compress] KEEP_RECENT: {len(messages)} -> {len(result)} messages")
    return result


def _keep_first_last(messages: List[BaseMessage], max_tokens: int) -> List[BaseMessage]:
    """Keep first message + as many recent messages as fit."""
    if not messages:
        return []
    
    if len(messages) == 1:
        return messages
    
    first = messages[0]
    rest = messages[1:]
    
    first_tokens = count_tokens(first.content)
    if first_tokens >= max_tokens:
        # First message alone exceeds limit
        return [first]
    
    result = [first]
    total = first_tokens
    available = max_tokens - first_tokens
    
    # Add recent messages from end
    for msg in reversed(rest):
        msg_tokens = count_tokens(msg.content)
        if total + msg_tokens <= max_tokens:
            result.append(msg)
            total += msg_tokens
        else:
            break
    
    # Sort to maintain order (first stays first)
    if len(result) > 1:
        result = [result[0]] + sorted(result[1:], key=lambda m: messages.index(m) if m in messages else 999)
    
    logger.info(f"[compress] KEEP_FIRST_LAST: {len(messages)} -> {len(result)} messages")
    return result


def estimate_context_usage(messages: List[BaseMessage], context_limit: int = 128000) -> dict:
    """Estimate context window usage.
    
    Args:
        messages: List of messages
        context_limit: Model's context window (default GPT-4 128k)
        
    Returns:
        dict with usage stats
    """
    total = sum(count_tokens(m.content) for m in messages)
    
    return {
        "total_tokens": total,
        "context_limit": context_limit,
        "usage_percent": round(total / context_limit * 100, 1),
        "remaining": context_limit - total,
        "needs_compression": total > context_limit * 0.9  # Warn at 90%
    }
