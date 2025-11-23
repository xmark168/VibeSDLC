"""Team Leader Agent - Crew-based project coordination.

Architecture:
- Inherits from BaseAgent (Kafka integration, task handling)
- Uses TeamLeaderCrew (multi-agent crew for analysis and coordination)
- Analyzes user requests and suggests appropriate specialists
"""

import logging
from typing import Any, Dict

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.team_leader.crew import TeamLeaderCrew
from app.models import Agent as AgentModel


logger = logging.getLogger(__name__)


class TeamLeader(BaseAgent):
    """Team Leader agent - coordinates project activities using a multi-agent crew.

    Architecture:
    - BaseAgent: Handles Kafka integration, state management, task routing
    - TeamLeaderCrew: Multi-agent crew for request analysis and coordination
    
    The crew consists of:
    - Requirements Analyst: Clarifies what users need
    - Project Coordinator: Suggests which specialist to tag
    - Progress Tracker: Monitors and reports project progress
    
    Workflow:
    1. User sends message without @mention → Router sends to Team Leader
    2. Team Leader crew analyzes request
    3. Provides guidance + suggests specialist (e.g., "@Developer for implementation")
    4. User tags specialist → Router sends directly to that agent
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize Team Leader.

        Args:
            agent_model: Agent database model
            **kwargs: Additional arguments (heartbeat_interval, max_idle_time)
        """
        super().__init__(agent_model, **kwargs)

        # Initialize crew
        self.crew = TeamLeaderCrew()

        logger.info(f"Team Leader initialized: {self.name} with {len(self.crew.agents)} crew members")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router.

        Args:
            task: TaskContext with user message and metadata

        Returns:
            TaskResult with guidance response
        """
        try:
            user_message = task.content
            task_type = task.task_type.value

            logger.info(f"[{self.name}] Processing {task_type}: {user_message[:50]}...")

            # Determine task type and route to appropriate crew workflow
            if task_type == "progress_query" or "status" in user_message.lower():
                # Progress tracking request
                await self.update_progress(1, 2, "Checking project status")
                
                # Get project context (could be enhanced with database queries)
                project_context = f"User asking about: {user_message}"
                
                response = self.crew.track_progress(project_context)
                
                await self.update_progress(2, 2, "Complete")
                
            else:
                # General request analysis
                await self.update_progress(1, 3, "Analyzing request")
                
                # Use crew to analyze and provide guidance
                response = self.crew.analyze_request(user_message)
                
                await self.update_progress(3, 3, "Complete")

            logger.info(f"[{self.name}] Generated response: {len(response)} chars")

            return TaskResult(
                success=True,
                output=response,
                structured_data={
                    "task_type": task_type,
                    "routing_reason": task.routing_reason,
                    "crew_agents_used": len(self.crew.agents),
                },
                requires_approval=False,
            )

        except Exception as e:
            logger.error(f"[{self.name}] Error handling task: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=str(e),
            )


# ===== ARCHITECTURE NOTES =====

"""
OLD ARCHITECTURE (Deprecated):
- Team Leader delegated tasks to specialists directly
- Used AGENT_ROUTING events
- Complex coordination logic in agent code

NEW ARCHITECTURE (Current):
- Router handles all task routing based on @mentions
- Team Leader provides guidance and suggestions
- User controls routing by tagging specialists
- Cleaner separation of concerns

CREW COMPOSITION:
- Requirements Analyst: Understands user needs, identifies requirements
- Project Coordinator: Maps needs to specialists, provides tagging suggestions
- Progress Tracker: Monitors project status, provides updates

WORKFLOW EXAMPLE:

1. User: "I need a new feature for user authentication"
   → Router: No @mention → sends to Team Leader
   
2. Team Leader Crew:
   - Requirements Analyst: "User wants authentication feature"
   - Project Coordinator: "This needs requirements + development"
   - Response: "I understand you need authentication. Let's start by defining requirements. 
               Please tag @BusinessAnalyst to create a PRD for this feature."
   
3. User: "@BusinessAnalyst create PRD for user auth"
   → Router: @BusinessAnalyst mentioned → sends to Business Analyst
   
4. BA creates PRD → publishes response
   
5. User: "@Developer implement the auth system from the PRD"
   → Router: @Developer mentioned → sends to Developer

This gives users full control while Team Leader provides expert guidance.
"""
