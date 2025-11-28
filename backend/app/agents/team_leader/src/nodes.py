"""Node functions for Team Leader graph."""

import logging
from uuid import UUID
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.schemas import ExtractedPreferences
from app.agents.team_leader.src.prompts import (
    build_system_prompt, build_user_prompt, parse_llm_decision, get_task_prompts
)

logger = logging.getLogger(__name__)

_fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, timeout=15)
_chat_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, timeout=30)


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
    try:
        messages = [
            SystemMessage(content=build_system_prompt(agent)),
            HumanMessage(content=build_user_prompt(
                state["user_message"],
                name=agent.name if agent else "Team Leader",
                conversation_history=state.get("conversation_history", ""),
                user_preferences=state.get("user_preferences", "")
            ))
        ]
        response = await _fast_llm.ainvoke(messages, config=_cfg(state, "router"))
        decision = parse_llm_decision(response.content)
        return {**state, **decision, "confidence": 0.85}
    except Exception as e:
        logger.error(f"[router] {e}")
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
