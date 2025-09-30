"""LangGraph Studio entry point for the Task Agent."""

from app.agents.task_agent import TaskAgent

def get_graph():
    """Get the compiled LangGraph for LangGraph Studio."""
    agent = TaskAgent()
    return agent.graph

# For LangGraph Studio
graph = get_graph()