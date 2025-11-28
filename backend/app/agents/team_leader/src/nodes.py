"""Node functions for Team Leader graph."""

import logging
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.schemas import ExtractedPreferences
from app.agents.team_leader.src.prompts import (
    build_system_prompt,
    build_user_prompt,
    parse_llm_decision,
    get_task_prompts,
)
from app.core.langfuse_client import get_langfuse_handler

logger = logging.getLogger(__name__)


def create_graph_handler(agent) -> dict:
    """Create a shared Langfuse handler for the entire graph execution.
    
    Call this once at graph entry point and pass handler via state.
    
    Returns:
        Handler or None
    """
    handler = get_langfuse_handler()
    if not handler:
        return None
    
    # Set trace-level metadata via the handler
    if agent:
        try:
            # These will be applied to the trace
            handler.user_id = str(agent._current_user_id) if agent._current_user_id else None
            handler.session_id = str(agent.project_id) if agent.project_id else None
            handler.tags = [agent.role_type, "team_leader"]
            handler.metadata = {
                "agent": agent.name,
                "agent_role": agent.role_type,
                "task_id": str(agent._current_task_id) if agent._current_task_id else None,
            }
        except Exception:
            pass  # Some handler versions may not support these
    
    return handler


def _get_llm_config(state: dict, trace_name: str) -> dict:
    """Get LangChain config using shared handler from state.
    
    Args:
        state: Graph state containing 'langfuse_handler'
        trace_name: Name for this specific LLM call (becomes observation name)
    """
    handler = state.get("langfuse_handler")
    if not handler:
        return {}
    
    return {
        "callbacks": [handler],
        "run_name": trace_name,
    }


# =============================================================================
# SHARED LLM CLIENTS (thread-safe, reuse across requests)
# =============================================================================

# Fast model for quick tasks (routing, preference extraction)
FAST_MODEL = "gpt-4o-mini"
# Chat model for conversational responses
CHAT_MODEL = "gpt-4o-mini"

# Pre-initialized LLM clients (avoid re-creating each request)
_fast_llm = ChatOpenAI(
    model=FAST_MODEL,
    temperature=0.1,
    timeout=15,
)

_chat_llm = ChatOpenAI(
    model=CHAT_MODEL,
    temperature=0.7,
    timeout=30,
)


async def extract_preferences(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """
    Node 0: Use LLM to silently extract and save user preferences from message.
    """
    user_message = state.get("user_message", "")
    
    # Skip very short messages (greetings, etc.)
    if len(user_message.strip()) < 10:
        return state
    
    try:
        # Use shared fast LLM with structured output
        structured_llm = _fast_llm.with_structured_output(ExtractedPreferences)
        
        # Get prompts for preference extraction task
        prompts = get_task_prompts("preference_extraction")
        system_prompt = prompts["system_prompt"]
        
        # Build dynamic hints from config (if available)
        additional_hints = prompts.get("additional_hints", [])
        if additional_hints:
            hints_text = "\n".join([
                f"- {h['name']}: {h['description']}"
                for h in additional_hints
            ])
            system_prompt += f"\n\n**Additional preferences to detect:**\n{hints_text}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f'Analyze this message for preferences: "{user_message}"')
        ]
        
        # Get Langfuse config for tracing
        config = _get_llm_config(agent, "preference_extraction") or None
        
        # Invoke LLM with structured output
        result: ExtractedPreferences = await structured_llm.ainvoke(messages, config=config)
        
        # Convert to dict, filter out None values (exclude 'additional' key for now)
        detected = {
            k: v for k, v in result.model_dump().items() 
            if v is not None and k != "additional"
        }
        
        # Merge additional preferences (flatten into detected dict)
        if result.additional:
            detected.update(result.additional)
        
        # Save detected preferences silently
        if detected and agent:
            for key, value in detected.items():
                await agent.update_preference(key, value)
            logger.info(f"[extract_preferences] LLM extracted: {detected}")
        
    except Exception as e:
        # Silent failure - don't block routing
        logger.warning(f"[extract_preferences] LLM error (non-blocking): {e}")
    
    return state  # Pass through unchanged


async def router(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Router node: Intent detection and routing decision.
    
    Decides action: DELEGATE, RESPOND, or CONVERSATION.
    """
    
    logger.info("[router] Analyzing intent for routing")
    
    try:
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
        
        # Get Langfuse config for tracing
        config = _get_llm_config(agent, "routing_decision") or None
        
        # Invoke shared LLM
        response = await _fast_llm.ainvoke(messages, config=config)
        
        decision = parse_llm_decision(response.content)
        
        logger.info(f"[router] Decision: {decision.get('action')}")
        
        return {
            **state,
            **decision,
            "confidence": 0.85,
        }
    
    except Exception as e:
        logger.error(f"[router] Error: {e}", exc_info=True)
        return {
            **state,
            "action": "RESPOND",
            "message": "I encountered an error processing your request. Can you rephrase?",
            "reason": f"router_error: {str(e)}",
            "confidence": 0.0,
        }


async def delegate(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Node 2: Delegate to target agent with Langfuse span tracking."""
    
    target_role = state["target_role"]
    logger.info(f"[delegate] Delegating to {target_role}")
    
    if agent:
        from app.agents.core.base_agent import TaskContext
        from app.kafka.event_schemas import AgentTaskType
        
        # Get LLM-generated delegation message (with @mention and personality)
        # Fallback only if LLM didn't generate message
        delegation_msg = state.get("message")
        if not delegation_msg:
            role_display_names = {
                "business_analyst": "Business Analyst",
                "developer": "Developer", 
                "tester": "Tester",
                "architect": "Architect",
            }
            target_display_name = role_display_names.get(target_role, target_role)
            delegation_msg = f"Để mình chuyển việc này cho @{target_display_name} nhé! 🚀"
        
        # Send delegation message to user
        await agent.message_user("response", delegation_msg)
        
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
            delegation_message=delegation_msg,
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
    """Respond node: Quick responses (greetings, acknowledgments)."""
    
    message = state.get("message", "How can I help you?")
    logger.info(f"[respond] Quick response: {message[:50]}")
    
    if agent:
        await agent.message_user("response", message)
    
    return {**state, "action": "RESPOND"}


async def conversational(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Conversational node: Human-like chat with personality."""
    user_message = state["user_message"]
    logger.info(f"[conversational] Processing: {user_message[:50]}")
    
    try:
        # Build prompt with agent personality
        system_prompt = build_system_prompt(agent, task_name="conversational")
        
        # Include conversation history if available
        conversation_context = state.get("conversation_history", "")
        if conversation_context:
            system_prompt += f"\n\n**Recent conversation:**\n{conversation_context}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        
        # Get Langfuse config for tracing
        config = _get_llm_config(agent, "conversational") or None
        
        # Invoke shared chat LLM
        response = await _chat_llm.ainvoke(messages, config=config)
        final_message = response.content
        
        if agent:
            await agent.message_user("response", final_message)
        
        return {**state, "message": final_message, "action": "CONVERSATION"}
    
    except Exception as e:
        logger.error(f"[conversational] Error: {e}", exc_info=True)
        fallback_message = "Xin lỗi, mình gặp chút trục trặc. Bạn thử hỏi lại được không?"
        if agent:
            await agent.message_user("response", fallback_message)
        return {**state, "message": fallback_message, "action": "CONVERSATION"}
