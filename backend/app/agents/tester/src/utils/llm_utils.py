"""LLM utilities for Tester Agent."""

import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def get_langfuse_config(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    handler = state.get("langfuse_handler")
    return {"callbacks": [handler], "run_name": name} if handler else {"run_name": name}


async def execute_llm_with_tools(
    llm: ChatOpenAI,
    tools: list,
    messages: list,
    state: dict,
    name: str,
    max_iterations: int = 10,
) -> str:
    """Execute LLM with ReAct tool calling pattern.
    
    Args:
        llm: ChatOpenAI instance
        tools: List of LangChain tools
        messages: Initial messages
        state: State dict (for langfuse handler)
        name: Run name for tracing
        max_iterations: Max tool call iterations
        
    Returns:
        Final response content
    """
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}
    conversation = list(messages)
    config = get_langfuse_config(state, name)
    
    # Track exploration tool calls to prevent infinite loops
    explore_tools = {"list_directory", "glob_files", "grep_files"}
    explore_count = 0
    max_explore = 4
    
    for i in range(max_iterations):
        response = await llm_with_tools.ainvoke(conversation, config=config)
        conversation.append(response)
        
        if not response.tool_calls:
            logger.info(f"[execute_llm_with_tools] Completed after {i+1} iterations")
            return response.content or ""
        
        # Execute tool calls
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            # Count exploration tools
            if tool_name in explore_tools:
                explore_count += 1
                if explore_count > max_explore:
                    logger.warning(f"[execute_llm_with_tools] Too many explore calls ({explore_count})")
                    conversation.append(ToolMessage(
                        content="STOP EXPLORING. You have searched enough. Now proceed with the task.",
                        tool_call_id=tool_call["id"]
                    ))
                    continue
            
            if tool_name in tool_map:
                try:
                    tool = tool_map[tool_name]
                    if hasattr(tool, 'invoke'):
                        result = tool.invoke(tool_args)
                    elif hasattr(tool, 'func'):
                        result = tool.func(**tool_args)
                    else:
                        result = tool(**tool_args)
                    
                    conversation.append(ToolMessage(
                        content=str(result)[:4000],
                        tool_call_id=tool_call["id"]
                    ))
                    logger.info(f"[tool] {tool_name} -> OK")
                except Exception as e:
                    conversation.append(ToolMessage(
                        content=f"Error: {str(e)}",
                        tool_call_id=tool_call["id"]
                    ))
                    logger.warning(f"[tool] {tool_name} -> Error: {e}")
            else:
                conversation.append(ToolMessage(
                    content=f"Unknown tool: {tool_name}",
                    tool_call_id=tool_call["id"]
                ))
    
    logger.warning(f"[execute_llm_with_tools] Max iterations ({max_iterations}) reached")
    return conversation[-1].content if hasattr(conversation[-1], 'content') else ""
