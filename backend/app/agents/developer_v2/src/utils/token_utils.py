"""Token counting and truncation utilities."""
import logging
from typing import Optional
import tiktoken

logger = logging.getLogger(__name__)
_encoder: Optional[tiktoken.Encoding] = None


def get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.encoding_for_model("gpt-4")
    return _encoder


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(get_encoder().encode(text))


def truncate_to_tokens(text: str, max_tokens: int, keep_end: bool = False) -> str:
    if not text:
        return text
    encoder = get_encoder()
    tokens = encoder.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated = tokens[-max_tokens:] if keep_end else tokens[:max_tokens]
    return encoder.decode(truncated)


def smart_truncate_tokens(text: str, max_tokens: int, head_ratio: float = 0.7) -> tuple[str, bool]:
    """Smart truncate showing head + tail."""
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
    truncated = head + "\n\n/* ... TRUNCATED ... */\n\n" + tail
    return truncated, True
