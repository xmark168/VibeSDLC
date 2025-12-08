"""Tester Agent - LangGraph Implementation."""

import logging
from typing import Any, Dict
from uuid import UUID

from sqlmodel import Session

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.tester.src.graph import TesterGraph
from app.core.db import engine
from app.core.langfuse_client import flush_langfuse
from app.models import Agent as AgentModel, Project


logger = logging.getLogger(__name__)


def _get_project_workspace(project_id) -> str:
    """Get project workspace path from database."""
    try:
        with Session(engine) as session:
            project = session.get(Project, UUID(str(project_id)))
            if project and project.project_path:
                return str(project.project_path)
    except Exception as e:
        logger.warning(f"[_get_project_workspace] Error: {e}")
    return ""


class Tester(BaseAgent):
    """Tester agent - creates test plans and ensures software quality.

    NEW ARCHITECTURE:
    - No more separate Consumer/Role layers
    - Handles tasks via handle_task() method
    - Router sends tasks via @Tester mentions
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        self.graph_engine = TesterGraph(agent=self)
        
        # Workspace management (aligned with Developer V2)
        self.main_workspace = _get_project_workspace(self.project_id)
        
        # Auto-task tracking (for redirecting messages to story channel)
        self._is_auto_task = False
        self._current_story_ids: list[str] = []
        
        logger.info(f"[{self.name}] Tester initialized, workspace: {self.main_workspace}")

    async def message_user(self, event_type: str, content: str, details=None, **kwargs):
        """Override to redirect messages to story channel when auto-triggered."""
        # Check if auto task from routing reason (set by base_agent before handle_task)
        is_auto_from_reason = getattr(self, '_current_routing_reason', '') == "story_status_changed_to_review"
        is_auto = self._is_auto_task or is_auto_from_reason
        
        # Skip system events (thinking, idle) for auto tasks - they're noise in main chat
        if is_auto and event_type in ("thinking", "idle"):
            logger.debug(f"[{self.name}] Suppressing '{event_type}' event for auto task")
            return None
        
        # For auto tasks, redirect regular messages to story channel
        if is_auto and self._current_story_ids and event_type == "response":
            for story_id in self._current_story_ids:
                try:
                    await self.message_story(
                        UUID(story_id), 
                        content, 
                        message_type=details.get("message_type", "update") if details else "update"
                    )
                except Exception as e:
                    logger.warning(f"[{self.name}] Failed to message story {story_id}: {e}")
            return None
        
        # Default behavior for user-initiated tasks
        return await super().message_user(event_type, content, details, **kwargs)

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph."""
        logger.info(f"[{self.name}] Task: type={task.task_type.value}, reason={task.routing_reason}")
        
        # Setup Langfuse tracing
        langfuse_handler = None
        langfuse_span = None
        langfuse_ctx = None
        try:
            from langfuse import get_client
            from langfuse.langchain import CallbackHandler
            
            langfuse = get_client()
            # Create parent span for entire graph execution
            langfuse_ctx = langfuse.start_as_current_observation(
                as_type="span",
                name="tester_graph"
            )
            # Enter context and get span object
            langfuse_span = langfuse_ctx.__enter__()
            # Update trace with metadata
            langfuse_span.update_trace(
                user_id=str(task.user_id) if task.user_id else None,
                session_id=str(self.project_id),
                input={"message": task.content[:200] if task.content else ""},
                tags=["tester", self.role_type],
                metadata={"agent": self.name, "task_id": str(task.task_id)}
            )
            # Handler inherits trace context automatically
            langfuse_handler = CallbackHandler()
        except Exception as e:
            logger.debug(f"[{self.name}] Langfuse setup: {e}")
        
        try:
            # Determine if auto-triggered and set instance flags for message_user override
            is_auto = task.context.get("trigger_type") == "status_review"
            self._is_auto_task = is_auto
            self._current_story_ids = task.context.get("story_ids", [])
            
            # Build initial state
            initial_state = {
                "project_id": str(self.project_id),
                "user_id": str(task.user_id) if task.user_id else None,
                "task_id": str(task.task_id),
                "task_type": task.task_type.value,  # For _should_message_user check
                "story_ids": task.context.get("story_ids", []),
                "user_message": task.content or "",
                "is_auto": is_auto,
                "langfuse_handler": langfuse_handler,
                # Workspace context (will be populated by setup_workspace node)
                "main_workspace": self.main_workspace,
                "workspace_path": "",
                "branch_name": "",
                "workspace_ready": False,
                "merged": False,
            }
            
            # Invoke graph with increased recursion limit
            recursion_limit = getattr(self.graph_engine, "recursion_limit", 50)
            final_state = await self.graph_engine.graph.ainvoke(
                initial_state,
                config={"recursion_limit": recursion_limit}
            )
            
            # Update trace output and close span
            if langfuse_span and langfuse_ctx:
                try:
                    langfuse_span.update_trace(output=final_state.get("result", {}))
                    langfuse_ctx.__exit__(None, None, None)
                    flush_langfuse()
                except Exception:
                    pass
            
            # Return result
            error = final_state.get("error")
            if error:
                return TaskResult(success=False, output="", error_message=error)
            
            # Reset flags
            self._is_auto_task = False
            self._current_story_ids = []
            
            return TaskResult(
                success=True,
                output=final_state.get("message", ""),
                structured_data={
                    "action": final_state.get("action"),
                    "run_status": final_state.get("run_status"),
                    "files_created": final_state.get("files_created", []),
                    "files_modified": final_state.get("files_modified", []),
                    "branch_name": final_state.get("branch_name"),
                    "workspace_path": final_state.get("workspace_path"),
                    "merged": final_state.get("merged", False),
                }
            )
            
        except Exception as e:
            # Reset flags on error
            self._is_auto_task = False
            self._current_story_ids = []
            logger.error(f"[{self.name}] Error: {e}", exc_info=True)
            # Cleanup langfuse on error
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                    flush_langfuse()
                except Exception:
                    pass
            return TaskResult(success=False, output="", error_message=str(e))
