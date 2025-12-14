"""Token counting and truncation utilities using tiktoken."""
import logging
from typing import Optional
import tiktoken

logger = logging.getLogger(__name__)

# Cache encoder for performance
_encoder: Optional[tiktoken.Encoding] = None


def get_encoder() -> tiktoken.Encoding:
    """Get cached tiktoken encoder for GPT-4."""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.encoding_for_model("gpt-4")
    return _encoder


def count_tokens(text: str) -> int:
    """Count tokens in text."""
    if not text:
        return 0
    return len(get_encoder().encode(text))


def truncate_to_tokens(text: str, max_tokens: int, keep_end: bool = False) -> str:
    """Truncate text to max tokens.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum number of tokens
        keep_end: If True, keep end of text instead of beginning
        
    Returns:
        Truncated text
    """
    if not text:
        return text
        
    encoder = get_encoder()
    tokens = encoder.encode(text)
    
    if len(tokens) <= max_tokens:
        return text
    
    if keep_end:
        truncated = tokens[-max_tokens:]
    else:
        truncated = tokens[:max_tokens]
    
    return encoder.decode(truncated)


def smart_truncate_tokens(
    text: str, 
    max_tokens: int, 
    head_ratio: float = 0.7
) -> tuple[str, bool]:
    """Smart truncate showing head + tail by tokens.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum number of tokens
        head_ratio: Ratio of tokens to keep from head (default 70%)
        
    Returns:
        tuple: (truncated_text, was_truncated)
    """
    if not text:
        return text, False
        
    encoder = get_encoder()
    tokens = encoder.encode(text)
    
    if len(tokens) <= max_tokens:
        return text, False
    
    head_tokens = int(max_tokens * head_ratio)
    tail_tokens = max_tokens - head_tokens
    
    head = encoder.decode(tokens[:head_tokens])
    tail = encoder.decode(tokens[-tail_tokens:])
    
    truncated = head + "\n\n/* ... TRUNCATED (showing head + tail) ... */\n\n" + tail
    
    logger.debug(f"[token_utils] Truncated: {len(tokens)} -> {max_tokens} tokens")
    return truncated, True


def truncate_error_logs(logs: str, max_tokens: int = 3000) -> str:
    """Truncate error logs intelligently - keep most relevant parts.
    
    For test errors, keep:
    - Error messages and stack traces (end of logs)
    - FAIL/Error summary lines
    """
    if not logs:
        return logs
    
    tokens = count_tokens(logs)
    if tokens <= max_tokens:
        return logs
    
    # For error logs, keep more from end (where errors usually are)
    truncated, _ = smart_truncate_tokens(logs, max_tokens, head_ratio=0.3)
    return truncated
