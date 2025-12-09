"""Developer V2 LangGraph - Story Implementation Workflow."""

from functools import partial
from typing import Literal
from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    setup_workspace, plan, implement, implement_parallel,
    run_code, analyze_error, review, route_after_review,
)


def route_after_implement(state: DeveloperState) -> Literal["review", "implement", "run_code"]:
    """Route after implement. Skip review for low complexity."""
    complexity = state.get("complexity", "medium")
    if complexity == "low":
        current_step = state.get("current_step", 0)
        total_steps = state.get("total_steps", 0)
        return "implement" if current_step < total_steps else "run_code"
    
    if state.get("use_code_review", True):
        return "review"
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    return "implement" if current_step < total_steps else "run_code"


def route_review_result(state: DeveloperState) -> Literal["implement", "run_code"]:
    """Route based on review result (LGTM/LBTM)."""
    if state.get("review_result", "LGTM") == "LBTM":
        return "implement"
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    return "implement" if current_step < total_steps else "run_code"


def route_after_test(state: DeveloperState) -> Literal["analyze_error", "__end__"]:
    run_result = state.get("run_result", {})
    if run_result.get("status", "PASS") == "PASS":
        return "__end__"
    return "analyze_error" if state.get("debug_count", 0) < 5 else "__end__"


def route_after_analyze_error(state: DeveloperState) -> Literal["implement", "__end__"]:
    return "implement" if state.get("action") == "IMPLEMENT" else "__end__"


class DeveloperGraph:
    """LangGraph state machine for story-driven code generation.
    Parallel: setup -> plan -> implement_parallel -> run_code -> END
    Sequential: setup -> plan -> implement <-> review -> run_code -> END
    """
    
    def __init__(self, agent=None, parallel=True):
        self.agent = agent
        self.parallel = parallel
        g = StateGraph(DeveloperState)
        
        g.add_node("setup_workspace", partial(setup_workspace, agent=agent))
        g.add_node("plan", partial(plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("implement_parallel", partial(implement_parallel, agent=agent))
        g.add_node("review", partial(review, agent=agent))
        g.add_node("run_code", partial(run_code, agent=agent))
        g.add_node("analyze_error", partial(analyze_error, agent=agent))
        
        g.set_entry_point("setup_workspace")
        g.add_edge("setup_workspace", "plan")
        
        if parallel:
            g.add_edge("plan", "implement_parallel")
            g.add_edge("implement_parallel", "run_code")
            g.add_edge("implement", "run_code")
        else:
            g.add_edge("plan", "implement")
            g.add_conditional_edges("implement", route_after_implement)
            g.add_conditional_edges("review", route_review_result)
        
        g.add_conditional_edges("run_code", route_after_test)
        g.add_conditional_edges("analyze_error", route_after_analyze_error)
        
        self.graph = g.compile()
