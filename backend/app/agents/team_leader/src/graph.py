"""Team Leader LangGraph."""

from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.nodes import router, delegate, respond, clarify, conversational, status_check, extract_preferences, confirm_replace


def route(state: TeamLeaderState) -> Literal["delegate", "extract_preferences", "conversational", "status_check", "clarify", "confirm_replace"]:
    """Route to action node. RESPOND goes through extract_preferences first."""
    action = state.get("action")
    if action == "DELEGATE":
        return "delegate"
    if action == "CONVERSATION":
        return "conversational"
    if action == "STATUS_CHECK":
        return "status_check"
    if action == "CLARIFY":
        return "clarify"
    if action == "CONFIRM_REPLACE":
        return "confirm_replace"
    return "extract_preferences"


class TeamLeaderGraph:
    """LangGraph-based Team Leader with Lean Kanban integration."""
    
    def __init__(self, agent=None):
        self.agent = agent
        g = StateGraph(TeamLeaderState)
        
        g.add_node("router", partial(router, agent=agent))
        g.add_node("extract_preferences", partial(extract_preferences, agent=agent))
        g.add_node("delegate", partial(delegate, agent=agent))
        g.add_node("respond", partial(respond, agent=agent))
        g.add_node("clarify", partial(clarify, agent=agent))
        g.add_node("conversational", partial(conversational, agent=agent))
        g.add_node("status_check", partial(status_check, agent=agent))
        g.add_node("confirm_replace", partial(confirm_replace, agent=agent))
        
        g.set_entry_point("router")
        g.add_conditional_edges("router", route)
        g.add_edge("extract_preferences", "respond")
        
        for node in ["delegate", "respond", "clarify", "conversational", "status_check", "confirm_replace"]:
            g.add_edge(node, END)
        
        self.graph = g.compile()
