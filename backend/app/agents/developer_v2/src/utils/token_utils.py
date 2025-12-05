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
    """Count tokens in text.
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Number of tokens
    """
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
    
    logger.info(f"[token_utils] Truncated: {len(tokens)} -> {max_tokens} tokens")
    return truncated, True


async def summarize_if_large(
    content: str,
    file_path: str,
    max_tokens: int = 2000,
    llm = None
) -> str:
    """Summarize file if too large, otherwise return as-is.
    
    Args:
        content: File content
        file_path: Path for context
        max_tokens: Max tokens before summarizing
        llm: LLM instance for summarization (optional)
        
    Returns:
        Original content or summarized version
    """
    from langchain_core.messages import HumanMessage
    
    tokens = count_tokens(content)
    
    if tokens <= max_tokens:
        return content
    
    if llm is None:
        # Fallback to smart truncate
        truncated, _ = smart_truncate_tokens(content, max_tokens)
        return truncated
    
    # Use LLM to summarize - preserve structure
    summary_prompt = f"""Summarize this code file concisely, preserving:
- All imports (exact)
- All type definitions/interfaces (exact)
- Function/class signatures with params (not implementations)
- Export statements (exact)

File: {file_path}
```
{truncate_to_tokens(content, 8000)}
```

Output a condensed version that captures the structure. Keep actual code for imports/exports."""

    try:
        response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
        summary = response.content if hasattr(response, 'content') else str(response)
        logger.info(f"[token_utils] Summarized {file_path}: {tokens} -> ~{count_tokens(summary)} tokens")
        return f"/* SUMMARIZED: {file_path} ({tokens} tokens -> condensed) */\n{summary}"
    except Exception as e:
        logger.warning(f"[token_utils] Summarize failed, using truncate: {e}")
        truncated, _ = smart_truncate_tokens(content, max_tokens)
        return truncated
