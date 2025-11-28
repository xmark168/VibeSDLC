"""Tester LangGraph implementation."""

import logging

from langgraph.graph import StateGraph, END

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.nodes import (
    query_stories,
    analyze_stories,
    generate_test_cases,
    generate_test_file
)

logger = logging.getLogger(__name__)


class TesterGraph:
    """LangGraph-based Tester for integration test generation.
    
    Graph flow:
        query_stories → analyze_stories → generate_test_cases → generate_test_file → END
    """
    
    def __init__(self, agent=None):
        """Initialize graph with reference to agent.
        
        Args:
            agent: Tester agent instance (for messaging if needed)
        """
        self.agent = agent
        self.graph = self._build_graph()
        logger.info("[TesterGraph] Graph compiled successfully")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph."""
        graph = StateGraph(TesterState)
        
        # Add nodes
        graph.add_node("query_stories", query_stories)
        graph.add_node("analyze_stories", analyze_stories)
        graph.add_node("generate_test_cases", generate_test_cases)
        graph.add_node("generate_test_file", generate_test_file)
        
        # Set entry point and edges
        graph.set_entry_point("query_stories")
        graph.add_edge("query_stories", "analyze_stories")
        graph.add_edge("analyze_stories", "generate_test_cases")
        graph.add_edge("generate_test_cases", "generate_test_file")
        graph.add_edge("generate_test_file", END)
        
        return graph.compile()
