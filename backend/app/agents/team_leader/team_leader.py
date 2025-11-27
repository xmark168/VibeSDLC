"""Team Leader Agent - CrewAI Flow-based Kanban Orchestration."""

import logging
from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel

logger = logging.getLogger(__name__)


class TeamLeader(BaseAgent):
    """Team Leader"""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Team Leader Flow")
        
        from app.agents.team_leader.flow import TeamLeaderFlow
        
        self.flow = TeamLeaderFlow(
            project_id=self.project_id,
            agent_name=self.name
        )

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using Flow."""
        logger.info(f"[{self.name}] Processing task with Flow")
        
        try:
            # Store task in flow before kickoff
            self.flow.current_task = task
            
            # Kickoff flow (no inputs needed, task already stored)
            result = await self.flow.kickoff_async()
            
            # Check if need to send message to user
            if isinstance(result, TaskResult):
                # If RESPOND action, send message to user
                if result.structured_data and result.structured_data.get("action") == "respond_direct":
                    await self.message_user("response", result.output)
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.name}] Flow error: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Flow execution error: {str(e)}"
            )

