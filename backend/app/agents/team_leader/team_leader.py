"""
Team Leader Agent
"""

import logging

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

        logger.info(f"Team Leader initialized: {self.name}")

    async def _should_delegate_to_analyst_smart(self, message: str) -> tuple[bool, str]:
        """Use CrewAI to decide if message should be delegated to BA."""
        try:
            should_delegate, reason = await self.crew.check_should_delegate(message)
            logger.info(f"[{self.name}] Delegation decision: {should_delegate}, reason: {reason[:100]}")
            return should_delegate, reason
        except Exception as e:
            logger.error(f"[{self.name}] Error in delegation check: {e}", exc_info=True)
            return False, f"delegation_check_failed: {str(e)}"

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router."""
        try:
            user_message = task.content
            task_type = task.task_type.value

            logger.info(f"[{self.name}] Processing {task_type}: {user_message[:50]}...")

            # CHANGE 1: Make delegation_failed handling terminal - return immediately
            if task.context.get("delegation_failed"):
                target_role = task.context.get("target_role")
                error_message = task.context.get("error_message")
                original_content = task.context.get("original_content", user_message)
                
                logger.warning(f"[{self.name}] Delegation to {target_role} failed, providing fallback response")
                
                # Provide a helpful fallback response instead of trying to delegate again
                fallback_response = (
                    f"{error_message}\n\n"
                    f"Tuy nhiên, tôi có thể giúp bạn một số việc:\n"
                    f"- Giải thích cách bắt đầu một dự án mới\n"
                    f"- Hướng dẫn quy trình phát triển\n"
                    f"- Trả lời câu hỏi chung về dự án\n\n"
                    f"Bạn muốn tôi giúp gì?"
                )
                
                await self.message_user("response", fallback_response, {
                    "message_type": "text",
                    "delegation_failed": True,
                    "target_role": target_role
                })
                
                # Return immediately - do NOT continue to crew processing
                return TaskResult(
                    success=True,
                    output="",  # Already sent message above
                    structured_data={
                        "delegation_failed": True,
                        "target_role": target_role,
                        "fallback_provided": True
                    }
                )
            
            # CHANGE 3: Check for prior delegation attempts before delegating
            should_delegate = False
            # Don't delegate if already attempted or if this is a delegation_failed callback
            if not task.context.get("delegation_failed") and not task.context.get("delegation_attempted"):
                should_delegate, reason = await self._should_delegate_to_analyst_smart(user_message)
                
                if should_delegate:
                    logger.info(f"[{self.name}] Delegating to BA (reason: {reason[:100]})")
                    
                    # CHANGE 2: Add marker to prevent re-delegation if this comes back
                    from datetime import datetime, timezone
                    task.context["delegation_attempted"] = True
                    task.context["delegation_timestamp"] = datetime.now(timezone.utc).isoformat()
                    
                    return await self.delegate_to_role(
                        task=task,
                        target_role="business_analyst",
                        delegation_message=(
                            f"Tôi nhận thấy đây là câu hỏi về phân tích dự án. "
                            f"Tôi đã chuyển yêu cầu này cho Business Analyst - chuyên gia phân tích của chúng ta. "
                            f"Họ sẽ giúp bạn chi tiết hơn! 📊"
                        )
                    )

            if task_type == "progress_query" or "status" in user_message.lower():
                project_context = f"User asking about: {user_message}"
                crew_output = await self.crew.track_progress(project_context)
                response = str(crew_output) if crew_output else ""
            else:
                crew_output = await self.crew.analyze_request(user_message)
                response = str(crew_output) if crew_output else ""

            logger.info(f"[{self.name}] Generated response: {len(response)} chars")
            
            if not response or not response.strip():
                logger.warning(f"[{self.name}] Empty response from crew, using fallback")
                response = "Xin lỗi, tôi không thể xử lý yêu cầu này. Vui lòng thử lại hoặc tag một specialist cụ thể."
            
            if len(response) > 5000:
                logger.warning(f"[{self.name}] Response too long, truncating")
                response = response[:5000] + "\n\n... (message truncated)"
            
            # Don't call message_user here - TaskResult output will be sent automatically
            return TaskResult(
                success=True,
                output=response,
                structured_data={
                    "task_type": task_type,
                    "routing_reason": task.routing_reason,
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
