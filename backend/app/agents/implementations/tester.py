"""
Tester Agent Implementation

Ensures software quality through comprehensive testing.
"""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Any, Dict

from crewai import Agent as CrewAIAgent, Task, Crew
from crewai_tools import FileReadTool, DirectoryReadTool

from app.agents.base import Role, Action, Message
from app.agents.implementations.team_leader import DelegateToTester
from app.agents.implementations.developer import WriteCode

logger = logging.getLogger(__name__)


class WriteTests(Action):
    """Write comprehensive tests."""

    def __init__(self, crewai_agent: CrewAIAgent):
        super().__init__()
        self.crewai_agent = crewai_agent

    async def run(self, context: Any) -> str:
        """Generate tests using CrewAI."""
        if isinstance(context, Message):
            content = context.content
        else:
            content = str(context)

        task = Task(
            description=f"Create comprehensive test plan and test cases for: {content}",
            expected_output="Test plan with unit, integration, and e2e tests",
            agent=self.crewai_agent,
        )

        loop = asyncio.get_event_loop()
        crew = Crew(agents=[self.crewai_agent], tasks=[task], verbose=False)
        result = await loop.run_in_executor(None, crew.kickoff)

        return str(result)


class TesterAgent(Role):
    """
    Tester Agent.

    Watches for code completion or direct delegation, creates tests.
    """

    def __init__(self):
        super().__init__(
            name="Tester",
            profile="QA Testing Specialist"
        )

        self.config = self._load_config()
        self.crewai_agent = self._create_crewai_agent()

        self.set_actions([WriteTests(self.crewai_agent)])
        self._watch([WriteCode, DelegateToTester])  # React to code or direct delegation

    async def _act(self) -> Message:
        """Execute current action."""
        if not self.rc.todo:
            return None

        logger.info(f"Tester executing: {self.rc.todo.name}")

        recent_messages = self.rc.memory.get(k=3)
        context = recent_messages[-1] if recent_messages else ""

        result = await self.rc.todo.run(context)

        message = Message(
            content=result,
            cause_by=type(self.rc.todo),
            sent_from=self.name
        )

        logger.info(f"Tester completed: {self.rc.todo.name}")
        return message

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration."""
        config_path = Path(__file__).parent.parent.parent / "crews" / "config" / "agents_config.yaml"

        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)

        return {"tester": {"model": "openai/gpt-4.1"}, "shared": {}}

    def _create_crewai_agent(self) -> CrewAIAgent:
        """Create CrewAI agent."""
        tester_config = self.config.get("tester", {})
        shared_config = self.config.get("shared", {})

        return CrewAIAgent(
            role=tester_config.get("role", "Tester"),
            goal=tester_config.get("goal", "Ensure quality"),
            backstory=tester_config.get("backstory", "Experienced tester"),
            tools=[FileReadTool(), DirectoryReadTool()],
            verbose=tester_config.get("verbose", False),
            allow_delegation=False,
            llm=tester_config.get("model", "openai/gpt-4.1"),
            max_iter=shared_config.get("max_iter", 25),
            max_rpm=shared_config.get("max_rpm", 10),
            memory=shared_config.get("memory", True),
        )
