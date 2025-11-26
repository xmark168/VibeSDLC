"""Developer Agent - Merged Role + Crew Implementation.

NEW ARCHITECTURE:
- Inherits from BaseAgent (Kafka abstracted)
- Handles code implementation tasks
- Integrates CrewAI crew logic directly
"""

import asyncio
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
            content = task.content.lower()
            project_id = getattr(task, 'project_id', 'default')
            project_dir = getattr(task, 'project_dir', f'../{project_id}')

            logger.info(
                f"[{self.name}] Processing task: {task.content[:50]}..."
            )

            # Analyze task content to determine the type of request
            if "moved to in progress" in content or "chuyển sang in progress" in content or "status changed to in progress" in content:
                return await self._handle_task_started(task, project_id, project_dir)
            elif "implement" in content or "develop" in content or "code" in content:
                return await self._handle_development_request(task, project_id, project_dir)
            else:
                # Default to development implementation
                return await self._handle_development_request(task, project_id, project_dir)

        except Exception as e:
            logger.error(f"[{self.name}] Error handling task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e),
            )

    async def _handle_task_started(self, task: TaskContext, project_id: str, project_dir: str) -> TaskResult:
        """Handle when a task is moved to In Progress status."""
        await self.message_user("thinking", "Task moved to In Progress, preparing development environment...")

        # Initialize a new crew instance with project-specific context
        project_crew = DeveloperCrew(project_id=project_id, root_dir=project_dir)

        # For task status change, we might want to prepare the development environment
        # This could involve creating a branch, setting up worktree, etc.
        response = await project_crew.implement_task(user_story=task.content, task_id=str(task.task_id))

        await self.message_user("thinking", "Development environment prepared")

        await self.message_user(
            "progress", "Task started successfully", {"milestone": "development_started"}
        )

        logger.info(
            f"[{self.name}] Task started for project {project_id}: {len(response)} chars"
        )

        return TaskResult(
            success=True,
            output=response,
            structured_data={
                "task_type": task.task_type.value,
                "routing_reason": task.routing_reason,
                "implementation_type": "task_started",
                "project_id": project_id,
            },
            requires_approval=False,
        )

    async def _handle_development_request(self, task: TaskContext, project_id: str, project_dir: str) -> TaskResult:
        """Handle regular development requests."""
        await self.message_user("thinking", "Analyzing development requirements")

        # Initialize a new crew instance with project-specific context
        project_crew = DeveloperCrew(project_id=project_id, root_dir=project_dir)

        response = await project_crew.implement_task(user_story=task.content, task_id=str(task.task_id))

        await self.message_user("thinking", "Reviewing implementation")

        await self.message_user(
            "progress", "Development task complete", {"milestone": "completed"}
        )

        logger.info(
            f"[{self.name}] Implementation completed for project {project_id}: {len(response)} chars"
        )

        return TaskResult(
            success=True,
            output=response,
            structured_data={
                "task_type": task.task_type.value,
                "routing_reason": task.routing_reason,
                "implementation_type": "code_development",
                "project_id": project_id,
            },
            requires_approval=False,
        )
