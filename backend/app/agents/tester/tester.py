"""Tester Agent"""

import asyncio
import logging
from typing import Any, Dict, Optional, Set

from uuid import UUID

from sqlmodel import Session

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.core.mixins import PausableAgentMixin, StoryStoppedException
from app.agents.core.graph_helpers import get_or_create_thread_id
from app.agents.tester.src.graph import TesterGraph
from app.core.db import engine
from app.core.langfuse_client import flush_langfuse
from app.models import Agent as AgentModel, Project
from app.models.base import StoryAgentState


logger = logging.getLogger(__name__)


class Tester(BaseAgent, PausableAgentMixin):
    """Tester agent with LangGraph workflow. Supports pause/resume/cancel via PostgresSaver."""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        self.graph_engine = TesterGraph(agent=self)
        
        self._is_auto_task = False
        self._current_story_ids: list[str] = []
        # Initialize PausableAgentMixin (provides pause/resume/cancel functionality)
        self.init_pausable_mixin()
        logger.info(f"[{self.name}] Tester initialized")

    async def message_user(self, event_type: str, content: str, details=None, **kwargs):
        """Override to redirect messages to story channel when auto-triggered."""
        is_auto_from_reason = getattr(self, '_current_routing_reason', '') == "story_status_changed_to_review"
        is_auto = self._is_auto_task or is_auto_from_reason
        
        if is_auto and event_type in ("thinking", "idle"):
            logger.debug(f"[{self.name}] Suppressing '{event_type}' event for auto task")
            return None
        
        if is_auto and self._current_story_ids and event_type == "response":
            # Log response for auto tasks (no longer saving to story messages)
            logger.info(f"[{self.name}] Auto task response: {content[:100]}...")
            return None
        
        return await super().message_user(event_type, content, details, **kwargs)

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph with checkpoint support."""
        logger.info(f"[{self.name}] Task: type={task.task_type.value}, reason={task.routing_reason}")
        
        context = task.context or {}
        story_ids = context.get("story_ids", [])
        story_id = story_ids[0] if story_ids else str(task.task_id)
        is_resume = context.get("resume", False)
        
        self.clear_signal(story_id)
        logger.info(f"[{self.name}] Cleared signals for story {story_id}")
        
        langfuse_ctx = None
        langfuse_span = None
        langfuse_handler = None
        
        try:
            is_auto = context.get("trigger_type") == "status_review"
            
            # Setup Langfuse tracing
            from app.core.config import settings
            if settings.LANGFUSE_ENABLED:
                try:
                    from langfuse import get_client
                    langfuse = get_client()
                    
                    langfuse_ctx = langfuse.start_as_current_observation(
                        as_type="span",
                        name="tester_execution"
                    )
                    langfuse_span = langfuse_ctx.__enter__()
                    
                    # Create LangChain CallbackHandler for detailed tracing
                    from langfuse.langchain import CallbackHandler
                    langfuse_handler = CallbackHandler()
                    
                    langfuse_span.update_trace(
                        user_id=str(task.user_id) if task.user_id else None,
                        session_id=story_id,
                        input={"story_id": story_id, "is_auto": is_auto},
                        tags=["tester", task.task_type.value],
                        metadata={
                            "agent": self.name,
                            "story_id": story_id,
                            "is_auto": is_auto,
                            "workspace_path": context.get("worktree_path", "")
                        }
                    )
                    logger.info(f"[{self.name}] ✓ Langfuse span started - trace={langfuse_span.trace_id}")
                    
                except Exception as e:
                    logger.error(f"[{self.name}] Langfuse setup failed: {e}", exc_info=True)
                    langfuse_handler = None
                    langfuse_ctx = None
                    langfuse_span = None
            else:
                logger.debug(f"[{self.name}] Langfuse disabled")
            self._is_auto_task = is_auto
            self._current_story_ids = story_ids
            
            logger.info(f"[{self.name}] Setting up graph with PostgresSaver...")
            await self.graph_engine.setup()
            logger.info(f"[{self.name}] Graph setup complete, checkpointer: {type(self.graph_engine.checkpointer).__name__}")
            
            current_task = asyncio.current_task()
            if current_task:
                self._running_tasks[story_id] = current_task
            
            # NOTE: langfuse_handler is passed via config["callbacks"], NOT in state
            # This avoids serialization issues with PostgresSaver checkpoint (msgpack)
            initial_state = {
                "project_id": str(self.project_id),
                "user_id": str(task.user_id) if task.user_id else None,
                "task_id": str(task.task_id),
                "story_id": story_id,
                "task_type": task.task_type.value,
                "story_ids": story_ids,
                "user_message": task.content or "",
                "is_auto": is_auto,
                "is_resume": is_resume,
                # Get workspace_path from task context (set by router from Story.worktree_path)
                "workspace_path": context.get("worktree_path", ""),
                "branch_name": context.get("branch_name", ""),
                "tech_stack": self.tech_stack,  # Pass from agent
                "workspace_ready": False,
                "merged": False,
                "base_branch": "main",
            }
            
            # Thread ID for checkpointing (enables pause/resume)
            # Use helper to get or create thread_id
            thread_id = get_or_create_thread_id(story_id, self.agent_id, is_resume)
            
            # NOTE: langfuse_handler is passed via config["callbacks"], NOT in state
            # This avoids serialization issues with PostgresSaver checkpoint (msgpack)
            config = {
                "configurable": {"thread_id": thread_id},
                "recursion_limit": getattr(self.graph_engine, "recursion_limit", 50),
                "callbacks": [langfuse_handler] if langfuse_handler else [],
            }
            
            if not await self._update_story_state(story_id, StoryAgentState.PROCESSING):
                logger.warning(f"[{self.name}] Failed to set PROCESSING state for {story_id}")
            
            if is_resume:
                logger.info(f"[{self.name}] Resuming story {story_id} from checkpoint")
                
                # FIX #2: Try to load checkpoint with fallback to memory cache
                checkpoint = await self._load_checkpoint_with_fallback(story_id, config)
                
                if checkpoint:
                    # Use Command(resume=True) for LangGraph
                    from langgraph.types import Command
                    logger.info(f"[{self.name}] Checkpoint found, resuming with Command(resume=True)")
                    try:
                        final_state = await self._run_graph_with_signal_check(
                            self.graph_engine.graph,
                            Command(resume=True),
                            config,
                            story_id
                        )
                    except Exception as resume_err:
                        # Resume failed - restart from beginning
                        logger.warning(f"[{self.name}] Resume failed: {resume_err}, restarting from beginning")
                        is_resume = False
                        final_state = await self._run_graph_with_signal_check(
                            self.graph_engine.graph,
                            initial_state,
                            config,
                            story_id
                        )
                else:
                    # No checkpoint available - restart from beginning
                    logger.warning(f"[{self.name}] No checkpoint found, restarting from beginning")
                    is_resume = False
                    final_state = await self._run_graph_with_signal_check(
                        self.graph_engine.graph,
                        initial_state,
                        config,
                        story_id
                    )
            else:
                final_state = await self._run_graph_with_signal_check(
                    self.graph_engine.graph,
                    initial_state,
                    config,
                    story_id
                )
            
            from langgraph.types import Interrupt
            interrupt_info = final_state.get("__interrupt__")
            if interrupt_info:
                interrupt_value = interrupt_info[0].value if interrupt_info else {}
                reason = interrupt_value.get("reason", "unknown") if isinstance(interrupt_value, dict) else "unknown"
                node = interrupt_value.get("node", "unknown") if isinstance(interrupt_value, dict) else "unknown"
                
                logger.info(f"[{self.name}] Graph interrupted: reason={reason}, node={node}")
                
                self._running_tasks.pop(story_id, None)
                if story_ids:
                    if reason == "pause":
                        logger.info(f"[{self.name}] Tests paused at node '{node}'. Checkpoint saved.")
                    elif reason == "cancel":
                        logger.info(f"[{self.name}] Tests cancelled at node '{node}'.")
                
                if langfuse_ctx:
                    try:
                        langfuse_ctx.__exit__(None, None, None)
                    except Exception:
                        pass
                
                return TaskResult(
                    success=False,
                    output="",
                    error_message=f"Tests {reason}ed at node {node}"
                )
            
            error = final_state.get("error")
            if error:
                self._running_tasks.pop(story_id, None)
                return TaskResult(success=False, output="", error_message=error)
            
            self._running_tasks.pop(story_id, None)
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
            
        except asyncio.CancelledError:
            logger.info(f"[{self.name}] Story {story_id} was cancelled/paused (CancelledError)")
            self._running_tasks.pop(story_id, None)
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            return TaskResult(
                success=False,
                output="",
                error_message="Tests were cancelled or paused"
            )
        
        except StoryStoppedException as e:
            logger.info(f"[{self.name}] Story {story_id} stopped: {e.message}")
            self._running_tasks.pop(story_id, None)
            self.consume_signal(story_id)
            if story_ids:
                if e.state == StoryAgentState.PAUSED:
                    logger.info(f"[{self.name}] Tests paused. Checkpoint saved.")
                elif e.state in [StoryAgentState.CANCEL_REQUESTED, StoryAgentState.CANCELED]:
                    if e.state == StoryAgentState.CANCEL_REQUESTED:
                        await self._update_story_state(story_id, StoryAgentState.CANCELED)
                    logger.info(f"[{self.name}] Tests cancelled.")
            
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            return TaskResult(
                success=False,
                output="",
                error_message=e.message
            )
            
        except Exception as e:
            self._is_auto_task = False
            self._current_story_ids = []
            self._running_tasks.pop(story_id, None)
            logger.error(f"[{self.name}] Error: {e}", exc_info=True)
            
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                    flush_langfuse()
                except Exception:
                    pass
            return TaskResult(success=False, output="", error_message=str(e))
