"""Team Leader Agent"""

import logging
from pathlib import Path
from sqlmodel import Session
from app.core.agent.base_agent import BaseAgent, TaskContext, TaskResult
from app.core.agent.project_context import ProjectContext
from app.models import Agent as AgentModel, ArtifactType, Epic, Story, Project
from app.agents.team_leader.src import TeamLeaderGraph, generate_response_message, check_cancel_intent
from app.agents.team_leader.project_manager import ProjectManager
from app.kafka.event_schemas import AgentTaskType
from app.core.db import engine
from app.services.artifact_service import ArtifactService
from app.utils.project_files import ProjectFiles

logger = logging.getLogger(__name__)


class TeamLeader(BaseAgent):
    """Team Leader using LangGraph for intelligent routing."""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Team Leader Agent")
        
        self.context = ProjectContext.get(self.project_id) 
        self.project_files = None
        if self.project_id:
            with Session(engine) as session:
                project = session.get(Project, self.project_id)
                if project and project.project_path:
                    self.project_files = ProjectFiles(Path(project.project_path))
                else:
                    default_path = Path("projects") / str(self.project_id)
                    default_path.mkdir(parents=True, exist_ok=True)
                    self.project_files = ProjectFiles(default_path)
        
        # Initialize ProjectManager for handling project confirmations
        self.project_manager = ProjectManager(self)
        
        # Pass self to graph for delegation and Langfuse callback access
        self.graph_engine = TeamLeaderGraph(agent=self)
        
        logger.info(f"[{self.name}] LangGraph initialized")
    
    async def update_preference(self, key: str, value) -> bool:
        """Update a single preference in DB and shared cache."""
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.models import ProjectPreference
            
            with Session(engine) as session:
                pref = session.query(ProjectPreference).filter(
                    ProjectPreference.project_id == self.project_id
                ).first()
                
                if not pref:
                    pref = ProjectPreference(
                        project_id=self.project_id,
                        preferences={key: value}
                    )
                    session.add(pref)
                else:
                    current = pref.preferences or {}
                    current[key] = value
                    pref.preferences = current
                
                session.commit()
                
                # Update shared cache
                self.context.update_preference(key, value)
                logger.info(f"[{self.name}] Updated preference: {key} = {value}")
                return True
                
        except Exception as e:
            logger.error(f"[{self.name}] Failed to update preference: {e}")
            return False

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph with conversation memory."""
        logger.info(f"[{self.name}] Processing task: {task.content[:50]}")
        
        # Check if this is a resume task (user answered a question)
        is_resume = task.task_type == AgentTaskType.RESUME_WITH_ANSWER
        
        if is_resume:
            # For multichoice, answer is in selected_options
            context = task.context or {}
            answer = context.get("answer", "")
            selected_options = context.get("selected_options", [])
            
            # Use selected_options if answer is empty (multichoice case)
            if not answer and selected_options:
                answer = selected_options[0] if isinstance(selected_options, list) else str(selected_options)
            
            logger.info(f"[{self.name}] Processing RESUME task with answer: {answer[:50] if answer else 'empty'}")
            return await self._handle_resume_task(task, answer)
        
        # Load shared context (cached, parallel loading)
        await self.context.ensure_loaded()
        
        try:
            # 1. Add user message to shared memory
            self.context.add_message("user", task.content)
            
            # 2. Setup Langfuse tracing (1 trace for entire graph)
            langfuse_handler = None
            langfuse_span = None
            langfuse_ctx = None
            
            # Check if Langfuse is enabled before initializing
            from app.core.config import settings
            if settings.LANGFUSE_ENABLED:
                try:
                    from langfuse import get_client
                    from langfuse.langchain import CallbackHandler
                    langfuse = get_client()
                    # Create parent span for entire graph execution
                    langfuse_ctx = langfuse.start_as_current_observation(
                        as_type="span",
                        name="team_leader_graph"
                    )
                    # Enter context and get span object
                    langfuse_span = langfuse_ctx.__enter__()
                    # Update trace with metadata (on span, not context)
                    langfuse_span.update_trace(
                        user_id=str(task.user_id) if task.user_id else None,
                        session_id=str(self.project_id),
                        input={"message": task.content[:200]},
                        tags=["team_leader", self.role_type],
                        metadata={"agent": self.name, "task_id": str(task.task_id)}
                    )
                    # Handler inherits trace context automatically
                    langfuse_handler = CallbackHandler()
                except Exception as e:
                    logger.debug(f"Langfuse setup: {e}")
            
            # 3. Build state
            initial_state = {
                "user_message": task.content,
                "user_id": str(task.user_id) if task.user_id else "",
                "project_id": str(self.project_id),
                "task_id": str(task.task_id),
                "conversation_history": self.context.format_memory(),
                "user_preferences": self.context.format_preferences(),
                "attachments": task.context.get("attachments") if task.context else None,  # Pass file attachments
                "action": None,
                "target_role": None,
                "message": None,
                "reason": None,
                "confidence": None,
                "wip_blocked": None,
                "langfuse_handler": langfuse_handler,
            }
            
            # 4. Execute graph
            logger.info(f"[{self.name}] Invoking LangGraph...")
            final_state = await self.graph_engine.graph.ainvoke(initial_state)
            
            # 5. Update trace output and close span
            if langfuse_span and langfuse_ctx:
                try:
                    langfuse_span.update_trace(output={
                        "action": final_state.get("action"),
                        "target_role": final_state.get("target_role"),
                    })
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass
            
            action = final_state.get("action")
            confidence = final_state.get("confidence")
            target_role = final_state.get("target_role")
            wip_blocked = final_state.get("wip_blocked", False)
            response_msg = final_state.get("message", "")
            
            # 6. Add response to shared memory
            if response_msg:
                self.context.add_message("assistant", response_msg)
            
            logger.info(
                f"[{self.name}] Graph completed: action={action}, "
                f"confidence={confidence}, wip_blocked={wip_blocked}"
            )
            
            return TaskResult(
                success=True,
                output=response_msg,
                structured_data={
                    "action": action,
                    "target_role": target_role,
                    "reason": final_state.get("reason"),
                    "confidence": confidence,
                    "wip_blocked": wip_blocked,
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] LangGraph error: {e}", exc_info=True)
            # Cleanup langfuse on error
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
    
    async def _handle_resume_task(self, task: TaskContext, answer: str) -> TaskResult:
        """Handle resume task - delegate to ProjectManager."""
        try:
            routing_reason = task.routing_reason or ""
            
            if "question_answer" not in routing_reason:
                logger.warning(f"[{self.name}] Unknown resume task: {routing_reason}")
                return TaskResult(success=False, output="", error_message="Unknown resume task type")
            
            # Delegate to ProjectManager
            return await self.project_manager.handle_confirmation_answer(task, answer)
                
        except Exception as e:
            logger.error(f"[{self.name}] Error handling resume task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Resume task error: {str(e)}"
            )
