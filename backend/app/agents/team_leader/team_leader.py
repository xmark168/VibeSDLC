"""Team Leader Agent - LangGraph-based Routing."""

import logging
from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.core.project_context import ProjectContext
from app.models import Agent as AgentModel
from app.agents.team_leader.src import TeamLeaderGraph

logger = logging.getLogger(__name__)


class TeamLeader(BaseAgent):
    """Team Leader using LangGraph for intelligent routing."""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Team Leader Agent")
        
        # Shared project context (memory + preferences)
        self.context = ProjectContext.get(self.project_id)
        
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
        
        # Load shared context (cached, parallel loading)
        await self.context.ensure_loaded()
        
        try:
            # 1. Add user message to shared memory
            self.context.add_message("user", task.content)
            
            # 2. Setup Langfuse tracing (1 trace for entire graph)
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

