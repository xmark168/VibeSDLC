"""LLM execution utilities for Developer V2."""

import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage


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


async def execute_llm_with_tools(
    llm: ChatOpenAI,
    tools: list,
    messages: list,
    state: dict,
    run_name: str,
    max_iterations: int = 5
) -> str:
    """Execute LLM with ReAct tool calling pattern.
    
    Pattern: LLM.bind_tools() -> tool_calls -> execute -> loop until done
    
    Args:
        llm: LLM instance to use
        tools: List of LangChain tools to bind
        messages: Initial conversation messages
        state: State dict (for Langfuse config)
        run_name: Run name for tracing
        max_iterations: Max tool calling loops
        
    Returns:
        Final LLM response content
    """
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}
    conversation = list(messages)
    
    for _ in range(max_iterations):
        response = await llm_with_tools.ainvoke(
            conversation, 
            config=get_langfuse_config(state, run_name)
        )
        conversation.append(response)
        
        if not response.tool_calls:
            return response.content or ""
        
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
                    
                    conversation.append(ToolMessage(
                        content=str(result)[:2000],
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
