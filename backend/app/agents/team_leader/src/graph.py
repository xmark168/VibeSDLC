"""Team Leader LangGraph implementation."""

import logging
from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.nodes import extract_preferences, llm_routing, delegate, respond

logger = logging.getLogger(__name__)


def route_after_llm(state: TeamLeaderState) -> Literal["delegate", "respond"]:
    """Conditional edge: Route after LLM decision."""
    if state.get("action") == "DELEGATE":
        return "delegate"
    return "respond"


class TeamLeaderGraph:
    """LangGraph-based Team Leader routing graph."""
    
    def __init__(self, agent=None):
        """Initialize graph with reference to agent.
        
        Args:
            agent: TeamLeader agent instance (for delegation/messaging)
        """
        self.agent = agent
        
        graph = StateGraph(TeamLeaderState)
        
        # Node 0: Silent preference extraction (runs first)
        graph.add_node("extract_preferences", partial(extract_preferences, agent=agent))
        # Node 1: LLM routing decision
        graph.add_node("llm_routing", partial(llm_routing, agent=agent))
        # Node 2: Delegate to specialist
        graph.add_node("delegate", partial(delegate, agent=agent))
        # Node 3: Respond directly
        graph.add_node("respond", partial(respond, agent=agent))
        
        # Flow: extract_preferences → llm_routing → delegate/respond
        graph.set_entry_point("extract_preferences")
        graph.add_edge("extract_preferences", "llm_routing")
        
        graph.add_conditional_edges(
            "llm_routing",
            route_after_llm,
            {
                "delegate": "delegate",
                "respond": "respond",
            }
        )
        
        graph.add_edge("delegate", END)
        graph.add_edge("respond", END)
        
        self.graph = graph.compile()
        
        logger.info("[TeamLeaderGraph] LLM-only routing graph compiled")
