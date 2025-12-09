"""Developer V2 Agent - LangGraph-based Story Processor.

This module contains the main DeveloperV2 agent class that processes
user stories and generates production-ready code using a LangGraph
state machine workflow.

Typical usage:
    agent = DeveloperV2(agent_model)
    result = await agent.handle_task(task_context)
"""

import logging
from typing import List, Optional

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.core.project_context import ProjectContext
from app.models import Agent as AgentModel
from app.agents.developer_v2.src import DeveloperGraph
from app.agents.developer_v2.src.tools.workspace_manager import ProjectWorkspaceManager
from app.agents.developer_v2.src.tools import commit_workspace_changes
from app.kafka.event_schemas import AgentTaskType

logger = logging.getLogger(__name__)


class DeveloperV2(BaseAgent):
    """AI-powered developer agent using LangGraph for story-driven code generation.

    Processes user stories through 7-node workflow: setup_workspace -> analyze_and_plan
    -> implement -> review -> summarize -> run_code -> (analyze_error if FAIL).

    Attrs: context, graph_engine, workspace_manager, main_workspace
    Limits: max 5 debug iterations, max 2 LBTM/step, max 40 react loops
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Developer V2 Agent")
        
        self.context = ProjectContext.get(self.project_id)
        self.graph_engine = DeveloperGraph(agent=self)
        
        # Workspace management
        self.workspace_manager = ProjectWorkspaceManager(self.project_id)
        self.main_workspace = self.workspace_manager.get_main_workspace()
        
        logger.info(f"[{self.name}] LangGraph initialized, workspace: {self.main_workspace}")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task - route to story processing or user message handling."""
        logger.info(f"[{self.name}] Received task: type={task.task_type}, content={task.content[:100]}...")
        
        await self.context.ensure_loaded()
        
        # Route based on task type
        if task.task_type in [AgentTaskType.STORY_PROCESS, AgentTaskType.IMPLEMENT_STORY]:
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
        try:
            story_data = self._parse_story_content(task)
            return await self._process_story(story_data, task)
        except Exception as e:
            logger.error(f"[{self.name}] Story processing error: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Story processing error: {str(e)}"
            )

    async def _process_story(self, story_data: dict, task: TaskContext) -> TaskResult:
        """Process story through LangGraph workflow.
        
        Note: Workspace setup is now handled by the setup_workspace node in the graph.
        It only creates a branch when code modification is actually needed.
        """
        langfuse_handler = None
        langfuse_ctx = None
        langfuse_span = None
        
        try:
            story_id = story_data.get("story_id", str(task.task_id))
            
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
            initial_state = {
                "story_id": story_id,
                "story_title": story_data.get("title", "Untitled Story"),
                "story_content": story_data.get("content", task.content),
                "acceptance_criteria": story_data.get("acceptance_criteria", []),
                "project_id": str(self.project_id),
                "task_id": str(task.task_id),
                "user_id": str(task.user_id) if task.user_id else "",
                "langfuse_handler": langfuse_handler,
                
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
            
            logger.info(f"[{self.name}] Invoking LangGraph for story: {story_data.get('title', 'Untitled')}")
            final_state = await self.graph_engine.graph.ainvoke(initial_state)
            
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
                    logger.info(f"[{self.name}] Langfuse span closed successfully")
                except Exception as e:
                    logger.error(f"[{self.name}] Langfuse span close error: {e}")
            
            # Commit changes if workspace was setup and has changes
            if final_state.get("workspace_ready"):
                commit_result = commit_workspace_changes(
                    workspace_path=final_state.get("workspace_path"),
                    title=story_data.get("title", "Untitled"),
                    branch_name=final_state.get("branch_name", "unknown"),
                    agent_name=self.name
                )
                logger.info(f"[{self.name}] Commit result: {commit_result}")
            
            action = final_state.get("action")
            task_type = final_state.get("task_type")
            message = final_state.get("message", "")
            
            logger.info(f"[{self.name}] Graph completed: action={action}, type={task_type}")
            
            return TaskResult(
                success=True,
                output=message,
                structured_data={
                    "action": action,
                    "task_type": task_type,
                    "complexity": final_state.get("complexity"),
                    "analysis": final_state.get("analysis_result"),
                    "plan_steps": len(final_state.get("implementation_plan", [])),
                    "files_created": final_state.get("files_created", []),
                    "files_modified": final_state.get("files_modified", []),
                    "validation": final_state.get("validation_result"),
                    "tests_passed": final_state.get("tests_passed"),
                    "branch_name": final_state.get("branch_name"),
                    "workspace_path": final_state.get("workspace_path"),
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Graph execution error: {e}", exc_info=True)
            
            # Cleanup langfuse span on error (Team Leader pattern)
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                    logger.info(f"[{self.name}] Langfuse span closed (on error)")
                except Exception as cleanup_err:
                    logger.error(f"[{self.name}] Langfuse cleanup error: {cleanup_err}")
            
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
        logger.info(f"[{self.name}] Story event: {story_id} ({from_status} -> {to_status})")
        
        if to_status != "InProgress":
            logger.info(f"[{self.name}] Ignoring non-InProgress transition")
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
            task_type=AgentTaskType.STORY_PROCESS,
            priority="high",
            project_id=self.project_id,
            content=story_data,
        )
        
        return await self.handle_task(task)
