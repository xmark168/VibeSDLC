"""Team Leader Agent - Crew-based project coordination.

Architecture:
- Inherits from BaseAgent (Kafka integration, task handling)
- Uses TeamLeaderCrew (multi-agent crew for analysis and coordination)
- Analyzes user requests and suggests appropriate specialists
"""

import logging
from typing import Any, Dict
from uuid import uuid4

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.team_leader.crew import TeamLeaderCrew
from app.models import Agent as AgentModel
from app.kafka.event_schemas import RouterTaskEvent, AgentTaskType, KafkaTopics


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

    def _should_delegate_to_analyst(self, message: str) -> bool:
        """Check if message should be delegated to Business Analyst.
        
        Args:
            message: User message to analyze
            
        Returns:
            True if message is about project analysis
        """
        # Keywords that indicate analysis tasks
        analysis_keywords = [
            # Vietnamese
            "phân tích", "analysis", "analyze", "đánh giá", "requirements", 
            "yêu cầu", "tài liệu", "document", "prd", "specification",
            "user story", "use case", "functional", "non-functional",
            "kiến trúc", "architecture", "thiết kế", "design",
            "rủi ro", "risk", "ước lượng", "estimate", "feasibility",
            # English
            "requirement", "spec", "documentation", "business", "process",
            "workflow", "stakeholder", "user need", "feature request"
        ]
        
        message_lower = message.lower()
        
        # Check for keywords
        for keyword in analysis_keywords:
            if keyword in message_lower:
                return True
                
        return False
    
    async def _delegate_to_business_analyst(self, task: TaskContext) -> TaskResult:
        """Delegate task to Business Analyst.
        
        Args:
            task: Original task context
            
        Returns:
            TaskResult indicating delegation
        """
        try:
            # Get Business Analyst from database
            from app.services import AgentService
            from sqlmodel import Session
            from app.core.db import engine
            
            with Session(engine) as session:
                agent_service = AgentService(session)
                ba = agent_service.get_by_project_and_role(
                    project_id=self.project_id,
                    role_type="business_analyst"
                )
                
                if not ba:
                    logger.warning(f"[{self.name}] Business Analyst not found in project")
                    return TaskResult(
                        success=False,
                        output="",
                        error_message="Business Analyst not available in this project"
                    )
                
                # Publish delegation task to BA
                producer = await self._get_producer()
                
                delegation_event = RouterTaskEvent(
                    event_type="router.task.dispatched",
                    task_id=uuid4(),
                    task_type=AgentTaskType.MESSAGE,
                    agent_id=ba.id,
                    agent_role="business_analyst",
                    source_event_type=task.context.get("source_event_type", "user.message.sent"),
                    source_event_id=task.context.get("source_event_id", str(task.task_id)),
                    routing_reason=f"delegated_by_team_leader:{self.name}",
                    priority="high",
                    context={
                        "message_id": task.message_id,
                        "user_id": task.user_id,
                        "content": task.content,
                        "project_id": str(self.project_id),
                        "delegated_from": self.name,
                        **task.context,
                    }
                )
                
                await producer.publish(
                    topic=KafkaTopics.AGENT_TASKS,
                    event=delegation_event
                )
                
                logger.info(f"[{self.name}] Delegated analysis task to Business Analyst: {ba.name}")
                
                # Update conversation context to BA
                from app.models import Project
                from datetime import datetime, timezone
                
                project = session.get(Project, self.project_id)
                if project:
                    project.active_agent_id = ba.id
                    project.active_agent_updated_at = datetime.now(timezone.utc)
                    session.add(project)
                    session.commit()
                    
                    logger.info(
                        f"[{self.name}] Updated active agent context to: {ba.human_name}"
                    )
                
                # Notify user about delegation
                delegation_message = (
                    f"Tôi nhận thấy đây là câu hỏi về phân tích dự án. "
                    f"Tôi đã chuyển yêu cầu này cho @{ba.human_name} - chuyên gia phân tích của chúng ta. "
                    f"Họ sẽ giúp bạn chi tiết hơn! 📊"
                )
                
                await self.message_user("response", delegation_message, {
                    "message_type": "text",
                    "delegated_to": ba.human_name,
                    "delegation_reason": "analysis_request"
                })
                
                return TaskResult(
                    success=True,
                    output=delegation_message,
                    structured_data={
                        "delegated_to": ba.human_name,
                        "delegation_reason": "analysis_request"
                    }
                )
                
        except Exception as e:
            logger.error(f"[{self.name}] Error delegating to BA: {e}", exc_info=True)
            return TaskResult(
                success=False,
                output="",
                error_message=f"Failed to delegate: {str(e)}"
            )

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

            # Check if this should be delegated to Business Analyst
            if self._should_delegate_to_analyst(user_message):
                logger.info(f"[{self.name}] Detected analysis request, delegating to Business Analyst")
                return await self._delegate_to_business_analyst(task)

            # Determine task type and route to appropriate crew workflow
            # NOTE: Base agent already sent "thinking" event, no need to duplicate
            
            if task_type == "progress_query" or "status" in user_message.lower():
                # Progress tracking request
                # Get project context (could be enhanced with database queries)
                project_context = f"User asking about: {user_message}"
                
                # Run CrewAI asynchronously using native async support
                crew_output = await self.crew.track_progress(project_context)
                
                # Convert CrewAI output to string
                response = str(crew_output) if crew_output else ""
                
            else:
                # General request analysis
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
