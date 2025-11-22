"""Developer Crew - Code implementation and development tasks.

This crew handles actual software development work.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from crewai import Agent, Task

from app.agents.roles.base_crew import BaseAgentCrew

logger = logging.getLogger(__name__)


class DeveloperCrew(BaseAgentCrew):
    """Developer Crew - handles software development implementation tasks.

    This crew:
    1. Implements features and fixes based on specifications
    2. Writes and modifies code
    3. Follows coding standards and best practices
    """

    @property
    def crew_name(self) -> str:
        return "Developer"

    @property
    def agent_type(self) -> str:
        return "developer"

    def _get_default_config_path(self) -> Path:
        """Get default config path for Developer."""
        return Path(__file__).parent / "config.yaml"

    def create_agent(self) -> Agent:
        """Create the Developer agent.

        Returns:
            Configured CrewAI Agent for software development
        """
        agent_config = self.config.get("agent", {})

        self.agent = Agent(
            role=agent_config.get("role", "Software Developer"),
            goal=agent_config.get(
                "goal",
                "Implement software features and fixes according to specifications"
            ),
            backstory=agent_config.get(
                "backstory",
                "You are an experienced software developer who writes clean, maintainable code."
            ),
            verbose=agent_config.get("verbose", True),
            allow_delegation=agent_config.get("allow_delegation", False),
        )

        return self.agent

    def create_tasks(self, context: Dict[str, Any]) -> list[Task]:
        """Create development tasks based on context.

        Args:
            context: Execution context containing:
                - user_message: User request/specification
                - task_description: Description of development task
                - requirements: List of requirements/specifications

        Returns:
            List of CrewAI Task instances for development
        """
        user_message = context.get("user_message", "")
        task_description = context.get("task_description", user_message)

        task = Task(
            description=f"""
            Implement the following development task:

            {task_description}

            Follow these guidelines:
            1. Write clean, readable, and maintainable code
            2. Follow established coding standards and patterns
            3. Include appropriate error handling
            4. Add comments for complex logic
            5. Ensure code is properly tested

            Return your implementation with:
            - File paths and code changes
            - Explanation of your implementation
            - Any notes or considerations
            """,
            expected_output="Implementation details with code changes and explanations",
            agent=self.agent,
        )

        return [task]
