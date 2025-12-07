"""LLM execution utilities for Developer V2."""

import logging
import re
import time
from typing import Dict, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)


# ============================================================================
# FILE CACHE - Avoid redundant file reads within session
# ============================================================================
class FileCache:
    """Simple in-memory file cache to reduce redundant reads.
    
    Cache invalidated after TTL or when file is written.
    """
    _cache: Dict[str, Tuple[str, float]] = {}
    TTL = 120  # seconds - cache valid for 2 minutes
    
    @classmethod
    def get(cls, file_path: str) -> Optional[str]:
        """Get cached file content if still valid."""
        if file_path in cls._cache:
            content, timestamp = cls._cache[file_path]
            if time.time() - timestamp < cls.TTL:
                return content
            # Expired, remove from cache
            del cls._cache[file_path]
        return None
    
    @classmethod
    def set(cls, file_path: str, content: str) -> None:
        """Cache file content."""
        cls._cache[file_path] = (content, time.time())
    
    @classmethod
    def invalidate(cls, file_path: str) -> None:
        """Invalidate cache for a file (call after write)."""
        if file_path in cls._cache:
            del cls._cache[file_path]
    
    @classmethod
    def clear(cls) -> None:
        """Clear entire cache."""
        cls._cache.clear()


# Global instance
file_cache = FileCache()


def get_langfuse_config(state: dict, run_name: str) -> dict:
    """Get LangChain config with optional Langfuse callback.
    
    Args:
        state: State dict containing langfuse_handler
        run_name: Name for this LLM run (for tracing)
        
    Returns:
        Config dict with callbacks if handler exists
    """
    handler = state.get("langfuse_handler")
    if handler:
        return {"callbacks": [handler], "run_name": run_name}
    return {"run_name": run_name}


def flush_langfuse(state: dict) -> None:
    """No-op: Langfuse batching handles flush automatically.
    
    With flush_at=10 and flush_interval=10, Langfuse batches events
    and flushes automatically. Manual flush only at end of story.
    """
    pass  # Batching handles this - no manual flush needed


async def execute_llm_with_tools(
    llm: ChatOpenAI,
    tools: list,
    messages: list,
    state: dict,
    name: str,
    max_iterations: int = 5
) -> str:
    """Execute LLM with ReAct tool calling pattern.
    
    Pattern: LLM.bind_tools() -> tool_calls -> execute -> loop until done
    
    Args:
        llm: LLM instance to use
        tools: List of LangChain tools to bind
        messages: Initial conversation messages
        state: State dict (for Langfuse config)
        name: Run name for Langfuse tracing
        max_iterations: Max tool calling loops
        
    Returns:
        Final LLM response content
    """
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}
    conversation = list(messages)
    
    for i in range(max_iterations):
        logger.info(f"[{name}] Iteration {i+1}/{max_iterations}")
        
        response = await llm_with_tools.ainvoke(
            conversation, 
            config=get_langfuse_config(state, name)
        )
        conversation.append(response)
        
        # Flush Langfuse for real-time updates
        flush_langfuse(state)
        
        if not response.tool_calls:
            logger.info(f"[{name}] Completed at iteration {i+1}")
            return response.content or ""
        
        # Log tool calls
        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info(f"[{name}] Tools called: {tool_names}")
        
        # Execute tool calls
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            if tool_name in tool_map:
                try:
                    tool = tool_map[tool_name]
                    if hasattr(tool, 'invoke'):
                        result = tool.invoke(tool_args)
                    elif hasattr(tool, 'func'):
                        result = tool.func(**tool_args)
                    else:
                        result = tool(**tool_args)
                    
                    # Smart truncate - skills need full content
                    result_str = str(result)
                    if "[SKILL:" in result_str or "[ACTIVATED" in result_str:
                        content = result_str  # Full skill content
                    else:
                        content = result_str[:4000]  # Other tools can truncate
                    
                    conversation.append(ToolMessage(
                        content=content,
                        tool_call_id=tool_call["id"]
                    ))
                except Exception as e:
                    conversation.append(ToolMessage(
                        content=f"Error: {str(e)}",
                        tool_call_id=tool_call["id"]
                    ))
            else:
                conversation.append(ToolMessage(
                    content=f"Unknown tool: {tool_name}",
                    tool_call_id=tool_call["id"]
                ))
    
    logger.warning(f"[{name}] Max iterations ({max_iterations}) reached without completion")
    return conversation[-1].content if hasattr(conversation[-1], 'content') else ""


def clean_json_response(text: str) -> str:
    """Strip markdown code blocks from LLM JSON response.
    
    Handles both ```json and ``` code blocks.
    
    Args:
        text: Raw LLM response that may contain markdown
        
    Returns:
        Cleaned JSON string
    """
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    return match.group(1).strip() if match else text.strip()


def extract_json_from_messages(result: dict) -> dict:
    """Extract JSON from agent's final AI message.
    
    Searches messages in reverse order for valid JSON content.
    
    Args:
        result: Dict with 'messages' key containing conversation
        
    Returns:
        Parsed JSON dict, or empty dict if not found
    """
    import json
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, 'content') and msg.content:
            try:
                return json.loads(clean_json_response(msg.content))
            except:
                continue
    return {}
