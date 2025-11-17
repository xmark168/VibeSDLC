"""
Team Leader Agent Implementation

Central orchestrator that analyzes user messages, provides insights,
and delegates tasks to specialist agents.
"""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import Any, Dict

from crewai import Agent as CrewAIAgent, Task, Crew
from crewai_tools import FileReadTool, DirectoryReadTool

from app.agents.base import Role, Action, Message
from app.core.config import settings

logger = logging.getLogger(__name__)


# Define Action Types that Team Leader can cause
class UserRequest(Action):
    """Marker for user-initiated requests."""
    async def run(self, context):
        return context


class AnalyzeMessage(Action):
    """Analyze user message to determine routing."""

    def __init__(self, crewai_agent: CrewAIAgent):
        super().__init__()
        self.crewai_agent = crewai_agent

    async def run(self, context: Any) -> str:
        """Analyze message using CrewAI."""
        if isinstance(context, Message):
            content = context.content
        else:
            content = str(context)

        task = Task(
            description=f"""
            Analyze this user message: "{content}"

            Determine:
            1. Is this asking for insights/analytics or delegating work?
            2. If delegation, which agent: BA, Developer, or Tester?
            3. Provide brief analysis

            Format:
            TYPE: [insights|delegation]
            AGENT: [ba|dev|tester|none]
            ANALYSIS: [brief explanation]
            """,
            expected_output="Structured analysis",
            agent=self.crewai_agent,
        )

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        crew = Crew(agents=[self.crewai_agent], tasks=[task], verbose=False)
        result = await loop.run_in_executor(None, crew.kickoff)

        return str(result)


class DelegateToBA(Action):
    """Delegate task to Business Analyst."""
    async def run(self, context):
        return f"Delegating to BA: {context}"


class DelegateToDev(Action):
    """Delegate task to Developer."""
    async def run(self, context):
        return f"Delegating to Developer: {context}"


class DelegateToTester(Action):
    """Delegate task to Tester."""
    async def run(self, context):
        return f"Delegating to Tester: {context}"


class TeamLeaderAgent(Role):
    """
    Team Leader Agent - Central orchestrator.

    Watches for user requests, analyzes them, and delegates to specialists.
    """

    def __init__(self):
        super().__init__(
            name="TeamLeader",
            profile="Technical Team Leader & Analytics Specialist"
        )

        # Load configuration
        self.config = self._load_config()
        self.crewai_agent = self._create_crewai_agent()

        # Set up actions
        self.set_actions([
            AnalyzeMessage(self.crewai_agent),
            DelegateToBA(),
            DelegateToDev(),
            DelegateToTester(),
        ])

        # Watch for user requests
        self._watch([UserRequest])

    async def _act(self) -> Message:
        """Execute current action and return result."""
        if not self.rc.todo:
            return None

        logger.info(f"TeamLeader executing: {self.rc.todo.name}")

        # Get context from memory
        recent_messages = self.rc.memory.get(k=5)
        context = recent_messages[-1] if recent_messages else ""

        # Execute action
        result = await self.rc.todo.run(context)

        # Create response message
        message = Message(
            content=result,
            cause_by=type(self.rc.todo),
            sent_from=self.name
        )

        logger.info(f"TeamLeader completed: {self.rc.todo.name}")
        return message

    def _load_config(self) -> Dict[str, Any]:
        """Load agent configuration from YAML."""
        config_path = Path(__file__).parent.parent.parent / "crews" / "config" / "agents_config.yaml"

        if not config_path.exists():
            logger.warning(f"Config not found at {config_path}, using defaults")
            return self._get_default_config()

        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "team_leader": {
                "role": "Technical Team Leader",
                "goal": "Orchestrate development workflow",
                "backstory": "Experienced leader with AI expertise",
                "verbose": True,
                "allow_delegation": True,
                "model": "openai/gpt-4.1",
            },
            "shared": {
                "max_iter": 25,
                "max_rpm": 10,
                "memory": True,
            }
        }

    def _create_crewai_agent(self) -> CrewAIAgent:
        """Create CrewAI agent for LLM-powered analysis."""
        tl_config = self.config.get("team_leader", {})
        shared_config = self.config.get("shared", {})

        tools = [
            FileReadTool(),
            DirectoryReadTool(),
        ]

        return CrewAIAgent(
            role=tl_config.get("role", "Team Leader"),
            goal=tl_config.get("goal", "Orchestrate workflow"),
            backstory=tl_config.get("backstory", "Experienced leader"),
            tools=tools,
            verbose=tl_config.get("verbose", False),
            allow_delegation=tl_config.get("allow_delegation", True),
            llm=tl_config.get("model", "openai/gpt-4.1"),
            max_iter=shared_config.get("max_iter", 25),
            max_rpm=shared_config.get("max_rpm", 10),
            memory=shared_config.get("memory", True),
        )
