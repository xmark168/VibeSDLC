"""Tester Agent - LangGraph Implementation.

ARCHITECTURE:
- Inherits from BaseAgent (Kafka abstracted)
- Handles QA and testing tasks
- Uses LangGraph for integration test generation
- Langfuse tracing for all LLM calls
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import yaml

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel


logger = logging.getLogger(__name__)


class Tester(BaseAgent):
    """Tester agent - creates test plans and ensures software quality.

    NEW ARCHITECTURE:
    - No more separate Consumer/Role layers
    - Handles tasks via handle_task() method
    - Router sends tasks via @Tester mentions
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize Tester.

        Args:
            agent_model: Agent database model
            **kwargs: Additional arguments (heartbeat_interval, max_idle_time)
        """
        super().__init__(agent_model, **kwargs)

        # Load configuration
        self.config = self._load_config()
        
        # Initialize TesterGraph (LangGraph) for all test generation
        from app.agents.tester.graph import TesterGraph
        self.tester_graph = TesterGraph()
        
        # Get project path for test file generation
        from app.core.db import engine
        from sqlmodel import Session
        from app.models import Project
        
        with Session(engine) as session:
            project = session.get(Project, self.project_id)
            self.project_path = project.project_path if project and project.project_path else None
            self.tech_stack = project.tech_stack if project else "nodejs-react"

        logger.info(f"Tester initialized: {self.name}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        config_path = Path(__file__).parent / "config.yaml"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

        # Default configuration
        return {
            "agent": {
                "role": "QA Engineer",
                "goal": "Create comprehensive test plans and ensure software quality",
                "backstory": "You are an experienced QA Engineer expert in testing strategies.",
                "verbose": True,
                "allow_delegation": False,
                "model": "openai/gpt-4",
            }
        }

    def _setup_langfuse(self, task: TaskContext, span_name: str) -> tuple[Any, Any, Any]:
        """Setup Langfuse tracing for graph execution.
        
        Args:
            task: TaskContext for metadata
            span_name: Name for the trace span
            
        Returns:
            Tuple of (langfuse_handler, langfuse_span, langfuse_ctx)
        """
        langfuse_handler = None
        langfuse_span = None
        langfuse_ctx = None
        
        try:
            from langfuse import get_client
            from langfuse.langchain import CallbackHandler
            
            langfuse = get_client()
            langfuse_ctx = langfuse.start_as_current_observation(
                as_type="span",
                name=span_name
            )
            langfuse_span = langfuse_ctx.__enter__()
            langfuse_span.update_trace(
                user_id=str(task.user_id) if task.user_id else None,
                session_id=str(self.project_id),
                input={"message": task.content[:200] if task.content else ""},
                tags=["tester", self.role_type],
                metadata={"agent": self.name, "task_id": str(task.task_id)}
            )
            langfuse_handler = CallbackHandler()
        except Exception as e:
            logger.debug(f"[{self.name}] Langfuse setup: {e}")
        
        return langfuse_handler, langfuse_span, langfuse_ctx
    
    def _close_langfuse(self, langfuse_span: Any, langfuse_ctx: Any, output: dict) -> None:
        """Close Langfuse span after execution."""
        if langfuse_span and langfuse_ctx:
            try:
                langfuse_span.update_trace(output=output)
                langfuse_ctx.__exit__(None, None, None)
            except Exception:
                pass

    def _determine_task_type(self, content: str) -> str:
        """Determine what type of testing task to perform.

        Args:
            content: User message content

        Returns:
            Task type: 'validate', 'test_cases', or 'test_plan'
        """
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in ["validate", "verify", "check compliance"]):
            return "validate"
        elif any(keyword in content_lower for keyword in ["test cases", "scenarios", "specific tests"]):
            return "test_cases"
        else:
            return "test_plan"

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router.

        Args:
            task: TaskContext with user message and metadata

        Returns:
            TaskResult with test plan/cases response
        """
        try:
            # Check if this is auto-triggered from story status change
            if task.context.get("trigger_type") == "status_review":
                return await self._handle_story_review_testing(task)
            
            # Otherwise, handle as manual @Tester mention (legacy flow)
            return await self._handle_manual_request(task)

        except Exception as e:
            logger.error(f"[{self.name}] Error handling task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e),
            )
    
    async def _handle_manual_request(self, task: TaskContext) -> TaskResult:
        """Handle manual @Tester mention - uses LangGraph.
        
        Args:
            task: TaskContext with user message
            
        Returns:
            TaskResult with test generation response
        """
        user_message = task.content

        logger.info(f"[{self.name}] Processing manual QA task: {user_message[:50]}...")

        # Setup Langfuse tracing
        langfuse_handler, langfuse_span, langfuse_ctx = self._setup_langfuse(
            task, "tester_manual_request"
        )
        
        try:
            # Check if project path is available
            if not self.project_path:
                response = (
                    "Xin lỗi, mình chưa có thông tin project path nên không thể tạo test file.\n"
                    "Bạn nhờ admin cấu hình project path giúp mình nhé!"
                )
                await self.message_user("response", response)
                return TaskResult(
                    success=False,
                    output=response,
                    error_message="Project path not configured"
                )
            
            # Use TesterGraph (LangGraph) for test generation
            result = await self.tester_graph.generate_tests(
                project_id=str(self.project_id),
                story_ids=[],  # Empty = all stories in REVIEW
                project_path=self.project_path,
                tech_stack=self.tech_stack,
                langfuse_handler=langfuse_handler,
                user_message=user_message
            )
            
            # Check for errors
            if result.get("error"):
                response = f"Hmm, mình gặp chút vấn đề: {result['error']}"
                await self.message_user("response", response)
                return TaskResult(
                    success=False,
                    output=response,
                    error_message=result['error']
                )
            
            # Build response message
            test_file = result.get("filename", "integration.test.ts")
            test_count = result.get("test_count", 0)
            skipped = result.get("skipped_duplicates", 0)
            
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
            
            logger.info(f"[{self.name}] Manual request completed: {test_count} tests")
            
            return TaskResult(
                success=True,
                output=response,
                structured_data={
                    "task_type": task.task_type.value,
                    "routing_reason": task.routing_reason,
                    "test_file": test_file,
                    "test_count": test_count,
                },
                requires_approval=False,
            )
            
        finally:
            # Close Langfuse
            self._close_langfuse(langfuse_span, langfuse_ctx, {
                "test_count": result.get("test_count", 0) if 'result' in dir() else 0
            })
    
    async def _handle_story_review_testing(self, task: TaskContext) -> TaskResult:
        """Handle auto-triggered integration test generation for stories in REVIEW.
        
        This is triggered automatically when stories move to REVIEW status.
        Generates integration tests for ALL stories currently in REVIEW status.
        
        Args:
            task: TaskContext with trigger_type="status_review"
            
        Returns:
            TaskResult with generated test file info
        """
        story_ids = task.context.get("story_ids", [])
        
        if not story_ids:
            logger.warning(f"[{self.name}] No story_ids in context for review testing")
            return TaskResult(
                success=False,
                error_message="No stories to generate tests for"
            )
        
        logger.info(
            f"[{self.name}] Auto-triggered: Generating integration tests for "
            f"{len(story_ids)} story(ies) in REVIEW status"
        )
        
        # Check if project path is available
        if not self.project_path:
            logger.error(f"[{self.name}] No project_path available for test generation")
            return TaskResult(
                success=False,
                error_message="Project path not configured"
            )
        
        # Setup Langfuse tracing
        langfuse_handler, langfuse_span, langfuse_ctx = self._setup_langfuse(
            task, "tester_auto_review"
        )
        
        try:
            # Use TesterGraph (LangGraph) to generate integration tests
            result = await self.tester_graph.generate_tests(
                project_id=str(self.project_id),
                story_ids=story_ids,
                project_path=self.project_path,
                tech_stack=self.tech_stack,
                langfuse_handler=langfuse_handler
            )
            
            # Check for errors
            if result.get("error"):
                logger.error(f"[{self.name}] TesterGraph error: {result['error']}")
                return TaskResult(
                    success=False,
                    error_message=result['error']
                )
            
            # Extract result info
            test_file = result.get("filename") or result.get("test_file")
            test_count = result.get("test_count", 0)
            skipped = result.get("skipped_duplicates", 0)
            stories_covered = result.get("stories_covered", [])
            
            logger.info(
                f"[{self.name}] Successfully generated {test_count} integration tests "
                f"in file {test_file}"
            )
            
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
            logger.error(
                f"[{self.name}] Error generating integration tests: {e}",
                exc_info=True
            )
            return TaskResult(
                success=False,
                error_message=str(e)
            )
        
        finally:
            # Close Langfuse
            self._close_langfuse(langfuse_span, langfuse_ctx, {
                "test_count": result.get("test_count", 0) if 'result' in dir() else 0,
                "trigger_type": "auto_review"
            })
