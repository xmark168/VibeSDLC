"""Developer V2 Agent - LangGraph-based Story Processor."""

import logging
from typing import List, Optional

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.core.project_context import ProjectContext
from app.models import Agent as AgentModel
from app.agents.developer_v2.src import DeveloperGraph

logger = logging.getLogger(__name__)


class DeveloperV2(BaseAgent):
    """Developer V2 using LangGraph for intelligent story processing.
    
    Handles story events when transitioning from Todo -> InProgress:
    1. Router - Classify story and decide workflow
    2. Analyze - Parse story requirements
    3. Plan - Create implementation plan
    4. Implement - Execute code changes
    5. Validate - Verify against acceptance criteria
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Developer V2 Agent")
        
        self.context = ProjectContext.get(self.project_id)
        self.graph_engine = DeveloperGraph(agent=self)
        
        logger.info(f"[{self.name}] LangGraph initialized")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle story processing task using LangGraph.
        
        Expected task.content format:
        - User story content with title and acceptance criteria
        - Or structured JSON with story_id, title, content, acceptance_criteria
        """
        logger.info(f"[{self.name}] Processing story task: {task.content[:100]}...")
        
        await self.context.ensure_loaded()
        
        try:
            story_data = self._parse_story_content(task)
            
            langfuse_handler = None
            langfuse_ctx = None
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
                    input={"story": story_data.get("title", "")[:200]},
                    tags=["developer_v2", self.role_type],
                    metadata={"agent": self.name, "task_id": str(task.task_id)}
                )
                langfuse_handler = CallbackHandler()
            except Exception as e:
                logger.debug(f"Langfuse setup: {e}")
            
            initial_state = {
                "story_id": story_data.get("story_id", str(task.task_id)),
                "story_title": story_data.get("title", "Untitled Story"),
                "story_content": story_data.get("content", task.content),
                "acceptance_criteria": story_data.get("acceptance_criteria", []),
                "project_id": str(self.project_id),
                "task_id": str(task.task_id),
                "user_id": str(task.user_id) if task.user_id else "",
                "langfuse_handler": langfuse_handler,
                "action": None,
                "task_type": None,
                "complexity": None,
                "analysis_result": None,
                "implementation_plan": None,
                "code_changes": [],
                "files_created": [],
                "files_modified": [],
                "validation_result": None,
                "message": None,
                "confidence": None,
            }
            
            logger.info(f"[{self.name}] Invoking LangGraph for story: {story_data.get('title', 'Untitled')}")
            final_state = await self.graph_engine.graph.ainvoke(initial_state)
            
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
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
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] Graph execution error: {e}", exc_info=True)
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
