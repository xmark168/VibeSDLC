"""LangGraph Workflow for Business Analyst"""

import logging
from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from .state import BAState
from .nodes import (
    analyze_intent,
    interview_requirements,
    ask_one_question,
    ask_batch_questions,
    process_answer,
    process_batch_answers,
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


def should_continue_or_wait(state: BAState) -> Literal["wait", "next_question", "generate_prd"]:
    """Router: After asking/processing, decide next step.
    
    - wait: Question sent, waiting for user answer (END this run)
    - next_question: More questions to ask
    - generate_prd: All questions answered, generate PRD
    """
    waiting = state.get("waiting_for_answer", False)
    all_answered = state.get("all_questions_answered", False)
    
    if waiting:
        logger.info("[BA Graph] Waiting for user answer, pausing execution")
        return "wait"
    elif all_answered:
        logger.info("[BA Graph] All questions answered, proceeding to PRD generation")
        return "generate_prd"
    else:
        logger.info("[BA Graph] More questions to ask")
        return "next_question"


def batch_after_ask(state: BAState) -> Literal["wait", "generate_prd"]:
    """Router: After asking batch questions, wait or generate PRD."""
    waiting = state.get("waiting_for_answer", False)
    all_answered = state.get("all_questions_answered", False)
    
    if waiting:
        logger.info("[BA Graph] Batch questions sent, waiting for all answers")
        return "wait"
    elif all_answered:
        logger.info("[BA Graph] All batch answers received, generating PRD")
        return "generate_prd"
    else:
        # If no questions, go to PRD
        return "generate_prd"


class BusinessAnalystGraph:
    
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
        # Sequential mode nodes (deprecated but kept for compatibility)
        graph.add_node("ask_one_question", partial(ask_one_question, agent=agent))
        graph.add_node("process_answer", partial(process_answer, agent=agent))
        # Batch mode nodes (preferred)
        graph.add_node("ask_batch_questions", partial(ask_batch_questions, agent=agent))
        graph.add_node("process_batch_answers", partial(process_batch_answers, agent=agent))
        # PRD and other nodes
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
        
        # Interview flow: generate questions -> ask ALL at once (batch mode)
        graph.add_conditional_edges(
            "interview_requirements",
            should_ask_questions,
            {
                "ask": "ask_batch_questions",  # Use batch mode
                "save": "save_artifacts"
            }
        )
        
        # After asking batch questions: wait for all answers
        graph.add_conditional_edges(
            "ask_batch_questions",
            batch_after_ask,
            {
                "wait": END,  # Pause, wait for user answers (RESUME will call process_batch_answers)
                "generate_prd": "generate_prd"  # All answered, generate PRD
            }
        )
        
        # After processing batch answers: generate PRD
        graph.add_edge("process_batch_answers", "generate_prd")
        
        # Keep sequential mode edges for backward compatibility (not used in main flow)
        graph.add_conditional_edges(
            "ask_one_question",
            should_continue_or_wait,
            {
                "wait": END,
                "next_question": "ask_one_question",
                "generate_prd": "generate_prd"
            }
        )
        
        graph.add_conditional_edges(
            "process_answer",
            should_continue_or_wait,
            {
                "wait": END,
                "next_question": "ask_one_question",
                "generate_prd": "generate_prd"
            }
        )
        
        # PRD creation -> extract stories -> save
        graph.add_edge("generate_prd", "extract_stories")
        graph.add_edge("extract_stories", "save_artifacts")
        
        # PRD update -> save (no story extraction needed)
        graph.add_edge("update_prd", "save_artifacts")
        
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
