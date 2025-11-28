"""Tester LangGraph with conditional routing."""

import logging
from functools import partial
from langgraph.graph import StateGraph, END

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.nodes import (
    setup_context,
    router,
    query_stories,
    analyze_stories,
    generate_test_cases,
    generate_test_file,
    send_response,
    test_status,
    conversation,
)

logger = logging.getLogger(__name__)


def _route_action(state: TesterState) -> str:
    """Route based on action from router node."""
    action = state.get("action", "CONVERSATION")
    
    if action == "GENERATE_TESTS":
        return "query_stories"
    elif action == "TEST_STATUS":
        return "test_status"
    else:
        return "conversation"


class TesterGraph:
    """LangGraph-based Tester with routing."""
    
    def __init__(self, agent=None):
        self.agent = agent
        
        graph = StateGraph(TesterState)
        
        # Add nodes (pass agent reference where needed)
        graph.add_node("setup_context", partial(setup_context, agent=agent))
        graph.add_node("router", partial(router, agent=agent))
        
        # Generate tests flow
        graph.add_node("query_stories", partial(query_stories, agent=agent))
        graph.add_node("analyze_stories", analyze_stories)
        graph.add_node("generate_test_cases", generate_test_cases)
        graph.add_node("generate_test_file", generate_test_file)
        graph.add_node("send_response", partial(send_response, agent=agent))
        
        # Tool-based nodes
        graph.add_node("test_status", partial(test_status, agent=agent))
        graph.add_node("conversation", partial(conversation, agent=agent))
        
        # Entry → setup → router
        graph.set_entry_point("setup_context")
        graph.add_edge("setup_context", "router")
        
        # Conditional routing
        graph.add_conditional_edges("router", _route_action, {
            "query_stories": "query_stories",
            "test_status": "test_status",
            "conversation": "conversation",
        })
        
        # Generate tests flow
        graph.add_edge("query_stories", "analyze_stories")
        graph.add_edge("analyze_stories", "generate_test_cases")
        graph.add_edge("generate_test_cases", "generate_test_file")
        graph.add_edge("generate_test_file", "send_response")
        graph.add_edge("send_response", END)
        
        # Tool nodes → END
        graph.add_edge("test_status", END)
        graph.add_edge("conversation", END)
        
        self.graph = graph.compile()
        logger.info("[TesterGraph] Compiled with routing")
