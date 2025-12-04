"""
Developer V2 LangGraph - Story Implementation Flow (MetaGPT-style).

Story flow: setup → analyze_and_plan → implement → review ─→ [next_step or summarize]
                                          ↑          │              ↓
                                          └── LBTM ──┘         run_code → END
                                                                   ↓
Bug fix flow:                                             analyze_error
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
    """After implement, route based on use_code_review flag (MetaGPT-style)."""
    use_code_review = state.get("use_code_review", True)  # Default ON
    
    if use_code_review:
        return "review"
    
    # Skip review - go to next step or summarize
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if current_step < total_steps:
        return "implement"  # More steps
    return "summarize"  # All done


def route_review_result(state: DeveloperState) -> Literal["implement", "summarize", "run_code"]:
    """Route based on review result (MetaGPT-style LGTM/LBTM).
    
    Returns:
        - "implement": LBTM, need to re-implement
        - "implement": LGTM but more steps remain
        - "run_code": All LGTM, skip summarize (optimization)
        - "summarize": Had LBTM, need final summary
    """
    review_result = state.get("review_result", "LGTM")
    review_count = state.get("review_count", 0)
    max_reviews = 2
    
    # LBTM: re-implement (with limit)
    if review_result == "LBTM" and review_count < max_reviews:
        return "implement"
    
    # Check if more steps
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if current_step < total_steps:
        return "implement"  # More steps to do
    
    # All steps done - skip summarize if all LGTM (optimization: saves ~10-15s)
    total_lbtm = state.get("total_lbtm_count", 0)
    if total_lbtm == 0:
        return "run_code"  # Skip summarize, go directly to tests
    
    return "summarize"  # Had LBTM, need final summary


def route_summarize_result(state: DeveloperState) -> Literal["implement", "run_code"]:
    """Route based on IS_PASS result (MetaGPT-style).
    
    Returns:
        - "implement": IS_PASS=NO, need to fix issues
        - "run_code": IS_PASS=YES, proceed to validation
    """
    is_pass = state.get("is_pass", "YES")
    summarize_count = state.get("summarize_count", 0)
    max_retries = 2
    
    if is_pass == "NO" and summarize_count < max_retries:
        return "implement"
    
    return "run_code"


def route_after_test(state: DeveloperState) -> Literal["analyze_error", "__end__"]:
    """Test result routing."""
    run_result = state.get("run_result", {})
    status = run_result.get("status", "PASS")
    debug_count = state.get("debug_count", 0)
    max_debug = 5  # Hard limit: max 5 debug attempts
    
    if status == "PASS":
        return "__end__"
    if debug_count < max_debug:
        return "analyze_error"
    return "__end__"  # Stop after 5 debug attempts


def route_after_analyze_error(state: DeveloperState) -> Literal["implement", "__end__"]:
    """Route after error analysis - goes directly to implement with fix plan."""
    action = state.get("action")
    if action == "IMPLEMENT":
        return "implement"
    return "__end__"


class DeveloperGraph:
    """Story implementation workflow (7 nodes) - MetaGPT-style.
    
    Nodes:
    1. setup_workspace - Git + CocoIndex
    2. analyze_and_plan - Combined analysis + planning (single LLM call)
    3. implement - Code generation (resets review_count for fresh attempts)
    4. review - LGTM/LBTM code review (MetaGPT-style, max 2 retries per step)
    5. summarize - IS_PASS final summary (MetaGPT-style, resets count on success)
    6. run_code - Lint + tests (acts as QaEngineer role from MetaGPT)
    7. analyze_error - Error analysis + fix planning
    
    Story flow: setup -> analyze_and_plan -> implement -> review -> [implement or summarize]
                                                                         -> run_code -> END
    Bug fix flow: run_code FAIL -> analyze_error -> implement -> review -> ...
    
    Counter Management:
    - review_count: Reset in implement(), incremented in review() on LBTM
    - summarize_count: Incremented on IS_PASS=NO, reset on YES
    - debug_count: Managed by analyze_error, max 5 attempts
    
    Note: run_code serves as QaEngineer - runs lint, typecheck, and tests
    """
    
    def __init__(self, agent=None):
        self.agent = agent
        g = StateGraph(DeveloperState)
        
        # 7 nodes (MetaGPT-style with review + summarize)
        g.add_node("setup_workspace", partial(setup_workspace, agent=agent))
        g.add_node("analyze_and_plan", partial(analyze_and_plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("review", partial(review, agent=agent))
        g.add_node("summarize", partial(summarize, agent=agent))
        g.add_node("run_code", partial(run_code, agent=agent))
        g.add_node("analyze_error", partial(analyze_error, agent=agent))
        
        # Entry point
        g.set_entry_point("setup_workspace")
        
        # Linear flow: setup -> analyze_and_plan -> implement
        g.add_edge("setup_workspace", "analyze_and_plan")
        g.add_edge("analyze_and_plan", "implement")
        
        # After implement -> review (or skip if use_code_review=False)
        g.add_conditional_edges("implement", route_after_implement)
        
        # Review routing: LBTM -> implement, LGTM -> [implement or summarize]
        g.add_conditional_edges("review", route_review_result)
        
        # Summarize routing: IS_PASS=NO -> implement, YES -> run_code
        g.add_conditional_edges("summarize", route_summarize_result)
        
        # Test + bug fix loop
        g.add_conditional_edges("run_code", route_after_test)
        g.add_conditional_edges("analyze_error", route_after_analyze_error)
        
        self.graph = g.compile()
