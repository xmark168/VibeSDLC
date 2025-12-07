"""Developer V2 LangGraph - Story Implementation Workflow.

This module defines the DeveloperGraph class, a LangGraph state machine
that orchestrates the complete story-to-code workflow with 7 nodes.

Workflow Diagram:
    setup_workspace -> analyze_and_plan -> implement -> review
                                              ^           |
                                              |   LBTM    v
                                              +-----------+
                                                          | LGTM
                                                          v
    END <- run_code <- summarize <------------------------+
             |
             | FAIL (debug_count < 5)
             v
        analyze_error -> implement

Key Features:
    - Conditional routing for code review loops (LGTM/LBTM)
    - Error recovery with analyze_error node
    - Configurable review skipping via use_code_review flag
    - Adaptive per-step LBTM limits based on complexity (low=1, medium=2, high=3)
"""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    setup_workspace, analyze_and_plan, implement,
    run_code, analyze_error,
    review, route_after_review,
    summarize, route_after_summarize,
)


def route_after_implement(state: DeveloperState) -> Literal["review", "implement", "summarize"]:
    """Route after implement based on complexity and use_code_review flag.
    
    Optimization: Skip review for low complexity stories to save ~25-50s.
    """
    # Skip review for low complexity (optimization)
    complexity = state.get("complexity", "medium")
    if complexity == "low":
        current_step = state.get("current_step", 0)
        total_steps = state.get("total_steps", 0)
        if current_step < total_steps:
            return "implement"
        return "summarize"
    
    if state.get("use_code_review", True):
        return "review"
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    if current_step < total_steps:
        return "implement"
    return "summarize"


def route_review_result(state: DeveloperState) -> Literal["implement", "summarize", "run_code"]:
    """Route based on review result (LGTM/LBTM).
    
    Note: Adaptive per-step LBTM limit based on complexity (low=1, medium=2, high=3)
    is enforced in review node. If step reaches limit, review forces LGTM.
    """
    review_result = state.get("review_result", "LGTM")
    
    # Per-step limit enforced in review node (forces LGTM after 2 attempts)
    if review_result == "LBTM":
        return "implement"
    
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    if current_step < total_steps:
        return "implement"
    
    # Skip summarize if all LGTM
    if state.get("total_lbtm_count", 0) == 0:
        return "run_code"
    return "summarize"


def route_summarize_result(state: DeveloperState) -> Literal["implement", "run_code"]:
    """Route based on IS_PASS result."""
    is_pass = state.get("is_pass", "YES")
    if is_pass == "NO" and state.get("summarize_count", 0) < 2:
        return "implement"
    return "run_code"


def route_after_test(state: DeveloperState) -> Literal["analyze_error", "__end__"]:
    """Route based on test result."""
    run_result = state.get("run_result", {})
    if run_result.get("status", "PASS") == "PASS":
        return "__end__"
    if state.get("debug_count", 0) < 5:
        return "analyze_error"
    return "__end__"


def route_after_analyze_error(state: DeveloperState) -> Literal["implement", "__end__"]:
    """Route after error analysis."""
    if state.get("action") == "IMPLEMENT":
        return "implement"
    return "__end__"


class DeveloperGraph:
    """LangGraph state machine for story-driven code generation.

    Sequential flow with per-step review:
    setup_workspace -> analyze_and_plan -> implement <-> review (LBTM loop)
                                                           |
                                                         LGTM
                                                           v
                                       END <- run_code <- summarize
                                               |
                                             FAIL
                                               v
                                         analyze_error -> implement

    Attrs: agent (DeveloperV2), graph (compiled StateGraph)
    Limits: max 5 debug iterations, adaptive LBTM per step (low=1, medium=2, high=3)
    """
    
    def __init__(self, agent=None):
        self.agent = agent
        g = StateGraph(DeveloperState)
        
        # All nodes
        g.add_node("setup_workspace", partial(setup_workspace, agent=agent))
        g.add_node("analyze_and_plan", partial(analyze_and_plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("review", partial(review, agent=agent))
        g.add_node("summarize", partial(summarize, agent=agent))
        g.add_node("run_code", partial(run_code, agent=agent))
        g.add_node("analyze_error", partial(analyze_error, agent=agent))
        
        # Sequential edges
        g.set_entry_point("setup_workspace")
        g.add_edge("setup_workspace", "analyze_and_plan")
        g.add_edge("analyze_and_plan", "implement")
        g.add_conditional_edges("implement", route_after_implement)
        g.add_conditional_edges("review", route_review_result)
        g.add_conditional_edges("summarize", route_summarize_result)
        g.add_conditional_edges("run_code", route_after_test)
        g.add_conditional_edges("analyze_error", route_after_analyze_error)
        
        self.graph = g.compile()
