"""Tester Agent - LangGraph Implementation."""

import logging
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel, Project
from app.agents.tester.src import TesterGraph
from app.core.langfuse_client import flush_langfuse
from app.core.db import engine

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
    """Tester agent using LangGraph for test generation."""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        self.graph_engine = TesterGraph(agent=self)
        
        # Workspace management (aligned with Developer V2)
        self.main_workspace = _get_project_workspace(self.project_id)
        
        logger.info(f"[{self.name}] Tester initialized, workspace: {self.main_workspace}")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph."""
        logger.info(f"[{self.name}] Task: type={task.task_type.value}, reason={task.routing_reason}")
        
        # Setup Langfuse tracing (same pattern as Team Leader)
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
            # Determine if auto-triggered
            is_auto = task.context.get("trigger_type") == "status_review"
            
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
                "index_ready": False,
                "merged": False,
            }
            
            # Invoke graph
            final_state = await self.graph_engine.graph.ainvoke(initial_state)
            
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
            logger.error(f"[{self.name}] Error: {e}", exc_info=True)
            # Cleanup langfuse on error
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                    flush_langfuse()
                except Exception:
                    pass
            return TaskResult(success=False, output="", error_message=str(e))
