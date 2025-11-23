"""Developer Agent - Merged Role + Crew Implementation.

NEW ARCHITECTURE:
- Inherits from BaseAgent (Kafka abstracted)
- Handles code implementation tasks
- Integrates CrewAI crew logic directly
"""

import logging
from pathlib import Path
from typing import Any, Dict
from uuid import UUID

import yaml
from crewai import Agent, Crew, Task

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel


logger = logging.getLogger(__name__)


class Developer(BaseAgent):
    """Developer agent - implements code and handles development tasks.

    NEW ARCHITECTURE:
    - No more separate Consumer/Role layers
    - Handles tasks via handle_task() method
    - Router sends tasks via @Developer mentions
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize Developer.

        Args:
            agent_model: Agent database model
            **kwargs: Additional arguments (heartbeat_interval, max_idle_time)
        """
        super().__init__(agent_model, **kwargs)

        # Load configuration
        self.config = self._load_config()

        # Create CrewAI agent
        self.crew_agent = self._create_crew_agent()

        logger.info(f"Developer initialized: {self.name}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        config_path = Path(__file__).parent / "config.yaml"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

        # Default configuration
        return {
            "agent": {
                "role": "Software Developer",
                "goal": "Implement software features and fixes according to specifications",
                "backstory": "You are an experienced software developer who writes clean, maintainable code.",
                "verbose": True,
                "allow_delegation": False,
                "model": "openai/gpt-4",
            }
        }

    def _create_crew_agent(self) -> Agent:
        """Create CrewAI agent for Developer.

        Returns:
            Configured CrewAI Agent
        """
        agent_config = self.config.get("agent", {})

        agent = Agent(
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
            llm=agent_config.get("model", "openai/gpt-4"),
        )

        return agent

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router.

        Args:
            task: TaskContext with user message and metadata

        Returns:
            TaskResult with implementation response
        """
        try:
            user_message = task.content

            logger.info(f"[{self.name}] Processing development task: {user_message[:50]}...")

            # Update progress
            await self.update_progress(1, 4, "Analyzing requirements")

            # Create CrewAI task for implementation
            crew_task = Task(
                description=f"""
                Implement the following development task:

                {user_message}

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
                agent=self.crew_agent,
            )

            # Execute crew
            await self.update_progress(2, 4, "Implementing solution")

            crew = Crew(
                agents=[self.crew_agent],
                tasks=[crew_task],
                verbose=True,
            )

            result = crew.kickoff()

            # Extract response
            response = str(result)

            await self.update_progress(3, 4, "Reviewing implementation")

            # Update progress to complete
            await self.update_progress(4, 4, "Complete")

            logger.info(f"[{self.name}] Implementation completed: {len(response)} chars")

            return TaskResult(
                success=True,
                output=response,
                structured_data={
                    "task_type": task.task_type.value,
                    "routing_reason": task.routing_reason,
                    "implementation_type": "code_development",
                },
                requires_approval=False,
            )

        except Exception as e:
            logger.error(f"[{self.name}] Error handling task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e),
            )
