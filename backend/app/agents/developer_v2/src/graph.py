"""
Developer V2 LangGraph - Story Implementation Flow.

Flow: setup → analyze → design → plan → implement ⟷ run_code → END
                                   ↑                    ↓
                                   └── analyze_error ───┘

Bug fix flow reuses plan + implement nodes with skill system.
"""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    setup_workspace, analyze, design, plan, implement,
    run_code, analyze_error,
)


def route_after_implement(state: DeveloperState) -> Literal["implement", "run_code"]:
    """Implement loop control."""
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if current_step < total_steps:
        return "implement"
    return "run_code"


def route_after_test(state: DeveloperState) -> Literal["analyze_error", "__end__"]:
    """Test result routing."""
    run_result = state.get("run_result", {})
    status = run_result.get("status", "PASS")
    debug_count = state.get("debug_count", 0)
    max_debug = state.get("max_debug", 5)
    
    if status == "PASS":
        return "__end__"
    if status == "RETRY" or debug_count < max_debug:
        return "analyze_error"
    return "__end__"


def route_after_analyze_error(state: DeveloperState) -> Literal["debug_error", "__end__"]:
    """Route after error analysis."""
    error_analysis = state.get("error_analysis", {})
    if error_analysis.get("should_continue", True):
        return "debug_error"
    return "__end__"


class DeveloperGraph:
    """Story implementation workflow (8 nodes).
    
    Nodes:
    1. setup_workspace - Git + CocoIndex
    2. analyze - Story analysis
    3. design - Technical design
    4. plan - Implementation plan
    5. implement - Code generation
    6. run_code - Lint + tests
    7. analyze_error - Pre-debug analysis
    8. debug_error - Fix errors
    """
    
    def __init__(self, agent=None):
        self.agent = agent
        g = StateGraph(DeveloperState)
        
        # 8 nodes
        g.add_node("setup_workspace", partial(setup_workspace, agent=agent))
        g.add_node("analyze", partial(analyze, agent=agent))
        g.add_node("design", partial(design, agent=agent))
        g.add_node("plan", partial(plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("run_code", partial(run_code, agent=agent))
        g.add_node("analyze_error", partial(analyze_error, agent=agent))
        g.add_node("debug_error", partial(debug_error, agent=agent))
        
        # Entry point: directly to setup
        g.set_entry_point("setup_workspace")
        
        # Linear flow
        g.add_edge("setup_workspace", "analyze")
        g.add_edge("analyze", "design")
        g.add_edge("design", "plan")
        g.add_edge("plan", "implement")
        
        # Implement loop
        g.add_conditional_edges("implement", route_after_implement)
        
        # Test + debug loop
        g.add_conditional_edges("run_code", route_after_test)
        g.add_conditional_edges("analyze_error", route_after_analyze_error)
        g.add_edge("debug_error", "run_code")
        
        self.graph = g.compile()
