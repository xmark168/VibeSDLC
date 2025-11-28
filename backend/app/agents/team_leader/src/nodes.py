"""Node functions for Team Leader graph."""

import logging
from uuid import UUID
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.schemas import ExtractedPreferences
from app.agents.team_leader.src.prompts import (
    build_system_prompt, build_user_prompt, parse_llm_decision, get_task_prompts
)
from app.agents.team_leader.tools import get_team_leader_tools

logger = logging.getLogger(__name__)

_fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, timeout=15)
_chat_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, timeout=30)


# Role to WIP column mapping for Lean Kanban
ROLE_TO_WIP_COLUMN = {
    "developer": "InProgress",
    "tester": "Review",
    "business_analyst": None,  # BA has no WIP constraint
}


async def _execute_tool_calls(tool_calls: list, project_id: str) -> list[ToolMessage]:
    """Execute tool calls and return ToolMessages."""
    tools = {t.name: t for t in get_team_leader_tools()}
    results = []
    
    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]
        
        # Inject project_id into tool args
        tool_args["project_id"] = project_id
        
        if tool_name in tools:
            try:
                result = tools[tool_name].invoke(tool_args)
                results.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
                logger.info(f"[tools] {tool_name} executed successfully")
            except Exception as e:
                logger.warning(f"[tools] {tool_name} failed: {e}")
                results.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tc["id"]))
        else:
            results.append(ToolMessage(content=f"Unknown tool: {tool_name}", tool_call_id=tc["id"]))
    
    return results


def _cfg(state: dict, name: str) -> dict:
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}





async def extract_preferences(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    user_message = state.get("user_message", "")
    if len(user_message.strip()) < 10:
        return state
    
    try:
        prompts = get_task_prompts("preference_extraction")
        messages = [
            SystemMessage(content=prompts["system_prompt"]),
            HumanMessage(content=f'Analyze: "{user_message}"')
        ]
        result = await _fast_llm.with_structured_output(ExtractedPreferences).ainvoke(
            messages, config=_cfg(state, "extract_preferences")
        )
        detected = {k: v for k, v in result.model_dump().items() if v is not None and k != "additional"}
        if result.additional:
            detected.update(result.additional)
        if detected and agent:
            for k, v in detected.items():
                await agent.update_preference(k, v)
    except Exception as e:
        logger.warning(f"[extract_preferences] {e}")
    return state


async def router(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Router with tool calling - LLM decides which tools to call for context."""
    try:
        project_id = state.get("project_id", "")
        
        # Build messages
        messages = [
            SystemMessage(content=build_system_prompt(agent)),
            HumanMessage(content=build_user_prompt(
                state["user_message"],
                name=agent.name if agent else "Team Leader",
                conversation_history=state.get("conversation_history", ""),
                user_preferences=state.get("user_preferences", ""),
                board_state="",  # Tools will provide context on-demand
            ))
        ]
        
        # Bind tools to LLM
        tools = get_team_leader_tools()
        llm_with_tools = _fast_llm.bind_tools(tools)
        
        # First LLM call - may request tools
        response = await llm_with_tools.ainvoke(messages, config=_cfg(state, "router"))
        
        # Check if LLM wants to call tools
        if response.tool_calls:
            logger.info(f"[router] Tool calls requested: {[tc['name'] for tc in response.tool_calls]}")
            
            # Execute tools
            tool_results = await _execute_tool_calls(response.tool_calls, project_id)
            
            # Build follow-up messages with tool results
            messages.append(response)  # AIMessage with tool_calls
            messages.extend(tool_results)  # ToolMessages with results
            
            # Second LLM call with tool results
            final_response = await _fast_llm.ainvoke(messages, config=_cfg(state, "router_with_context"))
            decision = parse_llm_decision(final_response.content)
        else:
            # Fast path - no tools needed (greetings, simple responses)
            decision = parse_llm_decision(response.content)
        
        action = decision.get("action")
        
        # For DELEGATE, do final WIP check
        if action == "DELEGATE":
            target_role = decision.get("target_role")
            wip_column = ROLE_TO_WIP_COLUMN.get(target_role)
            
            if wip_column:
                # Quick WIP check from cache
                if agent and hasattr(agent, 'context'):
                    _, _, wip_available = agent.context.get_kanban_context()
                    
                    if wip_available.get(wip_column, 1) <= 0:
                        logger.info(f"[router] WIP blocked: {wip_column} full")
                        return {
                            **state,
                            "action": "RESPOND",
                            "wip_blocked": True,
                            "message": f"Hiện tại {wip_column} đang full. Cần đợi stories hoàn thành trước khi pull work mới.",
                            "reason": f"wip_limit_exceeded_{wip_column}",
                            "confidence": 0.95,
                        }
        
        return {**state, **decision, "confidence": 0.85, "wip_blocked": False}
        
    except Exception as e:
        logger.error(f"[router] {e}", exc_info=True)
        return {**state, "action": "RESPOND", "message": "Xin lỗi, có lỗi xảy ra.", "confidence": 0.0}


async def delegate(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    target_role = state["target_role"]
    if agent:
        from app.agents.core.base_agent import TaskContext
        from app.kafka.event_schemas import AgentTaskType
        
        msg = state.get("message") or f"Chuyển cho @{target_role} nhé!"
        await agent.message_user("response", msg)
        
        task = TaskContext(
            task_id=UUID(state["task_id"]),
            task_type=AgentTaskType.MESSAGE,
            priority="high",
            routing_reason=state.get("reason", "team_leader_routing"),
            user_id=UUID(state["user_id"]) if state.get("user_id") else None,
            project_id=UUID(state["project_id"]),
            content=state["user_message"],
        )
        await agent.delegate_to_role(task=task, target_role=target_role, delegation_message=msg)
    return {**state, "action": "DELEGATE"}


async def respond(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    message = state.get("message", "Mình có thể giúp gì?")
    if agent:
        await agent.message_user("response", message)
    return {**state, "action": "RESPOND"}


async def conversational(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    try:
        system_prompt = build_system_prompt(agent, task_name="conversational")
        if state.get("conversation_history"):
            system_prompt += f"\n\n**Recent:**\n{state['conversation_history']}"
        
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=state["user_message"])]
        response = await _chat_llm.ainvoke(messages, config=_cfg(state, "conversational"))
        
        if agent:
            await agent.message_user("response", response.content)
        return {**state, "message": response.content, "action": "CONVERSATION"}
    except Exception as e:
        logger.error(f"[conversational] {e}")
        msg = "Xin lỗi, có lỗi xảy ra."
        if agent:
            await agent.message_user("response", msg)
        return {**state, "message": msg, "action": "CONVERSATION"}


async def status_check(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Report board status and flow metrics to user using tools."""
    try:
        from app.agents.team_leader.tools import get_board_status, get_flow_metrics, get_active_stories
        
        project_id = state.get("project_id", "")
        
        # Call tools to get fresh data
        board_status = get_board_status.invoke({"project_id": project_id})
        flow_metrics = get_flow_metrics.invoke({"project_id": project_id})
        active_stories = get_active_stories.invoke({"project_id": project_id})
        
        # Combine results
        message = f"{board_status}\n\n{flow_metrics}\n\n{active_stories}"
        
        if agent:
            await agent.message_user("response", message)
        
        return {**state, "message": message, "action": "STATUS_CHECK"}
        
    except Exception as e:
        logger.error(f"[status_check] {e}")
        msg = "Không thể lấy status board. Vui lòng thử lại."
        if agent:
            await agent.message_user("response", msg)
        return {**state, "message": msg, "action": "STATUS_CHECK"}
