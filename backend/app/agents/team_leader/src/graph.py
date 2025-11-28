"""Team Leader LangGraph implementation."""

import logging
from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.nodes import (
    extract_preferences, router, delegate, respond, conversational, status_check
)

logger = logging.getLogger(__name__)


def route(state: TeamLeaderState) -> Literal["delegate", "respond", "conversational", "status_check"]:
    """Route based on action decision."""
    action = state.get("action")
    if action == "DELEGATE":
        return "delegate"
    elif action == "CONVERSATION":
        return "conversational"
    elif action == "STATUS_CHECK":
        return "status_check"
    return "respond"


class TeamLeaderGraph:
    """LangGraph-based Team Leader graph with Lean Kanban integration.
    
  
    """
    
    def __init__(self, agent=None):
        """Initialize graph with reference to agent.
        
        Args:
            agent: TeamLeader agent instance (for delegation/messaging)
        """
        self.agent = agent
        
        graph = StateGraph(TeamLeaderState)
        
        # Nodes (Kanban context fetched lazily in router, not as separate node)
        graph.add_node("extract_preferences", partial(extract_preferences, agent=agent))
        graph.add_node("router", partial(router, agent=agent))
        graph.add_node("delegate", partial(delegate, agent=agent))
        graph.add_node("respond", partial(respond, agent=agent))
        graph.add_node("conversational", partial(conversational, agent=agent))
        graph.add_node("status_check", partial(status_check, agent=agent))
        
        # Flow: extract_preferences → router → action nodes
        graph.set_entry_point("extract_preferences")
        graph.add_edge("extract_preferences", "router")
        
        graph.add_conditional_edges("router", route, {
            "delegate": "delegate",
            "respond": "respond",
            "conversational": "conversational",
            "status_check": "status_check",
        })
        
        graph.add_edge("delegate", END)
        graph.add_edge("respond", END)
        graph.add_edge("conversational", END)
        graph.add_edge("status_check", END)
        
        self.graph = graph.compile()
        
        logger.info("[TeamLeaderGraph] Graph compiled with lazy Kanban loading")
