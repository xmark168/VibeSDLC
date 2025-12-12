"""Tester Agent - LangGraph Implementation.

Updated with pause/resume/cancel support (aligned with Developer V2).
Uses PostgresSaver for persistent checkpoints.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Set

from uuid import UUID

from sqlmodel import Session

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.tester.src.graph import TesterGraph
from app.core.db import engine
from app.core.langfuse_client import flush_langfuse
from app.models import Agent as AgentModel, Project
from app.models.base import StoryAgentState


logger = logging.getLogger(__name__)


# =============================================================================
# Exception for Story Stop (aligned with Developer V2)
# =============================================================================

class StoryStoppedException(Exception):
    """Raised when story processing should stop (paused or cancelled)."""
    def __init__(self, story_id: str, state: StoryAgentState, message: str = ""):
        self.story_id = story_id
        self.state = state
        self.message = message or f"Story {story_id} stopped with state: {state.value}"
        super().__init__(self.message)


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

    NEW ARCHITECTURE (aligned with Developer V2):
    - No more separate Consumer/Role layers
    - Handles tasks via handle_task() method
    - Router sends tasks via @Tester mentions
    - Supports pause/resume/cancel via AgentPoolManager signals
    - Uses PostgresSaver for persistent checkpoints
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        self.graph_engine = TesterGraph(agent=self)
        
        # Workspace management (aligned with Developer V2)
        self.main_workspace = _get_project_workspace(self.project_id)
        
        # Auto-task tracking (for redirecting messages to story channel)
        self._is_auto_task = False
        self._current_story_ids: list[str] = []
        
        # Task control: track running story tasks for cancel/pause (aligned with Developer V2)
        self._running_tasks: Dict[str, asyncio.Task] = {}  # story_id -> Task
        self._paused_stories: Set[str] = set()  # story_ids that are paused (local cache)
        self._cancelled_stories: Set[str] = set()  # story_ids that should be cancelled (local cache)
        
        logger.info(f"[{self.name}] Tester initialized, workspace: {self.main_workspace}")

    # =========================================================================
    # Story State Management (aligned with Developer V2)
    # =========================================================================
    
    def get_story_state_from_db(self, story_id: str) -> Optional[StoryAgentState]:
        """Get current story agent_state from database.
        
        This is the source of truth for pause/cancel detection.
        """
        try:
            from app.models import Story
            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                if story:
                    return story.agent_state
                return None
        except Exception as e:
            logger.error(f"[{self.name}] Failed to get story state from DB: {e}")
            return None
    
    def check_should_stop(self, story_id: str) -> None:
        """Check if story should stop processing. Raises StoryStoppedException if so.
        
        Uses fast in-memory signal check first (O(1)), then DB state.
        Call this periodically during graph execution to detect pause/cancel.
        """
        # Fast path: check in-memory signal from pool manager
        signal = self.check_signal(story_id)
        if signal == "cancel":
            self._cancelled_stories.add(story_id)
            raise StoryStoppedException(story_id, StoryAgentState.CANCEL_REQUESTED, "Cancel requested")
        elif signal == "pause":
            self._paused_stories.add(story_id)
            raise StoryStoppedException(story_id, StoryAgentState.PAUSED, "Story was paused")
        
        # Slow path: check DB state (backup, in case signal was missed)
        state = self.get_story_state_from_db(story_id)
        if state == StoryAgentState.CANCEL_REQUESTED or state == StoryAgentState.CANCELED:
            self._cancelled_stories.add(story_id)
            raise StoryStoppedException(story_id, state, "Story was cancelled")
        elif state == StoryAgentState.PAUSED:
            self._paused_stories.add(story_id)
            raise StoryStoppedException(story_id, state, "Story was paused")
    
    def is_story_paused(self, story_id: str) -> bool:
        """Check if story has been paused (from DB, not just local cache)."""
        if story_id in self._paused_stories:
            return True
        state = self.get_story_state_from_db(story_id)
        if state == StoryAgentState.PAUSED:
            self._paused_stories.add(story_id)
            return True
        return False
    
    def is_story_cancelled(self, story_id: str) -> bool:
        """Check if story has been cancelled (from DB, not just local cache)."""
        if story_id in self._cancelled_stories:
            return True
        state = self.get_story_state_from_db(story_id)
        if state == StoryAgentState.CANCELED:
            self._cancelled_stories.add(story_id)
            return True
        return False

    async def _run_graph_with_signal_check(self, graph, input_data, config, story_id: str):
        """Run graph with signal checking between nodes.
        
        Uses astream() to get control after each node, allowing us to check
        for cancel/pause signals and stop early if needed.
        """
        final_state = None
        node_count = 0
        
        async for event in graph.astream(input_data, config, stream_mode="values"):
            node_count += 1
            final_state = event
            
            # Check for cancel/pause signal after each node completes
            signal = self.check_signal(story_id)
            if signal:
                logger.info(f"[{self.name}] Signal '{signal}' detected after node {node_count}")
                
                if signal == "cancel":
                    self._cancelled_stories.add(story_id)
                    raise StoryStoppedException(
                        story_id, 
                        StoryAgentState.CANCEL_REQUESTED, 
                        f"Cancel signal detected between nodes"
                    )
                elif signal == "pause":
                    self._paused_stories.add(story_id)
                    raise StoryStoppedException(
                        story_id,
                        StoryAgentState.PAUSED,
                        f"Pause signal detected between nodes"
                    )
            
            # Also check DB state as backup
            db_state = self.get_story_state_from_db(story_id)
            if db_state in [StoryAgentState.CANCEL_REQUESTED, StoryAgentState.CANCELED]:
                logger.info(f"[{self.name}] DB state {db_state} detected after node {node_count}")
                self._cancelled_stories.add(story_id)
                raise StoryStoppedException(story_id, db_state, "Story cancelled (from DB state)")
            elif db_state == StoryAgentState.PAUSED:
                logger.info(f"[{self.name}] DB state PAUSED detected after node {node_count}")
                self._paused_stories.add(story_id)
                raise StoryStoppedException(story_id, db_state, "Story paused (from DB state)")
        
        logger.info(f"[{self.name}] Graph completed after {node_count} nodes")
        return final_state

    async def _update_story_state(self, story_id: str, state: StoryAgentState) -> bool:
        """Update story agent_state in database with WebSocket broadcast.

        Returns:
            bool: True if successful, False if failed
        """
        from app.models import Story
        from app.websocket.connection_manager import connection_manager
        
        project_id = None
        old_state = None
        
        try:
            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                if not story:
                    logger.error(f"[{self.name}] Story {story_id} not found")
                    return False

                old_state = story.agent_state
                project_id = story.project_id
                story.agent_state = state
                # CRITICAL: Set assigned_agent_id so cancel signal can find this agent
                story.assigned_agent_id = self.agent_id
                session.commit()

            logger.info(f"[{self.name}] Story {story_id} agent_state: {old_state} → {state} (assigned_agent_id={self.agent_id})")
            
            # Broadcast state change to frontend
            if project_id:
                try:
                    await connection_manager.broadcast_to_project({
                        "type": "story_state_changed",
                        "story_id": story_id,
                        "agent_state": state.value if state else None,
                        "old_state": old_state.value if old_state else None,
                    }, project_id)
                    logger.info(f"[{self.name}] Broadcasted agent_state change: {state.value}")
                except Exception as broadcast_err:
                    logger.warning(f"[{self.name}] Failed to broadcast state change: {broadcast_err}")
            
            return True

        except Exception as e:
            logger.error(f"[{self.name}] Failed to update story state: {e}", exc_info=True)
            return False

    # =========================================================================
    # Task Control: Cancel/Pause/Resume (aligned with Developer V2)
    # =========================================================================
    
    async def cancel_story(self, story_id: str) -> bool:
        """Cancel a running story task.

        Args:
            story_id: Story UUID string

        Returns:
            True if task was cancelled, False if not found
        """
        logger.info(f"[{self.name}] Cancelling story: {story_id}")
        self._cancelled_stories.add(story_id)

        task = self._running_tasks.get(story_id)
        if task and not task.done():
            task.cancel()
            await self._cleanup_story(story_id)
            return True

        return False
    
    async def pause_story(self, story_id: str) -> bool:
        """Pause a running story task at current checkpoint.

        Args:
            story_id: Story UUID string

        Returns:
            True if task was paused, False if not found or invalid state
        """
        logger.info(f"[{self.name}] Pausing story: {story_id}")
        self._paused_stories.add(story_id)

        task = self._running_tasks.get(story_id)
        if task and not task.done():
            task.cancel()  # Will save checkpoint before exit
            return True

        return False
    
    async def resume_story(self, story_id: str) -> bool:
        """Check if story can be resumed from pause.

        The actual resume happens via Kafka event triggering handle_task again.

        Args:
            story_id: Story UUID string

        Returns:
            True if story can be resumed (has checkpoint_thread_id)
        """
        try:
            from app.models import Story

            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                if not story:
                    logger.error(f"Story {story_id} not found")
                    return False

                # Check if has checkpoint (required for resume)
                if not story.checkpoint_thread_id:
                    logger.warning(f"Cannot resume: no checkpoint for {story_id}")
                    return False
                    
                # Clear from paused cache since we're resuming
                self._paused_stories.discard(story_id)
                
                logger.info(f"[{self.name}] Story {story_id} ready to resume from checkpoint: {story.checkpoint_thread_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to validate resume state: {e}")
            return False
    
    async def _cleanup_story(self, story_id: str):
        """Cleanup resources for a cancelled/finished story."""
        try:
            # Remove from tracking
            self._running_tasks.pop(story_id, None)
            self._cancelled_stories.discard(story_id)
            self._paused_stories.discard(story_id)
            # Clear any pending signals to prevent memory leak
            self.clear_signal(story_id)
            
        except Exception as e:
            logger.error(f"[{self.name}] Cleanup error for story {story_id}: {e}")

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
        """Handle task using LangGraph with checkpoint support (aligned with Developer V2)."""
        logger.info(f"[{self.name}] Task: type={task.task_type.value}, reason={task.routing_reason}")
        
        # Get story_id for checkpoint (use first story_id or task_id)
        context = task.context or {}
        story_ids = context.get("story_ids", [])
        story_id = story_ids[0] if story_ids else str(task.task_id)
        is_resume = context.get("resume", False)
        
        # Clear any leftover signals from previous runs (important for restart)
        self.clear_signal(story_id)
        logger.info(f"[{self.name}] Cleared signals for story {story_id}")
        
        langfuse_ctx = None
        langfuse_span = None
        
        try:
            # Determine if auto-triggered and set instance flags for message_user override
            is_auto = context.get("trigger_type") == "status_review"
            self._is_auto_task = is_auto
            self._current_story_ids = story_ids
            
            # Setup graph with PostgresSaver for persistent checkpoints
            logger.info(f"[{self.name}] Setting up graph with PostgresSaver...")
            await self.graph_engine.setup()
            logger.info(f"[{self.name}] Graph setup complete, checkpointer: {type(self.graph_engine.checkpointer).__name__}")
            
            # Track current task for cancel/pause
            current_task = asyncio.current_task()
            if current_task:
                self._running_tasks[story_id] = current_task
            
            # Build initial state (NOTE: langfuse_handler removed - not serializable)
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
                # Workspace context (will be populated by setup_workspace node)
                "main_workspace": self.main_workspace,
                "workspace_path": "",
                "branch_name": "",
                "workspace_ready": False,
                "merged": False,
                "base_branch": "main",
            }
            
            # Thread ID for checkpointing (enables pause/resume)
            from app.models import Story
            
            if is_resume:
                # Load thread_id from database for resume
                try:
                    with Session(engine) as session:
                        story = session.get(Story, UUID(story_id))
                        if not story:
                            raise ValueError(f"Story {story_id} not found")
                        if not story.checkpoint_thread_id:
                            raise ValueError(f"Cannot resume: no checkpoint_thread_id for story {story_id}")
                        thread_id = story.checkpoint_thread_id
                        logger.info(f"[{self.name}] Loaded checkpoint_thread_id from DB: {thread_id}")
                except Exception as e:
                    logger.error(f"[{self.name}] Failed to load checkpoint_thread_id: {e}")
                    raise
            else:
                # Generate and persist thread_id for new task
                thread_id = f"tester_{story_id}"
                try:
                    with Session(engine) as session:
                        story = session.get(Story, UUID(story_id))
                        if story:
                            story.checkpoint_thread_id = thread_id
                            session.commit()
                            logger.info(f"[{self.name}] Saved checkpoint_thread_id: {thread_id}")
                except Exception as e:
                    logger.warning(f"[{self.name}] Failed to save checkpoint_thread_id: {e}")
            
            config = {
                "configurable": {"thread_id": thread_id},
                "recursion_limit": getattr(self.graph_engine, "recursion_limit", 50)
            }
            
            # Set PROCESSING state before starting graph (aligned with Developer V2)
            # This enables pause/cancel buttons in frontend immediately
            if not await self._update_story_state(story_id, StoryAgentState.PROCESSING):
                logger.warning(f"[{self.name}] Failed to set PROCESSING state for {story_id}")
            
            # Check if resuming from pause
            if is_resume:
                logger.info(f"[{self.name}] Resuming story {story_id} from checkpoint")
                final_state = None
                
                try:
                    # Check checkpoint exists
                    checkpoint = await self.graph_engine.checkpointer.aget(config)
                    if checkpoint:
                        from langgraph.types import Command
                        logger.info(f"[{self.name}] Checkpoint found, resuming with Command(resume=True)")
                        try:
                            # Use signal-checking wrapper for resume
                            final_state = await self._run_graph_with_signal_check(
                                self.graph_engine.graph,
                                Command(resume=True),
                                config,
                                story_id
                            )
                        except Exception as resume_err:
                            logger.warning(f"[{self.name}] Resume failed: {resume_err}, falling back to fresh start")
                            final_state = None
                except Exception as e:
                    logger.error(f"[{self.name}] Checkpoint check failed: {e}")
                    final_state = None
                
                # Fallback: start fresh if resume failed
                if final_state is None:
                    logger.warning(f"[{self.name}] Auto-restarting from beginning")
                    is_resume = False
                    # Use signal-checking wrapper for fresh start
                    final_state = await self._run_graph_with_signal_check(
                        self.graph_engine.graph,
                        initial_state,
                        config,
                        story_id
                    )
            else:
                # Start fresh with signal-checking wrapper
                final_state = await self._run_graph_with_signal_check(
                    self.graph_engine.graph,
                    initial_state,
                    config,
                    story_id
                )
            
            # Check for LangGraph interrupt (pause/cancel signal was caught by a node)
            from langgraph.types import Interrupt
            interrupt_info = final_state.get("__interrupt__")
            if interrupt_info:
                interrupt_value = interrupt_info[0].value if interrupt_info else {}
                reason = interrupt_value.get("reason", "unknown") if isinstance(interrupt_value, dict) else "unknown"
                node = interrupt_value.get("node", "unknown") if isinstance(interrupt_value, dict) else "unknown"
                
                logger.info(f"[{self.name}] Graph interrupted: reason={reason}, node={node}")
                
                # Remove from local tracking
                self._running_tasks.pop(story_id, None)
                
                # Notify user
                if story_ids:
                    try:
                        if reason == "pause":
                            await self.message_story(
                                UUID(story_ids[0]),
                                f"⏸️ Tests đã tạm dừng tại node '{node}'. Checkpoint đã được lưu.",
                                message_type="system"
                            )
                        elif reason == "cancel":
                            await self.message_story(
                                UUID(story_ids[0]),
                                f"🛑 Tests đã bị hủy tại node '{node}'.",
                                message_type="system"
                            )
                    except Exception:
                        pass
                
                # Cleanup
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
            
            # Return result
            error = final_state.get("error")
            if error:
                # Remove from tracking
                self._running_tasks.pop(story_id, None)
                return TaskResult(success=False, output="", error_message=error)
            
            # Remove from tracking on success
            self._running_tasks.pop(story_id, None)
            
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
            
        except asyncio.CancelledError:
            # Task was cancelled (user clicked Cancel or Pause)
            logger.info(f"[{self.name}] Story {story_id} was cancelled/paused (CancelledError)")
            
            # Remove from local tracking
            self._running_tasks.pop(story_id, None)
            
            # Cleanup langfuse if needed
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
            # Story was stopped via signal or DB state check
            logger.info(f"[{self.name}] Story {story_id} stopped: {e.message}")
            
            # Remove from local tracking
            self._running_tasks.pop(story_id, None)
            
            # Clear the signal after handling
            self.consume_signal(story_id)
            
            # Handle based on state
            if story_ids:
                try:
                    story_uuid = UUID(story_ids[0])
                    
                    if e.state == StoryAgentState.PAUSED:
                        # Paused - checkpoint auto-saved by LangGraph, just notify
                        await self.message_story(
                            story_uuid,
                            f"⏸️ Tests đã tạm dừng. Checkpoint đã được lưu.",
                            message_type="system"
                        )
                    elif e.state in [StoryAgentState.CANCEL_REQUESTED, StoryAgentState.CANCELED]:
                        # Cancel requested/canceled - transition to CANCELED and notify
                        if e.state == StoryAgentState.CANCEL_REQUESTED:
                            # Agent acknowledges cancel by transitioning to CANCELED
                            await self._update_story_state(story_id, StoryAgentState.CANCELED)
                        await self.message_story(
                            story_uuid,
                            f"🛑 Tests đã bị hủy.",
                            message_type="system"
                        )
                except Exception:
                    pass
            
            # Cleanup langfuse
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
            # Reset flags on error
            self._is_auto_task = False
            self._current_story_ids = []
            self._running_tasks.pop(story_id, None)
            
            logger.error(f"[{self.name}] Error: {e}", exc_info=True)
            
            # Cleanup langfuse on error
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                    flush_langfuse()
                except Exception:
                    pass
            return TaskResult(success=False, output="", error_message=str(e))
