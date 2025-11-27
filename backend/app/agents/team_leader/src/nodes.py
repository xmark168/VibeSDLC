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
    
    Uses BaseAgent's track_llm_generation() for Langfuse tracing with token usage.
    """
    
    logger.info("[llm_routing] Using LLM for routing decision")
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        system_prompt = build_system_prompt(agent)
        agent_name = agent.name if agent else "Team Leader"
        conversation_history = state.get("conversation_history", "")
        user_prompt = build_user_prompt(
            state["user_message"], 
            name=agent_name,
            conversation_history=conversation_history
        )
        
        # Build messages for LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # Invoke LLM
        response = await llm.ainvoke(messages)
        
        # Track LLM generation with token usage in Langfuse
        if agent:
            agent.track_llm_generation(
                name="routing_decision",
                model="gpt-4o-mini",
                input_messages=messages,
                response=response,
                model_parameters={"temperature": 0}
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
    """Node 2: Delegate to target agent with Langfuse span tracking."""
    
    target_role = state["target_role"]
    logger.info(f"[delegate] Delegating to {target_role}")
    
    if agent:
        from app.agents.core.base_agent import TaskContext
        from app.kafka.event_schemas import AgentTaskType
        
        # Create span for delegation tracking
        delegation_span = agent.create_span(
            name="delegation",
            input_data={"target_role": target_role, "message": state["user_message"][:200]}
        )
        
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
        
        # End delegation span
        if delegation_span:
            try:
                delegation_span.end(output={"delegated_to": target_role, "success": True})
            except Exception:
                pass
        
        # Track delegation event
        agent.track_event("delegation_completed", {
            "target_role": target_role,
            "task_id": state.get("task_id"),
            "routing_reason": state.get("reason")
        })
    
    return {**state, "action": "DELEGATE"}


async def respond(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Node 3: Respond directly to user."""
    
    message = state.get("message", "How can I help you?")
    logger.info(f"[respond] Responding to user: {message[:50]}")
    
    if agent:
        await agent.message_user("response", message)
    
    return {**state, "action": "RESPOND"}
