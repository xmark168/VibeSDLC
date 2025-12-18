"""Developer Agent"""
import asyncio
import logging
from typing import Dict, List, Optional, Set
from uuid import UUID

from app.core.agent.base_agent import BaseAgent, TaskContext, TaskResult
from app.core.agent.project_context import ProjectContext
from app.core.agent.mixins import PausableAgentMixin, StoryStoppedException
from app.core.agent.graph_helpers import get_or_create_thread_id
from app.models import Agent as AgentModel
from app.models.base import StoryAgentState
from app.agents.developer.src import DeveloperGraph
from app.utils.workspace_utils import ProjectWorkspaceManager
from app.kafka.event_schemas import AgentTaskType

from app.agents.developer.src.utils.signal_utils import check_interrupt_signal

logger = logging.getLogger(__name__)


class Developer(BaseAgent, PausableAgentMixin):

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        self.context = ProjectContext.get(self.project_id)
        self.graph_engine = DeveloperGraph(agent=self)
        self.workspace_manager = ProjectWorkspaceManager(self.project_id)
        self.main_workspace = self.workspace_manager.get_main_workspace()
        # Initialize PausableAgentMixin (provides pause/resume/cancel functionality)
        self.init_pausable_mixin()
    
    # Override _cleanup_story_db_resources for Developer-specific cleanup (running_pid)
    async def _cleanup_story_db_resources(self, story_id: str):
        """Cleanup story-specific DB resources - kill running process."""
        try:
            import os
            import signal
            from uuid import UUID
            from sqlmodel import Session
            from app.core.db import engine
            from app.models import Story
            
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
        except Exception as e:
            logger.debug(f"[{self.name}] DB cleanup error: {e}")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task - route to story processing or user message handling.
        
        All task types are handled through the graph with routing based on graph_task_type:
        - MESSAGE → respond node  
        - IMPLEMENT_STORY → setup_workspace → plan → implement...
        - REVIEW_PR → handled separately (not in graph)
        """
        await self.context.ensure_loaded()
        
        # REVIEW_PR is handled separately (not in graph)
        if task.task_type == AgentTaskType.REVIEW_PR:
            return await self._handle_merge_to_main(task)
        
        # Route MESSAGE through graph
        if task.task_type == AgentTaskType.MESSAGE:
            return await self._handle_chat_task(task, graph_task_type="message")
        
        # IMPLEMENT_STORY - use full story processing flow
        return await self._handle_story_processing(task)
    
    async def _handle_chat_task(self, task: TaskContext, graph_task_type: str) -> TaskResult:
        """Handle chat tasks (MESSAGE) through graph.
        
        Uses lightweight graph invocation for quick responses.
        """
        context = task.context or {}
        story_id = context.get("story_id", str(task.task_id))
        user_message = context.get("content", task.content)
        
        # Try to get progress from checkpoint (for story_message only)
        current_step = 0
        total_steps = 0
        if graph_task_type == "story_message":
            try:
                config = {"configurable": {"thread_id": f"{self.agent_id}_{story_id}"}}
                checkpoint = await self.graph_engine.checkpointer.aget(config)
                if checkpoint and checkpoint.get("channel_values"):
                    values = checkpoint["channel_values"]
                    current_step = values.get("current_step", 0)
                    total_steps = values.get("total_steps", 0)
            except Exception:
                pass
        
        # Minimal state - node will load story info from DB
        initial_state = {
            "graph_task_type": graph_task_type,
            "story_id": story_id,
            "user_message": user_message,
            "current_step": current_step,
            "total_steps": total_steps,
            "project_id": str(self.project_id),
            "task_id": str(task.task_id),
            "user_id": str(task.user_id) if task.user_id else "",
        }
        
        try:
            await self.graph_engine.setup()
            config = {"configurable": {"thread_id": f"chat_{task.task_id}"}}
            
            final_state = None
            async for state in self.graph_engine.graph.astream(initial_state, config):
                final_state = state
            
            response = ""
            if final_state:
                # Get response from the node output
                for node_name, node_state in final_state.items():
                    if isinstance(node_state, dict) and "response" in node_state:
                        response = node_state.get("response", "")
                        break
            
            logger.info(f"[{self.name}] Chat task completed: {graph_task_type}")
            return TaskResult(success=True, output=response)
            
        except Exception as e:
            logger.error(f"[{self.name}] Chat task error: {e}", exc_info=True)
            return TaskResult(success=False, output="", error_message=str(e))

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
                
                # Check if story is already cancelled/cancel_requested - abort early
                current_state = self.get_story_state_from_db(story_id)
                if current_state in [StoryAgentState.CANCELED, StoryAgentState.CANCEL_REQUESTED]:
                    logger.info(f"[{self.name}] Story {story_id} is {current_state}, skipping")
                    return TaskResult(success=False, output="", error_message=f"Story is {current_state.value}")
                
                # NOTE: Don't set PROCESSING here - keep PENDING until workspace is ready
                # PROCESSING will be set by setup_workspace node after successful setup
                
                story_data = await self._load_story_from_db(story_id)
                
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
                # Additional fields for chat context
                "status": story.status.value if story.status else "todo",
                "agent_state": story.agent_state.value if story.agent_state else None,
                "branch_name": story.branch_name,
                "pr_url": story.pr_url,
                "pr_state": story.pr_state,
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
        langfuse_ctx = None
        langfuse_span = None
        
        try:
            story_id = story_data.get("story_id", str(task.task_id))
            
            # Clear any leftover signals from previous runs
            # Note: Restart API clears signal after sending cancel and waiting
            self.clear_signal(story_id)
            logger.info(f"[{self.name}] Cleared signals for story {story_id}")
            
            from app.core.config import settings
            
            logger.info(f"[{self.name}] Checking Langfuse: LANGFUSE_ENABLED={settings.LANGFUSE_ENABLED}")
            logger.info(f"[{self.name}] Langfuse keys: SECRET={bool(settings.LANGFUSE_SECRET_KEY)}, PUBLIC={bool(settings.LANGFUSE_PUBLIC_KEY)}")
            
            # Create Langfuse span for single unified trace (Team Leader pattern)
            # Wrap entire graph execution in start_as_current_observation
            langfuse_span = None
            langfuse_ctx = None
            if settings.LANGFUSE_ENABLED:
                try:
                    from langfuse import get_client
                    langfuse = get_client()
                    
                    # Create observation context - ALL operations inside will be in single trace!
                    langfuse_ctx = langfuse.start_as_current_observation(
                        as_type="span",
                        name="developer_story_execution"
                    )
                    langfuse_span = langfuse_ctx.__enter__()
                    
                    # Create LangChain CallbackHandler for detailed tracing
                    from langfuse.langchain import CallbackHandler
                    langfuse_handler = CallbackHandler()
                    
                    # Set trace-level metadata
                    langfuse_span.update_trace(
                        user_id=str(task.user_id) if task.user_id else None,
                        session_id=story_id,  # Group by session for filtering
                        input={"story": story_data.get("content", "")[:500]},
                        tags=["developer", self.role_type, f"story:{story_data.get('story_code', '')}"],
                        metadata={
                            "agent": self.name,
                            "story_code": story_data.get("story_code", ""),
                            "story_title": story_data.get("title", "")[:200],
                            "project_id": str(self.project_id)
                        }
                    )
                    
                    logger.info(f"[{self.name}] ✓ Langfuse span started - trace={langfuse_span.trace_id}")
                    
                except Exception as e:
                    logger.error(f"[{self.name}] ❌ Langfuse span creation failed: {e}", exc_info=True)
                    langfuse_span = None
                    langfuse_ctx = None
                    langfuse_handler = None
            else:
                logger.warning(f"[{self.name}] Langfuse DISABLED")
                langfuse_handler = None
            
            # Initial state - workspace will be set up by setup_workspace node if needed
            # NOTE: langfuse_handler is passed via config["callbacks"], NOT in state
            # This avoids serialization issues with PostgresSaver checkpoint (msgpack)
            story_code = story_data.get("story_code", f"STORY-{story_id[:8]}")
            initial_state = {
                # Graph routing - implement_story routes to setup_workspace
                "graph_task_type": "implement_story",
                
                "story_id": story_id,
                "story_code": story_code,
                "story_title": story_data.get("title", "Untitled Story"),
                "story_content": story_data.get("content", task.content),
                "acceptance_criteria": story_data.get("acceptance_criteria", []),
                "project_id": str(self.project_id),
                "task_id": str(task.task_id),
                "user_id": str(task.user_id) if task.user_id else "",
                
                # Workspace context - will be populated by setup_workspace node
                "workspace_path": "",
                "branch_name": "",
                "main_workspace": str(self.main_workspace),
                "workspace_ready": False,
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
            
            logger.info(f"✓ LANGFUSE: Observation context active: {langfuse_span is not None}, Handler created: {langfuse_handler is not None}")
            
            # Validate story state before checking signal
            # If story was canceled/restarted while we were setting up, clear stale signal
            from app.models import Story
            from app.api.deps import get_db
            try:
                db = next(get_db())
                story = db.get(Story, story_id)
                if story and story.agent_state != StoryAgentState.PROCESSING:
                    # Stale signal - story state changed externally (restart/cancel)
                    self.clear_signal(story_id)
                    logger.warning(f"[{self.name}] Cleared stale signal - story state is {story.agent_state}, not PROCESSING")
            except Exception as e:
                logger.debug(f"[{self.name}] Could not validate story state: {e}")
            
            # Check signal before starting graph (in case cancel came during setup)
            signal = self.check_signal(story_id)
            if signal == "cancel":
                logger.info(f"[{self.name}] Cancel signal found before graph start, aborting")
                await self._update_story_state(story_id, StoryAgentState.CANCELED)
                return TaskResult(success=False, output="", error_message="Cancelled before start")
            
            # Setup graph with PostgresSaver for persistent checkpoints
            logger.info(f"[{self.name}] Setting up graph with PostgresSaver...")
            await self.graph_engine.setup()
            logger.info(f"[{self.name}] Graph setup complete, checkpointer: {type(self.graph_engine.checkpointer).__name__}")
            
            # Track current task for cancel/pause
            current_task = asyncio.current_task()
            if current_task:
                self._running_tasks[story_id] = current_task
            
            # Thread ID for checkpointing (enables pause/resume)
            # Use helper to get or create thread_id
            thread_id = get_or_create_thread_id(story_id, self.agent_id, is_resume)

            # NOTE: langfuse_handler is passed via config["callbacks"], NOT in state
            # This avoids serialization issues with PostgresSaver checkpoint (msgpack)
            config = {
                "configurable": {"thread_id": thread_id},
                "callbacks": [langfuse_handler] if langfuse_handler else [],
            }

            # Check if resuming from pause
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
                # Start fresh with signal-checking wrapper
                final_state = await self._run_graph_with_signal_check(
                    self.graph_engine.graph,
                    initial_state,
                    config,
                    story_id
                )
            
            # Check for LangGraph interrupt (pause/cancel signal was caught by a node)
            interrupt_info = final_state.get("__interrupt__")
            logger.info(f"[{self.name}] Checking interrupt: {interrupt_info is not None}")
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
                    from app.agents.developer.src.nodes.implement import git_revert_uncommitted, git_reset_all
                    if reason == "pause":
                        # Revert uncommitted changes (keep commits)
                        await git_revert_uncommitted(workspace_path)
                        logger.info(f"[{self.name}] Reverted uncommitted changes on pause")
                    elif reason == "cancel":
                        # Reset all changes to base branch
                        base_branch = final_state.get("base_branch", "main")
                        await git_reset_all(workspace_path, base_branch)
                        logger.info(f"[{self.name}] Reset all changes on cancel")
                
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
            logger.info(f"[{self.name}] Final state: run_status={run_status}, action={action}, task_type={task_type}")
            if run_status == "PASS":
                # Squash WIP commits into single commit on success (non-critical)
                workspace_path = final_state.get("workspace_path", "")
                if workspace_path:
                    try:
                        from app.agents.developer.src.nodes.implement import git_squash_wip_commits
                        story_title = initial_state.get("title", "implement story")
                        base_branch = final_state.get("base_branch", "main")
                        await git_squash_wip_commits(workspace_path, base_branch, f"feat: {story_title}")
                        logger.info(f"[{self.name}] Squashed WIP commits")
                    except Exception as squash_err:
                        # Git squash is non-critical, don't fail the whole story
                        logger.warning(f"[{self.name}] Failed to squash commits (non-critical): {squash_err}")
                
                if not await self._update_story_state(story_id, StoryAgentState.FINISHED):
                    logger.error(f"Failed to set FINISHED state for {story_id}")
            else:
                if not await self._update_story_state(story_id, StoryAgentState.CANCELED):
                    logger.error(f"Failed to set CANCELED state for {story_id}")
            
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
            # Story was stopped via signal or DB state check
            logger.info(f"[{self.name}] Story {story_id} stopped: {e.message}")
            
            # Remove from local tracking
            self._running_tasks.pop(story_id, None)
            
            # Clear the signal after handling
            self.consume_signal(story_id)
            
            # Handle based on state
            if e.state in [StoryAgentState.CANCEL_REQUESTED, StoryAgentState.CANCELED]:
                # Cancel requested/canceled - transition to CANCELED
                if e.state == StoryAgentState.CANCEL_REQUESTED:
                    await self._update_story_state(story_id, StoryAgentState.CANCELED)
            
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

    async def _handle_merge_to_main(self, task: TaskContext) -> TaskResult:
        """Handle merge story branch to main/master.
        
        Flow:
        1. Fetch latest main branch
        2. Merge main into story branch (in worktree)
        3. If conflict: try to resolve, if not possible mark as conflict
        4. If success: merge story branch into main
        5. Cleanup worktree and branch
        """
        import subprocess
        from pathlib import Path
        from uuid import UUID
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Story
        from app.models.story import StoryStatus
        from app.agents.developer.src.utils.story_logger import log_to_story
        
        # Extract task context
        ctx = task.context or {}
        story_id = ctx.get("story_id") or (task.content if isinstance(task.content, str) else None)
        branch_name = ctx.get("branch_name")
        worktree_path = ctx.get("worktree_path")
        main_workspace = ctx.get("main_workspace")
        project_id = str(task.project_id) if task.project_id else ctx.get("project_id")
        
        if not story_id:
            return TaskResult(success=False, output="Missing story_id in task context")
        
        logger.info(f"[{self.name}] Starting merge task for story {story_id}")
        
        # Get story from DB
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id))
            if not story:
                return TaskResult(success=False, output=f"Story not found: {story_id}")
            
            branch_name = branch_name or story.branch_name
            worktree_path = worktree_path or story.worktree_path
            
            if not branch_name:
                story.pr_state = "error"
                story.merge_status = "no_branch"
                session.add(story)
                session.commit()
                return TaskResult(success=False, output="Story has no branch to merge")
        
        # Determine workspace to use
        workspace = worktree_path if worktree_path and Path(worktree_path).exists() else main_workspace
        if not workspace or not Path(workspace).exists():
            await self._update_merge_status(story_id, "error", "no_workspace")
            return TaskResult(success=False, output="No valid workspace found")
        
        await log_to_story(story_id, project_id, f"🔄 Starting merge of {branch_name} to main...", "info", "merge")
        
        # STOP DEV SERVER IF RUNNING (before merge to avoid conflicts)
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id))
            if story and story.running_pid:
                await log_to_story(story_id, project_id, f"🛑 Stopping dev server (PID {story.running_pid})...", "info", "merge")
                try:
                    import os
                    import signal
                    os.kill(story.running_pid, signal.SIGTERM)
                    await log_to_story(story_id, project_id, f"✅ Dev server stopped", "success", "merge")
                except (ProcessLookupError, OSError):
                    await log_to_story(story_id, project_id, f"⚠️ Dev server already stopped or not found", "warning", "merge")
                
                # Clear dev server fields in DB
                story.running_pid = None
                story.running_port = None
                session.add(story)
                session.commit()
        
        try:
            # Use main workspace (not worktree) for merge operations
            main_ws = main_workspace if main_workspace and Path(main_workspace).exists() else workspace
            
            # 1. Detect default branch (local)
            base_branch = "main"
            for branch in ["main", "master"]:
                result = subprocess.run(
                    ["git", "branch", "--list", branch],
                    cwd=main_ws, capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    base_branch = branch
                    break
            
            await log_to_story(story_id, project_id, f"📍 Base branch: {base_branch}, workspace: {main_ws}", "info", "merge")
            
            # 2. Fetch all branches
            await log_to_story(story_id, project_id, f"📥 Fetching latest changes...", "info", "merge")
            from app.utils.git_utils import git_fetch_all
            git_fetch_all(main_ws, timeout=60)
            
            # 3. Switch to base branch and pull latest
            await log_to_story(story_id, project_id, f"🔀 Switching to {base_branch}...", "info", "merge")
            checkout_result = subprocess.run(
                ["git", "checkout", base_branch],
                cwd=main_ws, capture_output=True, text=True, timeout=30
            )
            if checkout_result.returncode != 0:
                await self._update_merge_status(story_id, "error", "checkout_failed")
                await log_to_story(story_id, project_id, f"Failed to checkout {base_branch}: {checkout_result.stderr}", "error", "merge")
                return TaskResult(success=False, output=f"Failed to checkout {base_branch}")
            
            from app.utils.git_utils import git_pull
            git_pull(base_branch, remote="origin", cwd=main_ws, timeout=60)
            
            # 4. Merge story branch into base branch (local merge)
            await log_to_story(story_id, project_id, f"🔀 Merging {branch_name} into {base_branch}...", "info", "merge")
            merge_result = subprocess.run(
                ["git", "merge", branch_name, "--no-ff", "-m", f"Merge branch '{branch_name}'"],
                cwd=main_ws, capture_output=True, text=True, timeout=60
            )
            
            if merge_result.returncode != 0:
                from app.utils.git_utils import git_merge_abort
                # Check if conflict
                if "CONFLICT" in merge_result.stdout or "CONFLICT" in merge_result.stderr:
                    git_merge_abort(main_ws, timeout=10)
                    await self._update_merge_status(story_id, "conflict", "merge_conflict")
                    await log_to_story(story_id, project_id, f"Merge conflict! Please resolve manually.", "error", "merge")
                    return TaskResult(success=False, output=f"Merge conflict. Manual resolution required.")
                else:
                    error_msg = merge_result.stderr or merge_result.stdout
                    git_merge_abort(main_ws, timeout=10)
                    await self._update_merge_status(story_id, "error", "merge_failed")
                    await log_to_story(story_id, project_id, f"Merge failed: {error_msg[:200]}", "error", "merge")
                    return TaskResult(success=False, output=f"Merge failed: {error_msg}")
            
            await log_to_story(story_id, project_id, f"Successfully merged {branch_name} into {base_branch}", "success", "merge")
            
            # 5. Cleanup
            await log_to_story(story_id, project_id, f"🧹 Cleaning up worktree and branch...", "info", "merge")
            await self._cleanup_after_merge(story_id, worktree_path, branch_name, main_ws)
            
            # 6. Move story to Done and update merge status
            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                if story:
                    story.status = StoryStatus.DONE
                    story.pr_state = "merged"
                    story.merge_status = "merged"
                    session.add(story)
                    session.commit()
            
            # 7. Broadcast status change to frontend
            from app.websocket.connection_manager import connection_manager
            await connection_manager.broadcast_to_project({
                "type": "story_status_changed",
                "story_id": story_id,
                "status": "Done",
                "merge_status": "merged",
                "pr_state": "merged",
                # Clear dev server status để frontend ẩn nút dev server
                "running_pid": None,
                "running_port": None,
            }, UUID(project_id))
            
            await log_to_story(story_id, project_id, f"Story moved to Done", "success", "merge")
            await log_to_story(story_id, project_id, f"Successfully merged {branch_name} into {base_branch}!", "success", "merge")
            
            return TaskResult(
                success=True,
                output=f"Successfully merged {branch_name} into {base_branch}",
                structured_data={
                    "branch_name": branch_name,
                    "base_branch": base_branch,
                    "merge_status": "merged"
                }
            )
            
        except subprocess.TimeoutExpired:
            await self._update_merge_status(story_id, "error", "timeout")
            await log_to_story(story_id, project_id, "Merge operation timed out", "error", "merge")
            return TaskResult(success=False, output="Merge operation timed out")
        except Exception as e:
            logger.error(f"[{self.name}] Merge error: {e}")
            await self._update_merge_status(story_id, "error", "exception")
            await log_to_story(story_id, project_id, f"Merge error: {str(e)[:200]}", "error", "merge")
            return TaskResult(success=False, output=f"Merge error: {e}")

    async def _update_merge_status(self, story_id: str, pr_state: str, merge_status: str):
        """Update story merge status in DB and broadcast via WebSocket."""
        from uuid import UUID
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Story
        from app.websocket.connection_manager import connection_manager
        
        project_id = None
        with Session(engine) as session:
            story = session.get(Story, UUID(story_id))
            if story:
                story.pr_state = pr_state
                story.merge_status = merge_status
                project_id = story.project_id
                session.add(story)
                session.commit()
        
        # Broadcast WebSocket event for UI update
        if project_id:
            await connection_manager.broadcast_to_project({
                "type": "story_state_changed",
                "story_id": story_id,
                "pr_state": pr_state,
                "merge_status": merge_status,
            }, project_id)

    async def _cleanup_after_merge(self, story_id: str, worktree_path: str | None, branch_name: str | None, main_workspace: str):
        """Cleanup worktree and branch after successful merge."""
        import subprocess
        from pathlib import Path
        import shutil
        from uuid import UUID
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Story
        
        try:
            # 1. Remove worktree
            if worktree_path and Path(worktree_path).exists():
                try:
                    subprocess.run(
                        ["git", "worktree", "remove", worktree_path, "--force"],
                        cwd=main_workspace, capture_output=True, timeout=30
                    )
                except:
                    shutil.rmtree(worktree_path, ignore_errors=True)
                logger.info(f"[{self.name}] Removed worktree: {worktree_path}")
            
            # 2. Delete branch (local and remote)
            if branch_name:
                subprocess.run(
                    ["git", "branch", "-D", branch_name],
                    cwd=main_workspace, capture_output=True, timeout=10
                )
                subprocess.run(
                    ["git", "push", "origin", "--delete", branch_name],
                    cwd=main_workspace, capture_output=True, timeout=30
                )
                logger.info(f"[{self.name}] Deleted branch: {branch_name}")
            
            # 3. Update story in DB
            with Session(engine) as session:
                story = session.get(Story, UUID(story_id))
                if story:
                    story.worktree_path = None
                    story.branch_name = None
                    session.add(story)
                    session.commit()
                    
        except Exception as e:
            logger.error(f"[{self.name}] Cleanup error: {e}")
