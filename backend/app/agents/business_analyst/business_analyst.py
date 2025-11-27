"""Business Analyst Agent - LangGraph-based Implementation."""

import logging
from pathlib import Path

from sqlmodel import Session, select

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel, Project
from app.utils.project_files import ProjectFiles
from app.kafka.event_schemas import AgentTaskType
from app.core.db import engine
from app.agents.business_analyst.src import BusinessAnalystGraph

logger = logging.getLogger(__name__)


class BusinessAnalyst(BaseAgent):
    """Business Analyst using LangGraph for workflow management.
    
    Langfuse tracing is handled by BaseAgent.get_langfuse_callback().
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Business Analyst LangGraph")
        
        # Initialize project files
        self.project_files = None
        if self.project_id:
            with Session(engine) as session:
                project = session.exec(
                    select(Project).where(Project.id == self.project_id)
                ).first()
                
                if project and project.project_path:
                    self.project_files = ProjectFiles(Path(project.project_path))
                else:
                    default_path = Path("projects") / str(self.project_id)
                    default_path.mkdir(parents=True, exist_ok=True)
                    self.project_files = ProjectFiles(default_path)
        
        # Pass self to graph for Langfuse callback access
        self.graph_engine = BusinessAnalystGraph(agent=self)
        
        logger.info(f"[{self.name}] LangGraph initialized successfully")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph.
        
        Note: Langfuse tracing is automatically handled by BaseAgent.
        """
        logger.info(f"[{self.name}] Processing task with LangGraph: {task.content[:50]}")
        
        try:
            # Validate user message
            if not task.content or not task.content.strip():
                logger.error(f"[{self.name}] Empty task content received")
                return TaskResult(
                    success=False,
                    output="",
                    error_message="Empty user message"
                )
            
            # Check if this is a resume task
            is_resume = task.task_type == AgentTaskType.RESUME_WITH_ANSWER
            
            # Load existing PRD if available
            existing_prd = None
            if self.project_files:
                try:
                    existing_prd = await self.project_files.load_prd()
                except Exception as e:
                    logger.debug(f"[{self.name}] No existing PRD: {e}")
            
            # Prepare collected_info based on task type
            collected_info = {}
            user_message = task.content
            
            if is_resume:
                collected_info = {
                    "user_answers": [task.content],
                    "last_interaction": "answered_questions"
                }
                user_message = (
                    f"User provided answer to previous questions: {task.content}\n\n"
                    f"Now that we have more information, proceed to generate PRD."
                )
            
            # Prepare initial state
            initial_state = {
                "user_message": user_message,
                "project_id": str(self.project_id),
                "task_id": str(task.task_id),
                "user_id": str(task.user_id) if task.user_id else "",
                "project_path": str(self.project_files.project_path) if self.project_files else "",
                "collected_info": collected_info,
                "existing_prd": existing_prd,
                "intent": "",
                "reasoning": "",
                "questions": [],
                "questions_sent": False,
                "prd_draft": None,
                "prd_final": None,
                "prd_saved": False,
                "change_summary": "",
                "stories": [],
                "stories_saved": False,
                "analysis_text": "",
                "error": None,
                "retry_count": 0,
                "result": {},
                "is_complete": False
            }
            
            logger.info(f"[{self.name}] Invoking LangGraph...")
            final_state = await self.graph_engine.execute(initial_state)
            
            # Extract result
            result_data = final_state.get("result", {})
            action = final_state.get("intent", "completed")
            
            logger.info(f"[{self.name}] Graph completed: action={action}")
            
            return TaskResult(
                success=True,
                output=str(result_data),
                structured_data=result_data
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] LangGraph error: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Graph execution error: {str(e)}"
            )
