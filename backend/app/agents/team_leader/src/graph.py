"""Team Leader LangGraph implementation."""

import logging
from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.nodes import (
    extract_preferences, router, delegate, respond, conversational
)

logger = logging.getLogger(__name__)


def route(state: TeamLeaderState) -> Literal["delegate", "respond", "conversational"]:
    """Route based on action decision."""
    action = state.get("action")
    if action == "DELEGATE":
        return "delegate"
    elif action == "CONVERSATION":
        return "conversational"
    return "respond"


class TeamLeaderGraph:
    """LangGraph-based Team Leader graph.
    
    Flow: extract_preferences → router → delegate/respond/conversational
    """
    
    def __init__(self, agent=None):
        """Initialize graph with reference to agent.
        
        Args:
            agent: TeamLeader agent instance (for delegation/messaging)
        """
        self.agent = agent
        
        graph = StateGraph(TeamLeaderState)
        
        # Nodes
        graph.add_node("extract_preferences", partial(extract_preferences, agent=agent))
        graph.add_node("router", partial(router, agent=agent))
        graph.add_node("delegate", partial(delegate, agent=agent))
        graph.add_node("respond", partial(respond, agent=agent))
        graph.add_node("conversational", partial(conversational, agent=agent))
        
        # Flow: extract_preferences → router → delegate/respond/conversational
        graph.set_entry_point("extract_preferences")
        graph.add_edge("extract_preferences", "router")
        
        graph.add_conditional_edges("router", route, {
            "delegate": "delegate",
            "respond": "respond",
            "conversational": "conversational",
        })
        
        graph.add_edge("delegate", END)
        graph.add_edge("respond", END)
        graph.add_edge("conversational", END)
        
        self.graph = graph.compile()
        
        logger.info("[TeamLeaderGraph] Graph compiled with conversational node")
