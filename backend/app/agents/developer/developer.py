"""Developer Agent - Merged Role + Crew Implementation.

NEW ARCHITECTURE:
- Inherits from BaseAgent (Kafka abstracted)
- Handles code implementation tasks
- Integrates CrewAI crew logic directly
- Manages project workspaces automatically
"""

import logging

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.developer.crew import DeveloperCrew
from app.agents.developer.workspace_manager import ProjectWorkspaceManager
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
        # Initialize workspace manager BEFORE calling super
        self.workspace_manager = ProjectWorkspaceManager(agent_model.project_id)

        # Get main workspace (creates if doesn't exist)
        self.main_workspace = self.workspace_manager.get_main_workspace()

        # Now call super() - this will set self.project_id
        super().__init__(agent_model, **kwargs)

        # Initialize crew with correct workspace path
        self.crew = DeveloperCrew(
            project_id=str(self.project_id),
            root_dir=str(self.main_workspace),
        )

        logger.info(
            f"Developer initialized: {self.name} (workspace: {self.main_workspace.name})"
        )

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router based on task type.

        Args:
            task: TaskContext with user message and metadata

        Returns:
            TaskResult with implementation response
        """
        try:
            # Use workspace from workspace manager
            project_id = str(self.project_id)
            project_dir = str(self.main_workspace)

            # Override if task has specific project_dir (for compatibility)
            if hasattr(task, "project_dir") and task.project_dir:
                project_dir = task.project_dir

            logger.info(
                f"[{self.name}] Processing {task.task_type.value} task: {task.content[:50]}..."
            )
            logger.info(f"  Project ID: {project_id}")
            logger.info(f"  Workspace: {project_dir}")

            # Route based on task_type (similar to TeamLeader approach)
            task_type = task.task_type.value

            if task_type == "story_status_changed":
                # Handle when story moves to InProgress (from story event)
                return await self._handle_task_started(task, project_id, project_dir)
            elif task_type in ["implement_story", "write_code", "create_feature"]:
                # Handle development implementation requests
                return await self._handle_development_request(
                    task, project_id, project_dir
                )
            elif task_type == "progress_query":
                # Handle progress/status queries
                return await self._handle_status_query(task, project_id)
            elif task_type == "help_request":
                # Handle help requests
                return await self._handle_help_request(task)
            else:
                # Default to development implementation for unknown task types
                return await self._handle_general_request(task, project_id, project_dir)

        except Exception as e:
            logger.error(f"[{self.name}] Error handling task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e),
            )

    async def _handle_task_started(
        self, task: TaskContext, project_id: str, project_dir: str
    ) -> TaskResult:
        """Handle when a task is moved to In Progress status."""
        await self.message_user(
            "thinking",
            "Task moved to In Progress, preparing development environment...",
        )

        # Get story_id from context (sent by Router), fallback to task_id
        story_id = task.context.get("story_id") or str(task.task_id)
        
        # Calculate branch and worktree info using story_id (matches frontend logic)
        short_story_id = story_id.split('-')[-1] if '-' in story_id else story_id[:8]
        branch_name = f"story_{short_story_id}"
        worktree_name = f"ws_story_{short_story_id}"

        # Initialize a new crew instance with project-specific context
        project_crew = DeveloperCrew(project_id=project_id, root_dir=project_dir)

        # For task status change, we might want to prepare the development environment
        # This could involve creating a branch, setting up worktree, etc.
        response = await project_crew.implement_task(user_story=task.content, task_id=story_id)

        await self.message_user("thinking", "Development environment prepared")

        # Notify completion with branch/worktree info
        await self.message_user(
            "progress", 
            f" Development complete!\n\n"
            f" **Worktree:** `{worktree_name}`\n"
            f" **Branch:** `{branch_name}`\n\n"
            f"Please move story to Review on the Kanban board.", 
            {"milestone": "completed", "branch": branch_name, "worktree": worktree_name}
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

    async def _handle_development_request(
        self, task: TaskContext, project_id: str, project_dir: str
    ) -> TaskResult:
        """Handle regular development requests."""
        await self.message_user("thinking", "Analyzing development requirements")

        # Get story_id from context (sent by Router), fallback to task_id
        story_id = task.context.get("story_id") or str(task.task_id)
        
        # Calculate branch and worktree info using story_id (matches frontend logic)
        short_story_id = story_id.split('-')[-1] if '-' in story_id else story_id[:8]
        branch_name = f"story_{short_story_id}"
        worktree_name = f"ws_story_{short_story_id}"

        # Initialize a new crew instance with project-specific context
        project_crew = DeveloperCrew(project_id=project_id, root_dir=project_dir)

        response = await project_crew.implement_task(user_story=task.content, task_id=story_id)

        await self.message_user("thinking", "Reviewing implementation")

        # Notify completion with branch/worktree info
        await self.message_user(
            "progress", 
            f" Implementation complete!\n\n"
            f" **Worktree:** `{worktree_name}`\n"
            f" **Branch:** `{branch_name}`\n\n"
            f"Please move story to Review on the Kanban board.", 
            {"milestone": "completed", "branch": branch_name, "worktree": worktree_name}
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

    async def _handle_help_request(self, task: TaskContext) -> TaskResult:
        """Handle help request from user."""
        help_message = (
            "Tôi là Developer agent, chuyên phụ trách việc phát triển code và triển khai tính năng.\n\n"
            "Tôi có thể giúp bạn với các công việc sau:\n"
            "- Triển khai các tính năng mới theo yêu cầu\n"
            "- Viết code dựa trên User Story hoặc PRD (Product Requirements Document)\n"
            "- Cập nhật trạng thái phát triển khi task chuyển sang In Progress\n"
            "- Review và cải thiện code có sẵn\n"
            "- Tạo các module, component theo yêu cầu\n\n"
            "Ví dụ:\n"
            "- '@Developer hãy triển khai chức năng login'\n"
            "- '@Developer tạo API endpoint cho user management'\n"
            "- Khi bạn kéo một task sang In Progress, tôi sẽ tự động bắt đầu phát triển"
        )

        await self.message_user(
            "response",
            help_message,
            {
                "message_type": "text",
            },
        )

        return TaskResult(
            success=True,
            output=help_message,
            structured_data={
                "task_type": task.task_type.value,
                "routing_reason": task.routing_reason,
                "implementation_type": "help_response",
            },
            requires_approval=False,
        )

    async def _handle_status_query(
        self, task: TaskContext, project_id: str
    ) -> TaskResult:
        """Handle status query from user."""
        # Use the DeveloperCrew to provide a meaningful progress report
        project_crew = DeveloperCrew(project_id=project_id, root_dir=f"../{project_id}")

        try:
            response = await project_crew.report_progress(
                query=task.content,
                project_id=project_id,
                task_id=getattr(task, "task_id", None),
            )
        except Exception as e:
            logger.warning(
                f"Failed to report progress via crew: {e}, falling back to generic response"
            )
            response = (
                f"Hiện tại tôi không có thông tin cụ thể về trạng thái phát triển trong project {project_id}.\n"
                "Tuy nhiên, tôi có thể:\n"
                "- Báo cáo tiến độ phát triển cho các task cụ thể\n"
                "- Xác nhận việc bắt đầu phát triển khi task chuyển sang In Progress\n"
                "- Cập nhật khi hoàn thành công việc được giao\n\n"
                "Vui lòng mô tả rõ hơn task bạn muốn hỏi để tôi hỗ trợ tốt hơn."
            )

        await self.message_user(
            "response",
            response,
            {
                "message_type": "text",
            },
        )

        return TaskResult(
            success=True,
            output=response,
            structured_data={
                "task_type": task.task_type.value,
                "routing_reason": task.routing_reason,
                "implementation_type": "status_query_response",
                "project_id": project_id,
            },
            requires_approval=False,
        )

    async def _handle_general_request(
        self, task: TaskContext, project_id: str, project_dir: str
    ) -> TaskResult:
        """Handle general request from user - analyze and decide on appropriate action."""
        content = task.content

        # If it looks like a development request, process it as such
        await self.message_user("thinking", "Analyzing your request...")

        # Initialize a new crew instance with project-specific context
        project_crew = DeveloperCrew(project_id=project_id, root_dir=project_dir)

        try:
            response = await project_crew.implement_task(
                user_story=content, task_id=str(task.task_id)
            )
        except Exception as e:
            logger.warning(
                f"Failed to process with crew: {e}, falling back to general response"
            )
            response = (
                f"Tôi đã nhận được yêu cầu của bạn: '{content}'\n\n"
                "Là Developer agent, tôi chuyên xử lý các công việc liên quan đến phát triển code.\n"
                "Nếu bạn muốn tôi triển khai một tính năng cụ thể, vui lòng mô tả chi tiết yêu cầu.\n\n"
                "Bạn có thể hỏi tôi làm gì bằng '@Developer help' hoặc "
                "tag tôi vào task khi cần triển khai code."
            )
            await self.message_user(
                "response",
                response,
                {
                    "message_type": "text",
                },
            )

        return TaskResult(
            success=True,
            output=response,
            structured_data={
                "task_type": task.task_type.value,
                "routing_reason": task.routing_reason,
                "implementation_type": "general_processing",
                "project_id": project_id,
            },
            requires_approval=False,
        )
