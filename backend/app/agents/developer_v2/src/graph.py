"""
Developer V2 LangGraph Definition - Simplified MetaGPT-inspired Flow.

Flow: router → setup → analyze → plan → implement → run_code → respond
                                          ↑___________↓
                                         (debug loop)
"""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    router, setup_workspace, analyze, design, plan, implement,
    run_code, analyze_error, debug_error, respond, clarify
)


def route_after_router(state: DeveloperState) -> Literal["setup_workspace", "clarify", "respond"]:
    """Entry routing: workspace setup or direct response."""
    action = state.get("action")
    
    if action == "CLARIFY":
        return "clarify"
    if action == "RESPOND":
        return "respond"
    return "setup_workspace"


def route_after_implement(state: DeveloperState) -> Literal["implement", "run_code", "respond"]:
    """Simple implement loop control.
    
    Routes:
    - More steps → implement (continue)
    - All done → run_code (test)
    - Error → respond (abort)
    """
    error = state.get("error")
    if error:
        return "respond"
    
    action = state.get("action")
    if action == "RESPOND":
        return "respond"
    
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if total_steps == 0:
        return "respond"
    
    if current_step < total_steps:
        return "implement"
    
    return "run_code"


def route_after_test(state: DeveloperState) -> Literal["analyze_error", "respond"]:
    """Test result routing.
    
    Routes:
    - PASS → respond (success)
    - FAIL + retries → analyze_error (analyze before debug)
    - FAIL + exhausted → respond (give up)
    """
    run_result = state.get("run_result", {})
    status = run_result.get("status", "PASS")
    debug_count = state.get("debug_count", 0)
    max_debug = state.get("max_debug", 5)
    
    if status == "PASS":
        return "respond"
    
    # RETRY means packages installed, go to analyze
    if status == "RETRY":
        return "analyze_error"
    
    if debug_count < max_debug:
        return "analyze_error"
    
    # Give up after max attempts
    return "respond"


def route_after_analyze_error(state: DeveloperState) -> Literal["debug_error", "respond"]:
    """Route after error analysis.
    
    Routes:
    - Fixable → debug_error
    - Unfixable → respond
    """
    action = state.get("action")
    if action == "RESPOND":
        return "respond"
    return "debug_error"


class DeveloperGraph:
    """LangGraph workflow for story implementation.
    
    10 nodes:
    1. router - Entry routing
    2. setup_workspace - Git + CocoIndex
    3. analyze - Story analysis
    4. design - Technical design (saves to docs/design.md)
    5. plan - Implementation plan
    6. implement - Code generation
    7. run_code - Lint + tests
    8. analyze_error - Pre-debug analysis
    9. debug_error - Fix errors
    10. respond - Final response
    
    4 routing functions:
    - route_after_router: entry routing
    - route_after_implement: implement loop
    - route_after_test: to analyze_error or respond
    - route_after_analyze_error: to debug_error or respond
    
    Flow:
        router → setup → analyze → design → plan → implement ←→ run_code → respond
                                                      ↑           ↓
                                                      └── analyze_error → debug ──┘
    """
    
    def __init__(self, agent=None):
        self.agent = agent
        g = StateGraph(DeveloperState)
        
        # 10 nodes
        g.add_node("router", partial(router, agent=agent))
        g.add_node("setup_workspace", partial(setup_workspace, agent=agent))
        g.add_node("analyze", partial(analyze, agent=agent))
        g.add_node("design", partial(design, agent=agent))
        g.add_node("plan", partial(plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("run_code", partial(run_code, agent=agent))
        g.add_node("analyze_error", partial(analyze_error, agent=agent))
        g.add_node("debug_error", partial(debug_error, agent=agent))
        g.add_node("respond", partial(respond, agent=agent))
        g.add_node("clarify", partial(clarify, agent=agent))
        
        # Entry point
        g.set_entry_point("router")
        
        # Router → setup or clarify or respond
        g.add_conditional_edges("router", route_after_router)
        
        # Linear flow: setup → analyze → design → plan → implement
        g.add_edge("setup_workspace", "analyze")
        g.add_edge("analyze", "design")
        g.add_edge("design", "plan")
        g.add_edge("plan", "implement")
        
        # Implement loop
        g.add_conditional_edges("implement", route_after_implement)
        
        # Test → analyze_error → debug loop
        g.add_conditional_edges("run_code", route_after_test)
        g.add_conditional_edges("analyze_error", route_after_analyze_error)
        g.add_edge("debug_error", "run_code")
        
        # End nodes
        g.add_edge("respond", END)
        g.add_edge("clarify", END)
        
        self.graph = g.compile()
