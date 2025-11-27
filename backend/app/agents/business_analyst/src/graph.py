"""LangGraph Workflow for Business Analyst"""

import logging
from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from .state import BAState
from .nodes import (
    analyze_intent,
    interview_requirements,
    ask_questions,
    generate_prd,
    update_prd,
    extract_stories,
    analyze_domain,
    save_artifacts,
)

logger = logging.getLogger(__name__)


def route_by_intent(state: BAState) -> Literal["interview", "prd_create", "prd_update", "extract_stories", "domain_analysis"]:
    """Router: Direct flow based on classified intent."""
    intent = state.get("intent", "interview")
    reasoning = state.get("reasoning", "")
    collected_info = state.get("collected_info", {})
    
    # FORCE INTERVIEW if trying to create/update PRD without collected info
    if intent in ["prd_create", "prd_update"] and not collected_info:
        logger.warning(
            f"[BA Graph] Overriding '{intent}' -> 'interview': "
            f"No collected info yet, need to gather requirements first"
        )
        return "interview"
    
    logger.info(f"[BA Graph] Routing to '{intent}': {reasoning[:80] if reasoning else 'no reason'}")
    return intent


def should_ask_questions(state: BAState) -> Literal["ask", "save"]:
    """Router: Decide whether to ask questions or skip to save."""
    has_questions = bool(state.get("questions"))
    
    if has_questions:
        logger.info(f"[BA Graph] {len(state.get('questions', []))} questions to ask")
        return "ask"
    else:
        logger.info("[BA Graph] No questions, skipping to save")
        return "save"


class BusinessAnalystGraph:
    """LangGraph-based Business Analyst workflow.
    
    Graph structure:
        START
          |
        analyze_intent (classify user request)
          |
        ROUTER (conditional edges)
          |- interview -> ask_questions -> save
          |- prd_create -> generate_prd -> save
          |- prd_update -> update_prd -> save
          |- extract_stories -> save
          |- domain_analysis -> save
          |
        END
    """
    
    def __init__(self, agent=None):
        """Initialize graph with reference to agent.
        
        Args:
            agent: BusinessAnalyst agent instance (for Langfuse callback access)
        """
        self.agent = agent
        
        graph = StateGraph(BAState)
        
        # Add nodes with agent reference using partial
        graph.add_node("analyze_intent", partial(analyze_intent, agent=agent))
        graph.add_node("interview_requirements", partial(interview_requirements, agent=agent))
        graph.add_node("ask_questions", partial(ask_questions, agent=agent))
        graph.add_node("generate_prd", partial(generate_prd, agent=agent))
        graph.add_node("update_prd", partial(update_prd, agent=agent))
        graph.add_node("extract_stories", partial(extract_stories, agent=agent))
        graph.add_node("analyze_domain", partial(analyze_domain, agent=agent))
        graph.add_node("save_artifacts", partial(save_artifacts, agent=agent))
        
        # Set entry point
        graph.set_entry_point("analyze_intent")
        
        # Add conditional routing after intent analysis
        graph.add_conditional_edges(
            "analyze_intent",
            route_by_intent,
            {
                "interview": "interview_requirements",
                "prd_create": "generate_prd",
                "prd_update": "update_prd",
                "extract_stories": "extract_stories",
                "domain_analysis": "analyze_domain"
            }
        )
        
        # Interview flow: generate questions -> ask -> save
        graph.add_conditional_edges(
            "interview_requirements",
            should_ask_questions,
            {
                "ask": "ask_questions",
                "save": "save_artifacts"
            }
        )
        graph.add_edge("ask_questions", "save_artifacts")
        
        # PRD flows -> save
        graph.add_edge("generate_prd", "save_artifacts")
        graph.add_edge("update_prd", "save_artifacts")
        
        # Stories flow -> save
        graph.add_edge("extract_stories", "save_artifacts")
        
        # Domain analysis -> save
        graph.add_edge("analyze_domain", "save_artifacts")
        
        # Save -> END
        graph.add_edge("save_artifacts", END)
        
        self.graph = graph.compile()
        
        logger.info("[BA Graph] Graph compiled and ready")
    
    async def execute(self, initial_state: dict) -> dict:
        """Execute graph with initial state."""
        logger.info(f"[BA Graph] Starting execution...")
        
        try:
            result = await self.graph.ainvoke(initial_state)
            
            logger.info(
                f"[BA Graph] Execution complete: "
                f"intent={result.get('intent')}, "
                f"complete={result.get('is_complete', False)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[BA Graph] Execution failed: {e}", exc_info=True)
            raise
