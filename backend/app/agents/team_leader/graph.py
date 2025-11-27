"""Team Leader LangGraph implementation (simplified)."""

import json
import logging
import re
from typing import Literal
from uuid import UUID

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.team_leader.state import TeamLeaderState

logger = logging.getLogger(__name__)


class TeamLeaderGraph:
    """LangGraph-based Team Leader routing graph."""
    
    def __init__(self, agent=None):
        """Initialize graph with reference to agent.
        
        Args:
            agent: TeamLeader agent instance (for delegation/messaging)
        """
        self.agent = agent
        
        graph = StateGraph(TeamLeaderState)
        
        graph.add_node("llm_routing", self.llm_routing)
        graph.add_node("delegate", self.delegate)
        graph.add_node("respond", self.respond)
        
        graph.set_entry_point("llm_routing")
        
        graph.add_conditional_edges(
            "llm_routing",
            self.route_after_llm,
            {
                "delegate": "delegate",
                "respond": "respond"
            }
        )
        
        graph.add_edge("delegate", END)
        graph.add_edge("respond", END)
        
        self.graph = graph.compile()
        
        logger.info("[TeamLeaderGraph] LLM-only routing graph compiled")
    
    async def llm_routing(self, state: TeamLeaderState) -> TeamLeaderState:
        """Node 1: LLM-based routing for all requests."""
        
        logger.info("[llm_routing] Using LLM for routing decision")
        
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            
            system_prompt = self._build_system_prompt(state)
            user_prompt = self._build_user_prompt(state)
            
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            decision = self._parse_llm_decision(response.content)
            
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
    
    async def delegate(self, state: TeamLeaderState) -> TeamLeaderState:
        """Node 2: Delegate to target agent."""
        
        target_role = state["target_role"]
        logger.info(f"[delegate] Delegating to {target_role}")
        
        if self.agent:
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
            
            await self.agent.delegate_to_role(
                task=task,
                target_role=target_role,
                delegation_message=state.get("message", f"Routing to {target_role}"),
            )
        
        return {**state, "action": "DELEGATE"}
    
    async def respond(self, state: TeamLeaderState) -> TeamLeaderState:
        """Node 3: Respond directly to user."""
        
        message = state.get("message", "How can I help you?")
        logger.info(f"[respond] Responding to user: {message[:50]}")
        
        if self.agent:
            await self.agent.message_user("response", message)
        
        return {**state, "action": "RESPOND"}
    
    def route_after_llm(self, state: TeamLeaderState) -> Literal["delegate", "respond"]:
        """Conditional edge: Route after LLM decision."""
        
        if state.get("action") == "DELEGATE":
            return "delegate"
        else:
            return "respond"
    
    def _build_system_prompt(self, state: TeamLeaderState) -> str:
        """Build system prompt with clear routing logic."""
        
        return """You are a Team Leader routing user requests to specialist agents.

**Available agents:**
- business_analyst: 
  * NEW feature requests (build X, create Y, make Z)
  * Requirements gathering and analysis
  * PRD/spec creation, user stories
  * Planning phase work
  
- developer: 
  * IMPLEMENT existing stories/tasks (when requirements are clear)
  * Code changes, bug fixes
  * Technical implementation
  
- tester: 
  * Test plan creation
  * QA, testing, validation

**Routing Logic:**
→ NEW feature/idea → business_analyst (analyze requirements first)
→ IMPLEMENT task → developer (requirements already exist)
→ TEST work → tester"""
    
    def _build_user_prompt(self, state: TeamLeaderState) -> str:
        """Build user prompt for LLM with examples."""
        
        return f'''User message: "{state['user_message']}"

Analyze and decide routing.

Respond with JSON:
{{
    "action": "DELEGATE" or "RESPOND",
    "target_role": "business_analyst" | "developer" | "tester" (if DELEGATE),
    "message": "Brief message to user",
    "reason": "Internal routing reason"
}}

**Examples:**
✅ "tạo website bán hàng" → business_analyst (new feature)
✅ "build mobile app" → business_analyst (new project)
✅ "implement story #123" → developer (clear task)
✅ "sửa bug login" → developer (bug fix)
✅ "test feature payment" → tester (testing)
✅ "chào bạn" → RESPOND (conversational)

**Guidelines:**
- NEW features/ideas → business_analyst (requirements analysis needed)
- IMPLEMENT tasks → developer (requirements already clear)
- TEST/QA work → tester
- Unclear/conversational → RESPOND'''
    
    def _parse_llm_decision(self, response: str) -> dict:
        """Parse LLM JSON response."""
        
        try:
            # Try to extract JSON
            json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group(0))
                
                # Validate required fields
                if "action" in decision and "message" in decision:
                    return decision
            
            # Fallback parsing
            if "DELEGATE" in response.upper():
                return {
                    "action": "DELEGATE",
                    "target_role": self._extract_role(response),
                    "message": "Processing your request",
                    "reason": "llm_delegate"
                }
            else:
                return {
                    "action": "RESPOND",
                    "message": response[:200],
                    "reason": "llm_respond"
                }
        
        except Exception as e:
            logger.warning(f"[_parse_llm_decision] Parse error: {e}")
            return {
                "action": "RESPOND",
                "message": "I need more information. Can you clarify your request?",
                "reason": "parse_error"
            }
    
    def _extract_role(self, response: str) -> str:
        """Extract role from LLM response."""
        
        response_lower = response.lower()
        
        if "business_analyst" in response_lower or "business analyst" in response_lower:
            return "business_analyst"
        elif "developer" in response_lower:
            return "developer"
        elif "tester" in response_lower:
            return "tester"
        else:
            return "business_analyst"  # Default fallback
