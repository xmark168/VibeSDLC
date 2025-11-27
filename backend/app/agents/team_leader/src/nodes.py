"""Node functions for Team Leader graph."""

import logging
import re
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

# Preference detection patterns (case-insensitive)
PREFERENCE_PATTERNS = {
    "preferred_language": [
        (r"\b(tiếng việt|vietnamese)\b", "vi"),
        (r"\b(tiếng anh|english)\b", "en"),
    ],
    "emoji_usage": [
        (r"\b(đừng|không|no|don'?t)\s*(dùng|sử dụng|use)?\s*emoji\b", False),
    ],
    "expertise_level": [
        (r"\b(senior|expert|chuyên gia)\b", "expert"),
        (r"\b(junior|beginner|mới học|newbie)\b", "beginner"),
        (r"\b(mid|intermediate|trung bình)\b", "intermediate"),
    ],
    "response_length": [
        (r"\b(ngắn gọn|concise|brief|short)\b", "concise"),
        (r"\b(chi tiết|detailed|verbose|dài)\b", "detailed"),
    ],
}


async def extract_preferences(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Node 0: Silently extract and save user preferences from message.
    
    Runs BEFORE routing. Does not change main flow.
    """
    user_message = state.get("user_message", "").lower()
    detected = {}
    
    for pref_key, patterns in PREFERENCE_PATTERNS.items():
        for pattern, value in patterns:
            if re.search(pattern, user_message, re.IGNORECASE):
                detected[pref_key] = value
                break
    
    # Extract tech stack (special handling for multiple values)
    tech_patterns = [
        r"\b(react|vue|angular|nextjs|nuxt)\b",
        r"\b(fastapi|django|flask|express|nestjs)\b",
        r"\b(python|javascript|typescript|java|go|rust)\b",
        r"\b(postgresql|mysql|mongodb|redis)\b",
    ]
    tech_stack = []
    for pattern in tech_patterns:
        matches = re.findall(pattern, user_message, re.IGNORECASE)
        tech_stack.extend([m.capitalize() for m in matches])
    
    if tech_stack:
        detected["tech_stack"] = list(set(tech_stack))
    
    # Save detected preferences silently
    if detected and agent:
        for key, value in detected.items():
            await agent.update_preference(key, value)
        logger.info(f"[extract_preferences] Silently saved: {detected}")
    
    return state  # Pass through unchanged


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
        user_preferences = state.get("user_preferences", "")
        user_prompt = build_user_prompt(
            state["user_message"], 
            name=agent_name,
            conversation_history=conversation_history,
            user_preferences=user_preferences
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



