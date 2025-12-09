"""LLM execution utilities for Developer V2."""

import logging
import time
from typing import Dict, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)


class FileCache:
    """Simple in-memory file cache."""
    _cache: Dict[str, Tuple[str, float]] = {}
    TTL = 120
    
    @classmethod
    def get(cls, file_path: str) -> Optional[str]:
        if file_path in cls._cache:
            content, timestamp = cls._cache[file_path]
            if time.time() - timestamp < cls.TTL:
                return content
            del cls._cache[file_path]
        return None
    
    @classmethod
    def set(cls, file_path: str, content: str) -> None:
        cls._cache[file_path] = (content, time.time())
    
    @classmethod
    def invalidate(cls, file_path: str) -> None:
        if file_path in cls._cache:
            del cls._cache[file_path]
    
    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()


file_cache = FileCache()


def get_langfuse_config(state: dict, run_name: str) -> dict:
    handler = state.get("langfuse_handler")
    if handler:
        return {"callbacks": [handler], "run_name": run_name}
    return {"run_name": run_name}


def flush_langfuse(state: dict) -> None:
    langfuse_client = state.get("langfuse_client")
    if langfuse_client:
        try:
            langfuse_client.flush()
        except Exception:
            pass


def get_langfuse_span(state: dict, name: str, input_data: dict = None):
    """Get Langfuse span if handler available."""
    if not state.get("langfuse_handler"):
        return None
    try:
        from langfuse import get_client
        return get_client().span(name=name, input=input_data or {})
    except Exception:
        return None


async def execute_llm_with_tools(
    llm: ChatOpenAI,
    tools: list,
    messages: list,
    state: dict,
    name: str,
    max_iterations: int = 5
) -> str:
    """Execute LLM with ReAct tool calling pattern."""
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
        flush_langfuse(state)
        
        if not response.tool_calls:
            logger.info(f"[{name}] Completed at iteration {i+1}")
            return response.content or ""
        
        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info(f"[{name}] Tools called: {tool_names}")
        
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
                    
                    result_str = str(result)
                    content = result_str if "[SKILL:" in result_str else result_str[:4000]
                    
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
    
    logger.warning(f"[{name}] Max iterations reached")
    return conversation[-1].content if hasattr(conversation[-1], 'content') else ""
