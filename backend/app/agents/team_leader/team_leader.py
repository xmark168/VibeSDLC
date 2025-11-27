"""Team Leader Agent - LangGraph-based Routing."""

import logging
from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel
from app.agents.team_leader.graph import TeamLeaderGraph

logger = logging.getLogger(__name__)


class TeamLeader(BaseAgent):
    """Team Leader using LangGraph for intelligent routing."""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Team Leader LangGraph")
        
        self.graph_engine = TeamLeaderGraph(agent=self)
        
        logger.info(f"[{self.name}] LangGraph initialized successfully")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using LangGraph."""
        logger.info(f"[{self.name}] Processing task with LangGraph: {task.content[:50]}")
        
        try:
            initial_state = {
                "messages": [],
                "user_message": task.content,
                "user_id": str(task.user_id) if task.user_id else "",
                "project_id": str(self.project_id),
                "task_id": str(task.task_id),
                "action": None,
                "target_role": None,
                "message": None,
                "reason": None,
                "confidence": None,
            }
            
            logger.info(f"[{self.name}] Invoking LangGraph...")
            final_state = await self.graph_engine.graph.ainvoke(initial_state)
            
            action = final_state.get("action")
            confidence = final_state.get("confidence")
            
            logger.info(
                f"[{self.name}] Graph completed: action={action}, "
                f"confidence={confidence}"
            )
            
            return TaskResult(
                success=True,
                output=final_state.get("message", ""),
                structured_data={
                    "action": action,
                    "target_role": final_state.get("target_role"),
                    "reason": final_state.get("reason"),
                    "confidence": confidence,
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] LangGraph error: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Graph execution error: {str(e)}"
            )

