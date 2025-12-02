"""
Developer V2 LangGraph - Story Implementation Flow.

Story flow: setup → analyze_and_plan → implement ⟷ run_code → END
                                         ↑              ↓
Bug fix flow:                   analyze_error ──────────┘
                                      ↓
                                  implement → run_code
"""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    setup_workspace, analyze_and_plan, implement,
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
    """Story implementation workflow (5 nodes).
    
    Nodes:
    1. setup_workspace - Git + CocoIndex
    2. analyze_and_plan - Combined analysis + planning (single LLM call)
    3. implement - Code generation
    4. run_code - Lint + tests
    5. analyze_error - Error analysis + fix planning
    
    Story flow: setup -> analyze_and_plan -> implement -> run_code -> END
    Bug fix flow: run_code FAIL -> analyze_error -> implement -> run_code
    """
    
    def __init__(self, agent=None):
        self.agent = agent
        g = StateGraph(DeveloperState)
        
        # 5 nodes (merged analyze + plan)
        g.add_node("setup_workspace", partial(setup_workspace, agent=agent))
        g.add_node("analyze_and_plan", partial(analyze_and_plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("run_code", partial(run_code, agent=agent))
        g.add_node("analyze_error", partial(analyze_error, agent=agent))
        
        # Entry point
        g.set_entry_point("setup_workspace")
        
        # Linear flow: setup -> analyze_and_plan -> implement
        g.add_edge("setup_workspace", "analyze_and_plan")
        g.add_edge("analyze_and_plan", "implement")
        
        # Implement loop
        g.add_conditional_edges("implement", route_after_implement)
        
        # Test + bug fix loop
        g.add_conditional_edges("run_code", route_after_test)
        g.add_conditional_edges("analyze_error", route_after_analyze_error)
        
        self.graph = g.compile()
