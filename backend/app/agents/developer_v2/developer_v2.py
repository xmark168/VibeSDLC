"""
Developer V2 Agent - LangGraph-based Story Processor.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.core.project_context import ProjectContext
from app.agents.core.task_registry import (
    request_pause,
    request_cancel,
    check_interrupt_signal,
    clear_signals,
)
from app.models import Agent as AgentModel
from app.models.base import StoryAgentState
from app.agents.developer_v2.src import DeveloperGraph
from app.agents.developer_v2.src.utils.workspace_manager import ProjectWorkspaceManager
from app.kafka.event_schemas import AgentTaskType

logger = logging.getLogger(__name__)


# =============================================================================
# Pause/Cancel Signal Management - Delegated to TaskRegistry
# =============================================================================
# These functions are re-exported from task_registry for backward compatibility
# The actual implementation is in app.agents.core.task_registry
#
# - request_pause(story_id) - Request pause for a story
# - request_cancel(story_id) - Request cancel for a story  
# - check_interrupt_signal(story_id) - Check for 'pause', 'cancel', or None
# - clear_signals(story_id) - Clear all signals for a story


class StoryStoppedException(Exception):
    """Raised when story processing should stop (paused or cancelled)."""
    def __init__(self, story_id: str, state: StoryAgentState, message: str = ""):
        self.story_id = story_id
        self.state = state
        self.message = message or f"Story {story_id} stopped with state: {state.value}"
        super().__init__(self.message)


class DeveloperV2(BaseAgent):

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        
        self.context = ProjectContext.get(self.project_id)
        self.graph_engine = DeveloperGraph(agent=self)
        
        # Workspace management
        self.workspace_manager = ProjectWorkspaceManager(self.project_id)
        self.main_workspace = self.workspace_manager.get_main_workspace()
        
        # Task control: track running story tasks for cancel/pause
        self._running_tasks: Dict[str, asyncio.Task] = {}  # story_id -> Task
        self._paused_stories: Set[str] = set()  # story_ids that are paused (local cache)
        self._cancelled_stories: Set[str] = set()  # story_ids that should be cancelled (local cache)

    # =========================================================================
    # Story State Check from DB (for pause/cancel detection)
    # =========================================================================
    
    def get_story_state_from_db(self, story_id: str) -> Optional[StoryAgentState]:
        """Get current story agent_state from database.
        
        This is the source of truth for pause/cancel detection.
        """
        try:
            from uuid import UUID
            from sqlmodel import Session
            from app.core.db import engine
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
        
        Call this periodically during graph execution to detect pause/cancel.
        """
        state = self.get_story_state_from_db(story_id)
        if state == StoryAgentState.CANCELED:
            self._cancelled_stories.add(story_id)  # Update local cache
            raise StoryStoppedException(story_id, state, "Story was cancelled")
        elif state == StoryAgentState.PAUSED:
            self._paused_stories.add(story_id)  # Update local cache
            raise StoryStoppedException(story_id, state, "Story was paused")
    
    def is_story_paused(self, story_id: str) -> bool:
        """Check if story has been paused (from DB, not just local cache)."""
        # Check local cache first for performance
        if story_id in self._paused_stories:
            return True
        # Check DB as source of truth
        state = self.get_story_state_from_db(story_id)
        if state == StoryAgentState.PAUSED:
            self._paused_stories.add(story_id)
            return True
        return False

    async def _update_story_state(self, story_id: str, state: StoryAgentState) -> bool:
        """Update story agent_state in database with WebSocket broadcast.

        Returns:
            bool: True if successful, False if failed
        """
        from uuid import UUID
        from sqlmodel import Session
        from app.core.db import engine
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
                session.commit()

            logger.info(f"[{self.name}] Story {story_id} agent_state: {old_state} → {state}")
            
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
            if project_id:
                try:
                    await connection_manager.broadcast_to_project({
                        "type": "story_state_error",
                        "story_id": story_id,
                        "error": f"Failed to update state: {str(e)}",
                        "message_type": "error",
                    }, project_id)
                except Exception:
                    pass
            return False

    # =========================================================================
    # Task Control: Cancel/Pause/Resume
    # =========================================================================
    
    async def cancel_story(self, story_id: str) -> bool:
        """Cancel a running story task.

        Args:
            story_id: Story UUID string

        Returns:
            True if task was cancelled, False if not found
            
        Note: State is already updated by API endpoint before this is called.
        This method focuses on stopping the running task.
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
            
        Note: State is already updated by API endpoint before this is called.
        This method focuses on stopping the running task gracefully.
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

        The actual resume happens via Kafka event triggering _process_story again.

        Args:
            story_id: Story UUID string

        Returns:
            True if story can be resumed (has checkpoint_thread_id)
            
        Note: This validates resume conditions from DB, not in-memory state.
        """
        try:
            from uuid import UUID
            from sqlmodel import Session
            from app.core.db import engine
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
            # Stop dev server if running
            from uuid import UUID
            from sqlmodel import Session
            from app.core.db import engine
            from app.models import Story
            import os
            import signal
            
            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                if story and story.running_pid:
                    try:
                        os.kill(story.running_pid, signal.SIGTERM)
                    except (ProcessLookupError, OSError):
                        pass
                    story.running_pid = None
                    story.running_port = None
                    session.commit()
            
            # Remove from tracking
            self._running_tasks.pop(story_id, None)
            self._cancelled_stories.discard(story_id)
            self._paused_stories.discard(story_id)
            
        except Exception as e:
            logger.error(f"[{self.name}] Cleanup error for story {story_id}: {e}")
    
    def is_story_cancelled(self, story_id: str) -> bool:
        """Check if story has been cancelled (from DB, not just local cache)."""
        # Check local cache first for performance
        if story_id in self._cancelled_stories:
            return True
        # Check DB as source of truth
        state = self.get_story_state_from_db(story_id)
        if state == StoryAgentState.CANCELED:
            self._cancelled_stories.add(story_id)
            return True
        return False

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task - route to story processing or user message handling."""
        
        await self.context.ensure_loaded()
        
        # Route based on task type
        if task.task_type == AgentTaskType.IMPLEMENT_STORY:
            return await self._handle_story_processing(task)
        else:
            return await self._handle_user_message(task)

    async def _handle_user_message(self, task: TaskContext) -> TaskResult:
        """Handle direct @Developer messages."""
        content = task.content.lower()
        
        if "help" in content or "giúp" in content:
            return await self._respond_help()
        elif "status" in content or "tiến độ" in content or "progress" in content:
            return await self._respond_status()
        else:
            return await self._handle_dev_request(task)

    async def _respond_help(self) -> TaskResult:
        """Respond with help information."""
        msg = """Tôi là Developer, chuyên phụ trách phát triển code! 💻

**Tôi có thể giúp bạn:**
- Triển khai tính năng mới
- Viết code theo User Story/PRD
- Review và cải thiện code
- Tạo module, component

**Cách sử dụng:**
- Kéo story sang In Progress → Tôi tự động bắt đầu
- Hoặc nhắn: "@Developer triển khai chức năng login"
"""
        await self.message_user("response", msg)
        return TaskResult(success=True, output=msg)

    async def _respond_status(self) -> TaskResult:
        """Respond with current status."""
        msg = "📊 Hiện tại chưa có task nào đang xử lý. Bạn có thể kéo story sang In Progress để tôi bắt đầu!"
        await self.message_user("response", msg)
        return TaskResult(success=True, output=msg)

    async def _handle_dev_request(self, task: TaskContext) -> TaskResult:
        """Handle development request from user message."""
        story_data = {
            "story_id": str(task.task_id),
            "title": task.content[:50] if len(task.content) > 50 else task.content,
            "content": task.content,
            "acceptance_criteria": [],
        }
        return await self._process_story(story_data, task)

    async def _handle_story_processing(self, task: TaskContext) -> TaskResult:
        """Handle story processing using LangGraph."""
        story_id = None
        is_resume = False
        try:
            # Check if story data comes from router context (story status change)
            context = task.context or {}
            story_id_from_context = context.get("story_id")
            event_type = context.get("event_type", "")
            is_resume = context.get("resume", False)  # Check for resume flag
            
            if story_id_from_context and (event_type == "story.status.changed" or is_resume):
                story_id = story_id_from_context
                
                if is_resume:
                    # Resuming paused story - state update only, no message (node will handle)
                    if not await self._update_story_state(story_id, StoryAgentState.PROCESSING):
                        raise RuntimeError(f"Cannot resume: failed to update state for {story_id}")
                else:
                    # Starting new story - state update only
                    if not await self._update_story_state(story_id, StoryAgentState.PENDING):
                        raise RuntimeError(f"Cannot start: failed to update state for {story_id}")
                
                story_data = await self._load_story_from_db(story_id)
                
                if not is_resume:
                    # Send milestone message for new story start
                    from uuid import UUID
                    await self.message_story(
                        UUID(story_id),
                        f"🚀 Bắt đầu: {story_data.get('title', 'Story')}",
                        message_type="text"
                    )
            else:
                # Parse from task content (legacy/direct call)
                story_data = self._parse_story_content(task)
                story_id = story_data.get("story_id")
            
            return await self._process_story(story_data, task, is_resume=is_resume)
        except Exception as e:
            logger.error(f"[{self.name}] Story processing error: {e}", exc_info=True)
            # Set CANCELED on error
            if story_id:
                if not await self._update_story_state(story_id, StoryAgentState.CANCELED):
                    logger.error(f"Failed to set CANCELED state after error for {story_id}")
            return TaskResult(
                success=False,
                output="",
                error_message=f"Story processing error: {str(e)}"
            )

    async def _load_story_from_db(self, story_id: str) -> dict:
        """Load story details from database.
        
        Args:
            story_id: UUID string of the story
            
        Returns:
            dict with story_id, title, content, acceptance_criteria
        """
        from uuid import UUID
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Story
        
        story_uuid = UUID(story_id) if isinstance(story_id, str) else story_id
        
        with Session(engine) as session:
            story = session.get(Story, story_uuid)
            if not story:
                raise ValueError(f"Story {story_id} not found")
            

            
            return {
                "story_id": str(story.id),
                "story_code": story.story_code or f"STORY-{str(story.id)[:8]}",
                "title": story.title or "Untitled Story",
                "content": story.description or "",
                "acceptance_criteria": story.acceptance_criteria or [],
            }

    async def _process_story(self, story_data: dict, task: TaskContext, is_resume: bool = False) -> TaskResult:
        """Process story through LangGraph workflow.
        
        Note: Workspace setup is now handled by the setup_workspace node in the graph.
        It only creates a branch when code modification is actually needed.
        
        Args:
            story_data: Story details from database
            task: Task context
            is_resume: If True, resume from checkpoint instead of starting fresh
        """
        langfuse_handler = None
        langfuse_ctx = None
        langfuse_span = None
        
        try:
            story_id = story_data.get("story_id", str(task.task_id))
            
            # Clear any leftover signals from previous runs (important for restart)
            clear_signals(story_id)
            logger.info(f"[{self.name}] Cleared signals for story {story_id}")
            
            # Check if Langfuse is enabled before initializing
            from app.core.config import settings
            if settings.LANGFUSE_ENABLED:
                try:
                    from langfuse import get_client
                    from langfuse.langchain import CallbackHandler
                    langfuse = get_client()
                    langfuse_ctx = langfuse.start_as_current_observation(
                        as_type="span",
                        name="developer_v2_graph"
                    )
                    langfuse_span = langfuse_ctx.__enter__()
                    langfuse_span.update_trace(
                        user_id=str(task.user_id) if task.user_id else None,
                        session_id=str(self.project_id),
                        input={
                            "story_id": story_data.get("story_id", "unknown"),
                            "title": story_data.get("title", "")[:200],
                            "content": story_data.get("content", "")[:300]
                        },
                        tags=["developer_v2", self.role_type],
                        metadata={"agent": self.name, "task_id": str(task.task_id)}
                    )
                    langfuse_handler = CallbackHandler()
                except Exception as e:
                    logger.debug(f"Langfuse setup: {e}")
            
            # Initial state - workspace will be set up by setup_workspace node if needed
            # NOTE: Do NOT store non-serializable objects (langfuse_handler, skill_registry) 
            # in state - they will cause checkpoint serialization errors
            story_code = story_data.get("story_code", f"STORY-{story_id[:8]}")
            initial_state = {
                "story_id": story_id,
                "story_code": story_code,
                "story_title": story_data.get("title", "Untitled Story"),
                "story_content": story_data.get("content", task.content),
                "acceptance_criteria": story_data.get("acceptance_criteria", []),
                "project_id": str(self.project_id),
                "task_id": str(task.task_id),
                "user_id": str(task.user_id) if task.user_id else "",
                # langfuse_handler removed - not serializable, causes checkpoint errors
                
                # Workspace context - will be populated by setup_workspace node
                "workspace_path": "",
                "branch_name": "",
                "main_workspace": str(self.main_workspace),
                "workspace_ready": False,
                "index_ready": False,
                "merged": False,
                
                # Workflow state
                "action": None,
                "task_type": None,
                "complexity": None,
                "analysis_result": None,
                "implementation_plan": [],
                "files_created": [],
                "files_modified": [],
                "affected_files": [],
                "current_step": 0,
                "total_steps": 0,
                "validation_result": None,
                "message": None,
                "confidence": None,
                "reason": None,
                
                # Design document
                "design_doc": None,
                
                # Run/test state
                "run_status": None,
                "run_result": None,
                "run_stdout": "",
                "run_stderr": "",
                "test_command": None,
                "error_logs": "",
                
                # Debug state
                "debug_count": 0,
                "max_debug": 5,
                "debug_history": [],
                "last_debug_file": None,
                "error_analysis": None,
                
                # React mode (MetaGPT Engineer2 pattern)
                "react_mode": True,
                "react_loop_count": 0,
                "max_react_loop": 40,
                
                # Project context
                "project_context": None,
                "agents_md": None,
                "related_code_context": "",
                "research_context": "",
                
                # Tech stack for skills
                "tech_stack": "nextjs",
            }
            
            # Set PROCESSING state before starting graph
            if not await self._update_story_state(story_id, StoryAgentState.PROCESSING):
                raise RuntimeError(f"Failed to set PROCESSING state for {story_id}")
            
            # Setup graph with PostgresSaver for persistent checkpoints
            logger.info(f"[{self.name}] Setting up graph with PostgresSaver...")
            await self.graph_engine.setup()
            logger.info(f"[{self.name}] Graph setup complete, checkpointer: {type(self.graph_engine.checkpointer).__name__}")
            
            # Track current task for cancel/pause
            current_task = asyncio.current_task()
            if current_task:
                self._running_tasks[story_id] = current_task
            
            # Thread ID for checkpointing (enables pause/resume)
            # Load from DB on resume, generate and save on fresh start
            from uuid import UUID
            from sqlmodel import Session
            from app.core.db import engine
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
                # Generate and persist thread_id for new story (unique per agent)
                thread_id = f"{self.agent_id}_{story_id}"
                try:
                    with Session(engine) as session:
                        story = session.get(Story, UUID(story_id))
                        if story:
                            story.checkpoint_thread_id = thread_id
                            session.commit()
                            logger.info(f"[{self.name}] Saved checkpoint_thread_id: {thread_id}")
                except Exception as e:
                    logger.error(f"[{self.name}] Failed to save checkpoint_thread_id: {e}")

            config = {"configurable": {"thread_id": thread_id}}

            # Check if resuming from pause
            if is_resume:
                logger.info(f"[{self.name}] Resuming story {story_id} from checkpoint")
                final_state = None
                
                # Try to resume from checkpoint, with fallback to fresh start
                try:
                    # Check checkpoint exists
                    checkpoint = await self.graph_engine.checkpointer.aget(config)
                    if checkpoint:
                        # Checkpoint exists, attempt resume
                        from langgraph.types import Command
                        logger.info(f"[{self.name}] Checkpoint found, resuming with Command(resume=True)")
                        try:
                            final_state = await self.graph_engine.graph.ainvoke(Command(resume=True), config)
                        except Exception as resume_err:
                            # Resume failed (checkpoint may have been deleted after check)
                            logger.warning(f"[{self.name}] Resume failed: {resume_err}, falling back to fresh start")
                            final_state = None  # Will trigger fallback below
                except Exception as e:
                    logger.error(f"[{self.name}] Checkpoint check failed: {e}")
                    final_state = None  # Will trigger fallback below
                
                # Fallback: start fresh if resume failed
                if final_state is None:
                    logger.warning(f"[{self.name}] Auto-restarting from beginning")
                    from uuid import UUID
                    await self.message_story(
                        UUID(story_id),
                        f"⚠️ Không thể tiếp tục từ checkpoint, tự động khởi động lại từ đầu...",
                        message_type="warning"
                    )
                    is_resume = False
                    final_state = await self.graph_engine.graph.ainvoke(initial_state, config)
            else:
                # Start fresh
                final_state = await self.graph_engine.graph.ainvoke(initial_state, config)
            
            # Check for LangGraph interrupt (pause/cancel signal was caught by a node)
            from langgraph.types import Interrupt
            interrupt_info = final_state.get("__interrupt__")
            if interrupt_info:
                # Extract interrupt reason from the interrupt value
                interrupt_value = interrupt_info[0].value if interrupt_info else {}
                reason = interrupt_value.get("reason", "unknown") if isinstance(interrupt_value, dict) else "unknown"
                node = interrupt_value.get("node", "unknown") if isinstance(interrupt_value, dict) else "unknown"
                
                logger.info(f"[{self.name}] Graph interrupted: reason={reason}, node={node}")
                
                # Remove from local tracking
                self._running_tasks.pop(story_id, None)
                
                # Git operations based on reason
                workspace_path = final_state.get("workspace_path", "")
                if workspace_path:
                    from app.agents.developer_v2.src.nodes.implement import git_revert_uncommitted, git_reset_all
                    if reason == "pause":
                        # Revert uncommitted changes (keep commits)
                        git_revert_uncommitted(workspace_path)
                        logger.info(f"[{self.name}] Reverted uncommitted changes on pause")
                    elif reason == "cancel":
                        # Reset all changes to base branch
                        base_branch = final_state.get("base_branch", "main")
                        git_reset_all(workspace_path, base_branch)
                        logger.info(f"[{self.name}] Reset all changes on cancel")
                
                # Notify user (milestone messages for pause/cancel)
                from uuid import UUID
                story_uuid = UUID(story_id)
                if reason == "pause":
                    await self.message_story(
                        story_uuid,
                        f"⏸️ Đã tạm dừng. Bấm Resume để tiếp tục.",
                        message_type="text"
                    )
                elif reason == "cancel":
                    await self.message_story(
                        story_uuid,
                        f"🛑 Đã hủy story.",
                        message_type="text"
                    )
                
                # Cleanup langfuse
                if langfuse_ctx:
                    try:
                        langfuse_ctx.__exit__(None, None, None)
                    except Exception:
                        pass
                
                return TaskResult(
                    success=False,
                    output="",
                    error_message=f"Story {reason}ed at node {node}"
                )
            
            # Update trace output and close span (Team Leader pattern)
            if langfuse_span and langfuse_ctx:
                try:
                    langfuse_span.update_trace(output={
                        "action": final_state.get("action"),
                        "task_type": final_state.get("task_type"),
                        "complexity": final_state.get("complexity"),
                        "files_created": final_state.get("files_created", []),
                        "files_modified": final_state.get("files_modified", []),
                        "branch_name": final_state.get("branch_name"),
                    })
                    langfuse_ctx.__exit__(None, None, None)
                except Exception as e:
                    logger.debug(f"[{self.name}] Langfuse span close error: {e}")
            

            
            action = final_state.get("action")
            task_type = final_state.get("task_type")
            message = final_state.get("message", "")
            files_created = final_state.get("files_created", [])
            files_modified = final_state.get("files_modified", [])
            
            # Remove from local tracking
            self._running_tasks.pop(story_id, None)
            
            # Update story state based on result
            run_status = final_state.get("run_status", "")
            if run_status == "PASS":
                # Squash WIP commits into single commit on success
                workspace_path = final_state.get("workspace_path", "")
                if workspace_path:
                    from app.agents.developer_v2.src.nodes.implement import git_squash_wip_commits
                    story_title = initial_state.get("title", "implement story")
                    base_branch = final_state.get("base_branch", "main")
                    git_squash_wip_commits(workspace_path, base_branch, f"feat: {story_title}")
                    logger.info(f"[{self.name}] Squashed WIP commits")
                
                if not await self._update_story_state(story_id, StoryAgentState.FINISHED):
                    logger.error(f"Failed to set FINISHED state for {story_id}")
            else:
                if not await self._update_story_state(story_id, StoryAgentState.CANCELED):
                    logger.error(f"Failed to set CANCELED state for {story_id}")
            
            # Notify user of completion
            from uuid import UUID
            try:
                story_uuid = UUID(story_id)
                total_files = len(files_created) + len(files_modified)
                if run_status == "PASS":
                    await self.message_story(
                        story_uuid,
                        f"✅ Story hoàn thành! Đã tạo/sửa {total_files} files.",
                        message_type="text",
                        details={"files_created": files_created, "files_modified": files_modified, "branch_name": final_state.get('branch_name')}
                    )
                else:
                    await self.message_story(
                        story_uuid,
                        f"❌ Story chưa hoàn thành. Build failed.",
                        message_type="text",
                        details={"files_created": files_created, "files_modified": files_modified, "error": final_state.get("run_stderr", "")[:200]}
                    )
            except Exception:
                pass
            
            return TaskResult(
                success=True,
                output=message,
                structured_data={
                    "action": action,
                    "task_type": task_type,
                    "complexity": final_state.get("complexity"),
                    "analysis": final_state.get("analysis_result"),
                    "plan_steps": len(final_state.get("implementation_plan", [])),
                    "files_created": files_created,
                    "files_modified": files_modified,
                    "validation": final_state.get("validation_result"),
                    "tests_passed": final_state.get("tests_passed"),
                    "branch_name": final_state.get("branch_name"),
                    "workspace_path": final_state.get("workspace_path"),
                }
            )
            
        except asyncio.CancelledError:
            # Task was cancelled (user clicked Cancel or Pause)
            logger.info(f"[{self.name}] Story {story_id} was cancelled/paused (CancelledError)")
            
            # Remove from local tracking
            self._running_tasks.pop(story_id, None)
            
            # State already updated by API endpoint
            # Just cleanup langfuse if needed
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            return TaskResult(
                success=False,
                output="",
                error_message="Story was cancelled or paused"
            )
        
        except StoryStoppedException as e:
            # Story was stopped via DB state check (pause or cancel detected)
            logger.info(f"[{self.name}] Story {story_id} stopped: {e.message}")
            
            # Remove from local tracking
            self._running_tasks.pop(story_id, None)
            
            # Notify user (milestone messages)
            try:
                from uuid import UUID
                story_uuid = UUID(story_id)
                if e.state == StoryAgentState.PAUSED:
                    await self.message_story(
                        story_uuid,
                        f"⏸️ Đã tạm dừng. Bấm Resume để tiếp tục.",
                        message_type="text"
                    )
                elif e.state == StoryAgentState.CANCELED:
                    await self.message_story(
                        story_uuid,
                        f"🛑 Đã hủy story.",
                        message_type="text"
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
            logger.error(f"[{self.name}] Graph execution error: {e}", exc_info=True)
            
            # Remove from local tracking
            self._running_tasks.pop(story_id, None)

            # Set CANCELED on error
            if not await self._update_story_state(story_id, StoryAgentState.CANCELED):
                logger.error(f"Failed to set CANCELED state after graph error for {story_id}")
            
            # Notify user of error
            from uuid import UUID
            try:
                story_uuid = UUID(story_id)
                await self.message_story(
                    story_uuid,
                    f"❌ Lỗi: {str(e)[:200]}",
                    message_type="error"
                )
            except Exception:
                pass
            
            # Cleanup langfuse span on error
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                except Exception:
                    pass
            
            return TaskResult(
                success=False,
                output="",
                error_message=f"Story processing error: {str(e)}"
            )

    def _parse_story_content(self, task: TaskContext) -> dict:
        """Parse story content from task.
        
        Supports:
        1. JSON format with story_id, title, content, acceptance_criteria
        2. Plain text format
        """
        import json
        
        content = task.content
        
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return {
                    "story_id": data.get("story_id", data.get("id", "")),
                    "title": data.get("title", data.get("name", "Untitled")),
                    "content": data.get("content", data.get("description", "")),
                    "acceptance_criteria": data.get("acceptance_criteria", data.get("ac", [])),
                }
        except (json.JSONDecodeError, TypeError):
            pass
        
        lines = content.strip().split("\n")
        title = lines[0] if lines else "Untitled"
        
        ac_start = -1
        for i, line in enumerate(lines):
            lower = line.lower()
            if "acceptance criteria" in lower or "ac:" in lower:
                ac_start = i + 1
                break
        
        acceptance_criteria = []
        if ac_start > 0:
            for line in lines[ac_start:]:
                line = line.strip()
                if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                    acceptance_criteria.append(line[1:].strip())
                elif line:
                    acceptance_criteria.append(line)
        
        return {
            "story_id": str(task.task_id),
            "title": title,
            "content": content,
            "acceptance_criteria": acceptance_criteria,
        }

    async def handle_story_event(
        self,
        story_id: str,
        story_title: str,
        story_content: str,
        acceptance_criteria: Optional[List[str]] = None,
        from_status: str = "Todo",
        to_status: str = "InProgress",
    ) -> TaskResult:
        """Handle story status change event (Todo -> InProgress).
        
        This method is called when a story transitions to InProgress,
        triggering the developer workflow.
        """
        if to_status != "InProgress":
            return TaskResult(
                success=True,
                output="Story event ignored (not InProgress transition)",
            )
        
        import json
        from uuid import uuid4
        from app.kafka.event_schemas import AgentTaskType
        
        story_data = json.dumps({
            "story_id": story_id,
            "title": story_title,
            "content": story_content,
            "acceptance_criteria": acceptance_criteria or [],
        })
        
        task = TaskContext(
            task_id=uuid4(),
            task_type=AgentTaskType.IMPLEMENT_STORY,
            priority="high",
            project_id=self.project_id,
            content=story_data,
        )
        
        return await self.handle_task(task)
