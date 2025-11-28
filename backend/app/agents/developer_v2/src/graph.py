"""Developer V2 LangGraph Definition."""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes import (
    router, analyze, plan, implement, validate, clarify, respond
)


def route(state: DeveloperState) -> Literal["analyze", "plan", "implement", "validate", "clarify", "respond"]:
    """Route to appropriate node based on action."""
    action = state.get("action")
    
    if action == "ANALYZE":
        return "analyze"
    if action == "PLAN":
        return "plan"
    if action == "IMPLEMENT":
        return "implement"
    if action == "VALIDATE":
        return "validate"
    if action == "CLARIFY":
        return "clarify"
    return "respond"


def should_continue(state: DeveloperState) -> Literal["implement", "validate", "respond"]:
    """Check if implementation should continue or move to next phase."""
    action = state.get("action")
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if action == "IMPLEMENT" and current_step < total_steps:
        return "implement"
    if action == "VALIDATE":
        return "validate"
    return "respond"


class DeveloperGraph:
    """LangGraph-based Developer V2 for story processing."""
    
    def __init__(self, agent=None):
        self.agent = agent
        g = StateGraph(DeveloperState)
        
        g.add_node("router", partial(router, agent=agent))
        g.add_node("analyze", partial(analyze, agent=agent))
        g.add_node("plan", partial(plan, agent=agent))
        g.add_node("implement", partial(implement, agent=agent))
        g.add_node("validate", partial(validate, agent=agent))
        g.add_node("clarify", partial(clarify, agent=agent))
        g.add_node("respond", partial(respond, agent=agent))
        
        g.set_entry_point("router")
        
        g.add_conditional_edges("router", route)
        
        g.add_edge("analyze", "plan")
        g.add_edge("plan", "implement")
        g.add_conditional_edges("implement", should_continue)
        g.add_edge("validate", "respond")
        g.add_edge("clarify", END)
        g.add_edge("respond", END)
        
        self.graph = g.compile()
