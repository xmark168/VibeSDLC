"""Developer Agent - Merged Role + Crew Implementation.

NEW ARCHITECTURE:
- Inherits from BaseAgent (Kafka abstracted)
- Handles code implementation tasks
- Integrates CrewAI crew logic directly
"""

import logging

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.developer.crew import DeveloperCrew
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

        # Create CrewAI agent
        self.crew = DeveloperCrew(project_id="demo", root_dir="../demo")

        logger.info(f"Developer initialized: {self.name}")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router.

        Args:
            task: TaskContext with user message and metadata

        Returns:
            TaskResult with implementation response
        """
        try:
            user_story = task.content

            logger.info(
                f"[{self.name}] Processing development task: {user_story[:50]}..."
            )

            # Status update
            await self.message_user("thinking", "Analyzing User Story")

            # Create CrewAI task for implementation
            response = await self.crew.implement_task(user_story=user_story)

            await self.message_user("thinking", "Reviewing implementation")

            # Final milestone
            await self.message_user(
                "progress", "Development task complete", {"milestone": "completed"}
            )

            logger.info(
                f"[{self.name}] Implementation completed: {len(response)} chars"
            )

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
