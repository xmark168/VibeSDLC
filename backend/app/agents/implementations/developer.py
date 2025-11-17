"""
Developer Agent Implementation

Implements features and writes production-ready code.
"""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Any, Dict

from crewai import Agent as CrewAIAgent, Task, Crew
from crewai_tools import FileReadTool, DirectoryReadTool

from app.agents.base import Role, Action, Message
from app.agents.implementations.team_leader import DelegateToDev
from app.agents.implementations.business_analyst import WritePRD

logger = logging.getLogger(__name__)


class WriteCode(Action):
    """Write production code."""

    def __init__(self, crewai_agent: CrewAIAgent):
        super().__init__()
        self.crewai_agent = crewai_agent

    async def run(self, context: Any) -> str:
        """Generate code using CrewAI."""
        if isinstance(context, Message):
            content = context.content
        else:
            content = str(context)

        task = Task(
            description=f"Implement production-ready code for: {content}",
            expected_output="Clean, tested, documented code",
            agent=self.crewai_agent,
        )

        loop = asyncio.get_event_loop()
        crew = Crew(agents=[self.crewai_agent], tasks=[task], verbose=False)
        result = await loop.run_in_executor(None, crew.kickoff)

        return str(result)


class DeveloperAgent(Role):
    """
    Developer Agent.

    Watches for PRD completion or direct delegation, writes code.
    """

    def __init__(self):
        super().__init__(
            name="Developer",
            profile="Senior Full-Stack Developer"
        )

        self.config = self._load_config()
        self.crewai_agent = self._create_crewai_agent()

        self.set_actions([WriteCode(self.crewai_agent)])
        self._watch([WritePRD, DelegateToDev])  # React to PRD or direct delegation

    async def _act(self) -> Message:
        """Execute current action."""
        if not self.rc.todo:
            return None

        logger.info(f"Developer executing: {self.rc.todo.name}")

        recent_messages = self.rc.memory.get(k=3)
        context = recent_messages[-1] if recent_messages else ""

        result = await self.rc.todo.run(context)

        message = Message(
            content=result,
            cause_by=type(self.rc.todo),
            sent_from=self.name
        )

        logger.info(f"Developer completed: {self.rc.todo.name}")
        return message

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        config_path = Path(__file__).parent.parent.parent / "crews" / "config" / "agents_config.yaml"

        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)

        return {"developer": {"model": "openai/gpt-4.1"}, "shared": {}}

    def _create_crewai_agent(self) -> CrewAIAgent:
        """Create CrewAI agent."""
        dev_config = self.config.get("developer", {})
        shared_config = self.config.get("shared", {})

        return CrewAIAgent(
            role=dev_config.get("role", "Developer"),
            goal=dev_config.get("goal", "Implement features"),
            backstory=dev_config.get("backstory", "Experienced developer"),
            tools=[FileReadTool(), DirectoryReadTool()],
            verbose=dev_config.get("verbose", False),
            allow_delegation=False,
            llm=dev_config.get("model", "openai/gpt-4.1"),
            max_iter=shared_config.get("max_iter", 25),
            max_rpm=shared_config.get("max_rpm", 10),
            memory=shared_config.get("memory", True),
        )
