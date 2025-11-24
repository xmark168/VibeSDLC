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
                await self.message_user("thinking", "Checking project status...")
                
                # Get project context (could be enhanced with database queries)
                project_context = f"User asking about: {user_message}"
                
                # Run CrewAI asynchronously using native async support
                crew_output = await self.crew.track_progress(project_context)
                
                # Convert CrewAI output to string
                response = str(crew_output) if crew_output else ""
                
            else:
                # General request analysis
                await self.message_user("thinking", "Analyzing request...")
                
                # Run CrewAI asynchronously using native async support
                crew_output = await self.crew.analyze_request(user_message)
                
                # Convert CrewAI output to string (it might be CrewOutput object)
                response = str(crew_output) if crew_output else ""

            logger.info(f"[{self.name}] Generated response: {len(response)} chars, type={type(response).__name__}")
            
            # Validate and sanitize response
            if not response or not response.strip():
                logger.warning(f"[{self.name}] Empty response from crew, using fallback")
                response = "Xin lỗi, tôi không thể xử lý yêu cầu này. Vui lòng thử lại hoặc tag một specialist cụ thể."
            
            # Truncate if too long (max 5000 chars to prevent Kafka message size issues)
            if len(response) > 5000:
                logger.warning(f"[{self.name}] Response too long ({len(response)} chars), truncating to 5000")
                response = response[:5000] + "\n\n... (message truncated)"
            
            # Send response back to user
            logger.info(f"[{self.name}] About to send response to user...")
            try:
                await self.message_user("response", response, {
                    "message_type": "text",  # Use 'text' so frontend renders as normal message
                })
                logger.info(f"[{self.name}] Response sent successfully")
            except Exception as response_error:
                logger.error(f"[{self.name}] CRITICAL: Failed to send response: {response_error}", exc_info=True)
                # Re-raise to ensure it's caught by outer handler
                raise

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
