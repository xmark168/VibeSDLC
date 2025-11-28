"""Tester Agent - LangGraph Implementation.

ARCHITECTURE (same as Team Leader):
- Inherits from BaseAgent
- Uses LangGraph for test generation (src/graph.py)
- Langfuse: 1 trace for entire graph, session_id = project_id
"""

import logging
from datetime import datetime

from sqlmodel import Session

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.core.db import engine
from app.models import Agent as AgentModel, Project
from app.agents.tester.src import TesterGraph


logger = logging.getLogger(__name__)


class Tester(BaseAgent):
    """Tester agent - creates test plans and ensures software quality.

    ARCHITECTURE (same as Team Leader):
    - Inherits from BaseAgent
    - Uses LangGraph for test generation
    - Langfuse: 1 trace for entire graph, session_id = project_id
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize Tester."""
        super().__init__(agent_model, **kwargs)
        
        # Initialize TesterGraph (LangGraph) - pass self for agent reference
        self.graph_engine = TesterGraph(agent=self)
        
        # Get project path for test file generation
        with Session(engine) as session:
            project = session.get(Project, self.project_id)
            self.project_path = project.project_path if project and project.project_path else None
            self.tech_stack = project.tech_stack if project else "nodejs-react"

        logger.info(f"[{self.name}] Tester initialized with LangGraph")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph with Langfuse tracing.
        
        Same pattern as Team Leader:
        1. Setup Langfuse (1 trace for entire graph)
        2. Build initial state
        3. Execute graph via self.graph_engine.graph.ainvoke()
        4. Close Langfuse span
        """
        # Determine task type
        is_auto_review = task.context.get("trigger_type") == "status_review"
        story_ids = task.context.get("story_ids", []) if is_auto_review else []
        
        logger.info(f"[{self.name}] Processing task: {task.content[:50] if task.content else 'auto-trigger'}...")
        
        # Validate prerequisites
        if is_auto_review and not story_ids:
            logger.warning(f"[{self.name}] No story_ids in context for review testing")
            return TaskResult(success=False, error_message="No stories to generate tests for")
        
        if not self.project_path:
            error_msg = "Project path not configured"
            if not is_auto_review:
                await self.message_user("response", 
                    "Xin lỗi, mình chưa có thông tin project path nên không thể tạo test file.\n"
                    "Bạn nhờ admin cấu hình project path giúp mình nhé!"
                )
            logger.error(f"[{self.name}] {error_msg}")
            return TaskResult(success=False, output="", error_message=error_msg)
        
        # 1. Setup Langfuse tracing (1 trace for entire graph) - same as Team Leader
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
            # Update trace with metadata (session_id = project_id)
            langfuse_span.update_trace(
                user_id=str(task.user_id) if task.user_id else None,
                session_id=str(self.project_id),
                input={
                    "message": task.content[:200] if task.content else "",
                    "trigger_type": "auto_review" if is_auto_review else "manual",
                    "story_ids": story_ids[:5] if story_ids else []
                },
                tags=["tester", self.role_type, "auto" if is_auto_review else "manual"],
                metadata={"agent": self.name, "task_id": str(task.task_id)}
            )
            # Handler inherits trace context automatically
            langfuse_handler = CallbackHandler()
        except Exception as e:
            logger.debug(f"Langfuse setup: {e}")
        
        try:
            # 2. Build initial state (same pattern as Team Leader)
            initial_state = {
                "project_id": str(self.project_id),
                "story_ids": story_ids,
                "project_path": self.project_path,
                "tech_stack": self.tech_stack,
                "timestamp": datetime.now().strftime("%Y-%m-%d-%H%M%S"),
                "user_message": task.content or "",
                "stories": [],
                "test_scenarios": [],
                "test_cases": [],
                "test_content": "",
                "langfuse_handler": langfuse_handler,
                "result": {},
                "error": None,
            }
            
            # 3. Execute graph (same as Team Leader)
            logger.info(f"[{self.name}] Invoking TesterGraph...")
            final_state = await self.graph_engine.graph.ainvoke(initial_state)
            
            # Extract results
            result = final_state.get("result", {})
            error = final_state.get("error") or result.get("error")
            
            if error:
                logger.error(f"[{self.name}] TesterGraph error: {error}")
                # Update trace and close on error
                if langfuse_span and langfuse_ctx:
                    try:
                        langfuse_span.update_trace(output={"error": error})
                        langfuse_ctx.__exit__(None, None, None)
                    except Exception:
                        pass
                if not is_auto_review:
                    await self.message_user("response", f"Hmm, mình gặp chút vấn đề: {error}")
                return TaskResult(success=False, error_message=error)
            
            # Extract result info
            test_file = result.get("filename") or result.get("test_file", "")
            test_count = result.get("test_count", 0)
            skipped = result.get("skipped_duplicates", 0)
            stories_covered = result.get("stories_covered", [])
            
            # 4. Update trace output and close span (same as Team Leader)
            if langfuse_span and langfuse_ctx:
                try:
                    langfuse_span.update_trace(output={
                        "test_file": test_file,
                        "test_count": test_count,
                        "skipped_duplicates": skipped,
                        "trigger_type": "auto_review" if is_auto_review else "manual"
                    })
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            logger.info(
                f"[{self.name}] Graph completed: test_file={test_file}, "
                f"test_count={test_count}, skipped={skipped}"
            )
            
            # Build response for manual requests
            if not is_auto_review:
                if test_count == 0 and skipped > 0:
                    response = (
                        f"Mình check rồi, {skipped} tests cho stories này đã có sẵn trong file `{test_file}`.\n"
                        f"Không cần tạo thêm đâu!"
                    )
                elif skipped > 0:
                    response = (
                        f"Xong rồi! Mình đã thêm {test_count} test cases mới vào file `{test_file}` "
                        f"(bỏ qua {skipped} tests đã có)."
                    )
                else:
                    response = f"Xong rồi! Mình đã tạo {test_count} test cases trong file `{test_file}`."
                
                await self.message_user("response", response)
                
                return TaskResult(
                    success=True,
                    output=response,
                    structured_data={
                        "task_type": task.task_type.value if task.task_type else "test",
                        "routing_reason": task.routing_reason,
                        "test_file": test_file,
                        "test_count": test_count,
                    }
                )
            else:
                # Auto-review response
                return TaskResult(
                    success=True,
                    output=f"Generated integration tests: {test_file}",
                    structured_data={
                        "test_file": test_file,
                        "test_count": test_count,
                        "stories_covered": stories_covered,
                        "trigger_type": "auto_review"
                    }
                )
            
        except Exception as e:
            logger.error(f"[{self.name}] LangGraph error: {e}", exc_info=True)
            # Cleanup langfuse on error (same as Team Leader)
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(type(e), e, e.__traceback__)
                except Exception:
                    pass
            return TaskResult(
                success=False,
                output="",
                error_message=f"Graph execution error: {str(e)}"
            )
