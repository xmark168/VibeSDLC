"""Tester Agent - LangGraph Implementation."""

import logging
from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel
from app.agents.tester.src import TesterGraph

logger = logging.getLogger(__name__)


class Tester(BaseAgent):
    """Tester agent using LangGraph for test generation."""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        self.graph_engine = TesterGraph(agent=self)
        logger.info(f"[{self.name}] Tester initialized")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph."""
        logger.info(f"[{self.name}] Task: type={task.task_type.value}, reason={task.routing_reason}")
        
        # Setup Langfuse
        langfuse_handler, langfuse_ctx = None, None
        try:
            from langfuse import get_client
            from langfuse.langchain import CallbackHandler
            langfuse_ctx = get_client().start_as_current_observation(as_type="span", name="tester_graph")
            span = langfuse_ctx.__enter__()
            span.update_trace(
                user_id=str(task.user_id) if task.user_id else None,
                session_id=str(self.project_id),
                input={"message": task.content[:200] if task.content else ""},
                tags=["tester", self.role_type],
                metadata={"agent": self.name, "task_id": str(task.task_id)}
            )
            langfuse_handler = CallbackHandler()
        except Exception as e:
            logger.debug(f"Langfuse: {e}")
        
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
            }
            
            # Invoke graph
            final_state = await self.graph_engine.graph.ainvoke(initial_state)
            
            # Close Langfuse
            if langfuse_ctx:
                try:
                    span.update_trace(output=final_state.get("result", {}))
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            # Return result
            error = final_state.get("error")
            if error:
                return TaskResult(success=False, error_message=error)
            
            return TaskResult(
                success=True,
                output=final_state.get("message", ""),
                structured_data=final_state.get("result", {})
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}", exc_info=True)
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                except Exception:
                    pass
            return TaskResult(success=False, error_message=str(e))
