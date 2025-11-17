"""
Business Analyst Agent Implementation

Transforms business requirements into technical specifications.
"""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Any, Dict

from crewai import Agent as CrewAIAgent, Task, Crew
from crewai_tools import FileReadTool, DirectoryReadTool

from app.agents.base import Role, Action, Message
from app.agents.implementations.team_leader import DelegateToBA

logger = logging.getLogger(__name__)


class WritePRD(Action):
    """Write Product Requirements Document."""

    def __init__(self, crewai_agent: CrewAIAgent):
        super().__init__()
        self.crewai_agent = crewai_agent

    async def run(self, context: Any) -> str:
        """Generate PRD using CrewAI."""
        if isinstance(context, Message):
            content = context.content
        else:
            content = str(context)

        task = Task(
            description=f"Create detailed product requirements document for: {content}",
            expected_output="Comprehensive PRD with user stories and acceptance criteria",
            agent=self.crewai_agent,
        )

        loop = asyncio.get_event_loop()
        crew = Crew(agents=[self.crewai_agent], tasks=[task], verbose=False)
        result = await loop.run_in_executor(None, crew.kickoff)

        return str(result)


class BusinessAnalystAgent(Role):
    """
    Business Analyst Agent.

    Watches for delegation from Team Leader, creates specifications.
    """

    def __init__(self):
        super().__init__(
            name="BusinessAnalyst",
            profile="Senior Business Analyst"
        )

        self.config = self._load_config()
        self.crewai_agent = self._create_crewai_agent()

        self.set_actions([WritePRD(self.crewai_agent)])
        self._watch([DelegateToBA])  # React when Team Leader delegates

    async def _act(self) -> Message:
        """Execute current action."""
        if not self.rc.todo:
            return None

        logger.info(f"BA executing: {self.rc.todo.name}")

        recent_messages = self.rc.memory.get(k=3)
        context = recent_messages[-1] if recent_messages else ""

        result = await self.rc.todo.run(context)

        message = Message(
            content=result,
            cause_by=type(self.rc.todo),
            sent_from=self.name
        )

        logger.info(f"BA completed: {self.rc.todo.name}")
        return message

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        config_path = Path(__file__).parent.parent.parent / "crews" / "config" / "agents_config.yaml"

        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)

        return {"business_analyst": {"model": "openai/gpt-4.1"}, "shared": {}}

    def _create_crewai_agent(self) -> CrewAIAgent:
        """Create CrewAI agent."""
        ba_config = self.config.get("business_analyst", {})
        shared_config = self.config.get("shared", {})

        return CrewAIAgent(
            role=ba_config.get("role", "Business Analyst"),
            goal=ba_config.get("goal", "Create specifications"),
            backstory=ba_config.get("backstory", "Experienced BA"),
            tools=[FileReadTool(), DirectoryReadTool()],
            verbose=ba_config.get("verbose", False),
            allow_delegation=False,
            llm=ba_config.get("model", "openai/gpt-4.1"),
            max_iter=shared_config.get("max_iter", 25),
            max_rpm=shared_config.get("max_rpm", 10),
            memory=shared_config.get("memory", True),
        )
