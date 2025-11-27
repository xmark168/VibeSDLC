"""Team Leader LangGraph implementation."""

import logging
from functools import partial
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.team_leader.src.state import TeamLeaderState
from app.agents.team_leader.src.nodes import llm_routing, delegate, respond

logger = logging.getLogger(__name__)


def route_after_llm(state: TeamLeaderState) -> Literal["delegate", "respond"]:
    """Conditional edge: Route after LLM decision."""
    if state.get("action") == "DELEGATE":
        return "delegate"
    else:
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
        
        graph.add_node("llm_routing", partial(llm_routing, agent=agent))
        graph.add_node("delegate", partial(delegate, agent=agent))
        graph.add_node("respond", partial(respond, agent=agent))
        
        graph.set_entry_point("llm_routing")
        
        graph.add_conditional_edges(
            "llm_routing",
            route_after_llm,
            {
                "delegate": "delegate",
                "respond": "respond"
            }
        )
        
        graph.add_edge("delegate", END)
        graph.add_edge("respond", END)
        
        self.graph = graph.compile()
        
        logger.info("[TeamLeaderGraph] LLM-only routing graph compiled")
