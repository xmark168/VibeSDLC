"""Tester Agent - STUBBED (crewai removed).

TODO: Rewrite using LangGraph like developer_v2.
"""

import logging

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel


logger = logging.getLogger(__name__)


class Tester(BaseAgent):
    """Tester agent - STUBBED (crewai removed).
    
    TODO: Implement using LangGraph.
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.warning(f"Tester agent {self.name} is STUBBED - crewai removed")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task - returns not implemented error."""
        return TaskResult(
            success=False,
            output="",
            error_message="Tester agent not implemented (crewai removed). TODO: rewrite with LangGraph.",
        )
