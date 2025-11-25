"""Team Leader Agent - Crew-based project coordination.

Architecture:
- Inherits from BaseAgent (Kafka integration, task handling)
- Uses TeamLeaderCrew (multi-agent crew for analysis and coordination)
- Analyzes user requests and suggests appropriate specialists
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

        logger.info(f"Team Leader initialized: {self.name} with {len(self.crew.agents)} crew members")

    async def _should_delegate_to_analyst_smart(self, message: str) -> tuple[bool, str]:
        """Use CrewAI to decide if message should be delegated to BA."""
        try:
            from crewai import Crew, Task, Process
            
            decision_task = Task(
                description=f"""Analyze this user message and decide if it should be handled by a Business Analyst.

User Message: "{message}"

A Business Analyst should handle:
- New project ideas (e.g., "I want to build a website", "tôi muốn làm website")
- Feature requests that need requirements analysis
- Vague inquiries about "what can we build"
- Questions about project scope, requirements, specifications
- Project ideas that need clarification

Business Analyst should NOT handle:
- Project status queries (that's for Team Leader)
- Simple greetings (that's for Team Leader)
- Technical implementation questions (that's for Developer)
- Bug reports or testing (that's for Tester)

Answer in this format:
DECISION: [YES or NO]
REASON: [one sentence why]
""",
                agent=self.crew.agents["project_coordinator"],
                expected_output="DECISION: YES/NO with brief reason"
            )
            
            crew = Crew(
                agents=[self.crew.agents["project_coordinator"]],
                tasks=[decision_task],
                process=Process.sequential,
                verbose=False,
            )
            
            result = await crew.kickoff_async(inputs={})
            result_str = str(result).upper()
            
            should_delegate = "DECISION: YES" in result_str or "YES" in result_str[:100]
            reason = str(result).split("REASON:")[-1].strip() if "REASON:" in str(result) else "AI decision"
            
            logger.info(f"[{self.name}] Delegation decision: {should_delegate}, reason: {reason[:100]}")
            
            return should_delegate, reason
            
        except Exception as e:
            logger.error(f"[{self.name}] Error in smart delegation check: {e}", exc_info=True)
            return self._should_delegate_to_analyst_fallback(message), "fallback"
    
    def _should_delegate_to_analyst_fallback(self, message: str) -> bool:
        """Fallback keyword-based delegation check if CrewAI fails."""
        keywords = [
            "phân tích", "analysis", "requirements", "yêu cầu",
            "tài liệu", "document", "prd", "specification",
            "muốn làm", "muốn tạo", "muốn xây dựng", "muốn phát triển",
            "ý tưởng", "dự án mới", "project idea",
            "want to build", "want to create", "want to make",
            "website", "app", "ứng dụng", "hệ thống", "phần mềm",
        ]
        
        message_lower = message.lower()
        return any(kw in message_lower for kw in keywords)

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router."""
        try:
            user_message = task.content
            task_type = task.task_type.value

            logger.info(f"[{self.name}] Processing {task_type}: {user_message[:50]}...")

            if task.context.get("delegation_failed"):
                target_role = task.context.get("target_role")
                error_message = task.context.get("error_message")
                original_content = task.context.get("original_content", user_message)
                
                logger.warning(f"[{self.name}] Delegation to {target_role} failed, handling as fallback")
                
                await self.message_user("response", error_message, {
                    "message_type": "text",
                    "delegation_failed": True,
                    "target_role": target_role
                })
                
                user_message = original_content
            
            should_delegate = False
            if not task.context.get("delegation_failed"):
                should_delegate, reason = await self._should_delegate_to_analyst_smart(user_message)
                
                if should_delegate:
                    logger.info(f"[{self.name}] Delegating to BA (reason: {reason[:100]})")
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
            
            await self.message_user("response", response, {"message_type": "text"})

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
