"""Team Leader Agent - CrewAI Flow-based Kanban Orchestration."""

import logging
from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel
from app.agents.team_leader.flow import TeamLeaderFlow

logger = logging.getLogger(__name__)


class TeamLeader(BaseAgent):
    """Team Leader"""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Team Leader Flow")
        
        
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
            
            # Kickoff flow - returns routing decision dict
            routing = await self.flow.kickoff_async()
            
            # Execute routing decision
            action = routing.get("action")
            
            if action == "DELEGATE":
                # Delegate to specialist
                from datetime import datetime, timezone
                
                task.context["delegation_attempted"] = True
                task.context["delegation_timestamp"] = datetime.now(timezone.utc).isoformat()
                
                return await self.delegate_to_role(
                    task=task,
                    target_role=routing["target_role"],
                    delegation_message=routing["message"]
                )
            
            elif action == "RESPOND":
                # Respond directly to user
                await self.message_user("response", routing["message"])
                
                return TaskResult(
                    success=True,
                    output=routing["message"],
                    structured_data={"action": "respond_direct"}
                )
            
            else:
                # Unknown action
                logger.error(f"Unknown routing action: {action}")
                return TaskResult(
                    success=False,
                    output="",
                    error_message=f"Unknown routing action: {action}"
                )
            
        except Exception as e:
            logger.error(f"[{self.name}] Flow error: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Flow execution error: {str(e)}"
            )

