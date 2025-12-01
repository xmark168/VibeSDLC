"""
Developer V2 LangGraph - Story Implementation Flow.

Story flow: setup → analyze → plan → implement ⟷ run_code → END
                                       ↑              ↓
Bug fix flow:                 analyze_error ──────────┘
                                    ↓
                                implement → run_code
"""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    setup_workspace, analyze, plan, implement,
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


def route_after_analyze_error(state: DeveloperState) -> Literal["implement", "__end__"]:
    """Route after error analysis - goes directly to implement with fix plan."""
    action = state.get("action")
    if action == "IMPLEMENT":
        return "implement"
    return "__end__"


class DeveloperGraph:
    """Story implementation workflow (6 nodes).
    
    Nodes:
    1. setup_workspace - Git + CocoIndex
    2. analyze - Story analysis
    3. plan - Implementation plan
    4. implement - Code generation
    5. run_code - Lint + tests
    6. analyze_error - Error analysis + fix planning
    
    Story flow: setup -> analyze -> plan -> implement -> run_code -> END
    Bug fix flow: run_code FAIL -> analyze_error -> implement -> run_code
    """
    
    def __init__(self, agent=None):
        self.agent = agent
        g = StateGraph(DeveloperState)
        
        # 6 nodes
        g.add_node("setup_workspace", partial(setup_workspace, agent=agent))
        g.add_node("analyze", partial(analyze, agent=agent))
        g.add_node("plan", partial(plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("run_code", partial(run_code, agent=agent))
        g.add_node("analyze_error", partial(analyze_error, agent=agent))
        
        # Entry point
        g.set_entry_point("setup_workspace")
        
        # Linear flow: setup -> analyze -> plan -> implement
        g.add_edge("setup_workspace", "analyze")
        g.add_edge("analyze", "plan")
        g.add_edge("plan", "implement")
        
        # Implement loop
        g.add_conditional_edges("implement", route_after_implement)
        
        # Test + bug fix loop
        g.add_conditional_edges("run_code", route_after_test)
        g.add_conditional_edges("analyze_error", route_after_analyze_error)
        
        self.graph = g.compile()
