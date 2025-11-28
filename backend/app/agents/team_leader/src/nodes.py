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

logger = logging.getLogger(__name__)


async def extract_preferences(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Node 0: Use LLM to silently extract and save user preferences from message.
    
    Runs BEFORE routing. Does not change main flow.
    Uses structured output with hybrid schema (core typed + dynamic additional).
    """
    user_message = state.get("user_message", "")
    
    # Skip very short messages (greetings, etc.)
    if len(user_message.strip()) < 10:
        return state
    
    try:
        # Use fast model with structured output
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        structured_llm = llm.with_structured_output(ExtractedPreferences)
        
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
        
        # Invoke LLM with structured output - returns ExtractedPreferences directly
        result: ExtractedPreferences = await structured_llm.ainvoke(messages)
        
        # Track LLM generation in Langfuse (if agent available)
        if agent:
            agent.track_llm_generation(
                name="preference_extraction",
                model="gpt-4o-mini",
                input_messages=messages,
                response=result.model_dump(),
                model_parameters={"temperature": 0}
            )
        
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
    """Respond node: Quick responses (greetings, acknowledgments)."""
    
    message = state.get("message", "How can I help you?")
    logger.info(f"[respond] Quick response: {message[:50]}")
    
    if agent:
        await agent.message_user("response", message)
    
    return {**state, "action": "RESPOND"}


async def conversational(state: TeamLeaderState, agent=None) -> TeamLeaderState:
    """Conversational node: Human-like chat with personality + Tavily web search.
    
    - Answers general knowledge, life questions
    - Uses Tavily tool for current information (weather, news, facts)
    - Responds with agent's personality
    """
    from langchain_core.messages import ToolMessage
    from langchain_community.tools.tavily_search import TavilySearchResults
    
    user_message = state["user_message"]
    logger.info(f"[conversational] Processing: {user_message[:50]}")
    
    try:
        # LLM with Tavily tool binding
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        tavily_tool = TavilySearchResults(max_results=3)
        llm_with_tools = llm.bind_tools([tavily_tool])
        
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
        
        # First LLM call - may decide to use Tavily tool
        response = await llm_with_tools.ainvoke(messages)
        
        # Handle tool calls if LLM decided to search
        if response.tool_calls:
            logger.info(f"[conversational] Tavily search triggered")
            
            for tool_call in response.tool_calls:
                try:
                    # Execute Tavily search
                    search_result = await tavily_tool.ainvoke(tool_call["args"])
                    
                    # Add tool response to messages
                    messages.append(response)
                    messages.append(ToolMessage(
                        content=str(search_result),
                        tool_call_id=tool_call["id"]
                    ))
                except Exception as e:
                    logger.warning(f"[conversational] Tavily error: {e}")
                    messages.append(response)
                    messages.append(ToolMessage(
                        content="Search unavailable, please respond based on your knowledge.",
                        tool_call_id=tool_call["id"]
                    ))
            
            # Second LLM call with search results
            response = await llm_with_tools.ainvoke(messages)
        
        final_message = response.content
        
        # Track LLM generation
        if agent:
            agent.track_llm_generation(
                name="conversational",
                model="gpt-4o-mini",
                input_messages=messages,
                response=response,
                model_parameters={"temperature": 0.7}
            )
        
        # Send response to user
        if agent:
            await agent.message_user("response", final_message)
        
        logger.info(f"[conversational] Response sent: {final_message[:50]}")
        
        return {**state, "message": final_message, "action": "CONVERSATION"}
    
    except Exception as e:
        logger.error(f"[conversational] Error: {e}", exc_info=True)
        
        fallback_message = "Xin lỗi, mình gặp chút trục trặc. Bạn thử hỏi lại được không?"
        if agent:
            await agent.message_user("response", fallback_message)
        
        return {**state, "message": fallback_message, "action": "CONVERSATION"}
