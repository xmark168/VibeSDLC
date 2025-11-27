"""Node functions for Team Leader graph."""

import logging
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.prompts import (
    build_system_prompt,
    build_user_prompt,
    parse_llm_decision,
)

logger = logging.getLogger(__name__)


async def llm_routing(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Node 1: LLM-based routing for all requests.
    
    Uses BaseAgent's get_langfuse_callback() for LLM tracing.
    """
    
    logger.info("[llm_routing] Using LLM for routing decision")
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        system_prompt = build_system_prompt(agent)
        agent_name = agent.name if agent else "Team Leader"
        user_prompt = build_user_prompt(state["user_message"], name=agent_name)
        
        # Get Langfuse callback from agent (BaseAgent provides this)
        callbacks = []
        if agent:
            callback = agent.get_langfuse_callback(
                trace_name="team_leader_routing_llm",
                tags=["routing", "llm"],
                metadata={
                    "project_id": state.get("project_id"),
                    "task_id": state.get("task_id"),
                }
            )
            if callback:
                callbacks.append(callback)
        
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ],
            config={"callbacks": callbacks} if callbacks else None
        )
        
        decision = parse_llm_decision(response.content)
        
        logger.info(f"[llm_routing] LLM decision: {decision.get('action')}")
        
        return {
            **state,
            **decision,
            "routing_method": "llm",
            "confidence": 0.85,
        }
    
    except Exception as e:
        logger.error(f"[llm_routing] Error: {e}", exc_info=True)
        return {
            **state,
            "action": "RESPOND",
            "routing_method": "llm_error",
            "message": "I encountered an error processing your request. Can you rephrase?",
            "reason": f"llm_error: {str(e)}",
            "confidence": 0.0,
        }


async def delegate(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Node 2: Delegate to target agent."""
    
    target_role = state["target_role"]
    logger.info(f"[delegate] Delegating to {target_role}")
    
    if agent:
        from app.agents.core.base_agent import TaskContext
        from app.kafka.event_schemas import AgentTaskType
        
        task = TaskContext(
            task_id=UUID(state["task_id"]),
            task_type=AgentTaskType.MESSAGE,
            priority="high",
            routing_reason=state.get("reason", "team_leader_routing"),
            user_id=UUID(state["user_id"]) if state.get("user_id") else None,
            project_id=UUID(state["project_id"]),
            content=state["user_message"],
        )
        
        await agent.delegate_to_role(
            task=task,
            target_role=target_role,
            delegation_message=state.get("message", f"Routing to {target_role}"),
        )
    
    return {**state, "action": "DELEGATE"}


async def respond(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Node 3: Respond directly to user."""
    
    message = state.get("message", "How can I help you?")
    logger.info(f"[respond] Responding to user: {message[:50]}")
    
    if agent:
        await agent.message_user("response", message)
    
    return {**state, "action": "RESPOND"}
