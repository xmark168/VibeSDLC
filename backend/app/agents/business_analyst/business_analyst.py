"""Business Analyst Agent - Simple chat-based requirements analysis.

NEW ARCHITECTURE:
- Inherits from BaseAgent (Kafka abstracted)
- Handles requirements analysis and business tasks
- Responds to @BusinessAnalyst mentions in chat
- Provides PRD generation and requirements gathering
"""

import asyncio
import logging
from typing import Any, Dict
from uuid import UUID

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.business_analyst.crew import BusinessAnalystCrew
from app.models import Agent as AgentModel


logger = logging.getLogger(__name__)


class BusinessAnalyst(BaseAgent):
    """Business Analyst agent - analyzes requirements and business needs.

    NEW ARCHITECTURE:
    - No more separate Consumer/Role layers
    - Handles tasks via handle_task() method
    - Router sends tasks via @BusinessAnalyst mentions in chat
    - Provides requirements analysis, PRD generation, and business documentation
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize Business Analyst."""
        super().__init__(agent_model, **kwargs)

        self.crew = BusinessAnalystCrew()

        logger.info(f"Business Analyst initialized: {self.name}")

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router."""
        try:
            from app.kafka.event_schemas import AgentTaskType
            if task.task_type == AgentTaskType.RESUME_WITH_ANSWER:
                return await self._handle_resume(task)
            
            user_message = task.content
            logger.info(f"[{self.name}] Processing BA task: {user_message[:50]}...")
            
            needs_clarification = await self.crew.check_needs_clarification(user_message)
            if needs_clarification:
                logger.info(f"[{self.name}] Message needs clarification, asking user...")
                
                await self.ask_clarification_question(
                    question="Bạn muốn phân tích khía cạnh nào của dự án?",
                    question_type="multichoice",
                    options=["Requirements", "Architecture", "Risks", "User Stories"],
                    allow_multiple=True
                )
                
                return TaskResult(
                    success=True,
                    output="⏸️ Đang chờ bạn trả lời câu hỏi...",
                    structured_data={"status": "waiting_clarification"}
                )

            response = await self.crew.analyze_requirements(user_message)

            logger.info(f"[{self.name}] Requirements analysis completed: {len(response)} chars")
            
            await self.message_user("response", response, {
                "message_type": "requirements_analysis",
                "data": {
                    "analysis": response,
                    "analysis_type": "requirements_analysis"
                }
            })

            return TaskResult(
                success=True,
                output=response,
                structured_data={
                    "task_type": task.task_type.value,
                    "routing_reason": task.routing_reason,
                    "analysis_type": "requirements_analysis",
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
    
    async def _handle_resume(self, task: TaskContext) -> TaskResult:
        """Handle resume after user answered clarification question."""
        answer = task.context.get("answer", "")
        selected_options = task.context.get("selected_options", [])
        original_context = task.context.get("original_context", {})
        original_message = original_context.get("original_message", "")
        
        logger.info(
            f"[{self.name}] Resuming with answer: {answer}, "
            f"selected: {selected_options}, original: {original_message}"
        )
        aspects_details = []
        for aspect in selected_options:
            if aspect == "Requirements":
                aspects_details.append("- Functional and non-functional requirements")
            elif aspect == "Architecture":
                aspects_details.append("- System architecture and design patterns")
            elif aspect == "Risks":
                aspects_details.append("- Technical and business risks")
            elif aspect == "User Stories":
                aspects_details.append("- User stories and acceptance criteria")
        
        response = await self.crew.analyze_with_context(
            original_message=original_message,
            selected_aspects=', '.join(selected_options),
            aspects_list='\n'.join(aspects_details)
        )
        
        logger.info(f"[{self.name}] Resume analysis completed: {len(response)} chars")
        
        # Parse response into structured PRD content
        # TODO: Use LLM to extract structured data from response
        prd_content = {
            "title": f"Requirements Analysis: {original_message[:50]}",
            "overview": response[:500] if len(response) > 500 else response,
            "goals": [f"Analyze {aspect}" for aspect in selected_options],
            "target_users": ["Development Team", "Product Owner"],
            "requirements": [
                {
                    "id": f"REQ-{i+1}",
                    "title": aspect,
                    "description": f"Requirements for {aspect}",
                    "priority": "high",
                    "type": "functional"
                }
                for i, aspect in enumerate(selected_options)
            ],
            "acceptance_criteria": ["Analysis covers all selected aspects"],
            "constraints": [],
            "risks": [],
            "next_steps": ["Review requirements", "Create user stories", "Design architecture"],
            "full_analysis": response  # Include full analysis text
        }
        
        # Create PRD artifact
        try:
            artifact_id = await self.create_artifact(
                artifact_type="analysis",
                title=f"Requirements Analysis - {original_message[:30]}",
                content=prd_content,
                description=f"Requirements analysis focused on: {', '.join(selected_options)}",
                tags=["requirements", "analysis"] + [asp.lower() for asp in selected_options]
            )
            
            logger.info(f"[{self.name}] Created artifact {artifact_id}")
            
            # Send concise response (Claude-style)
            artifact_message = (
                f"📄 Tôi đã tạo tài liệu phân tích yêu cầu với các khía cạnh: "
                f"{', '.join(selected_options)}. "
                f"Click vào artifact card bên dưới để xem chi tiết."
            )
            
            await self.message_user("response", artifact_message, {
                "message_type": "artifact_created",
                "artifact_id": str(artifact_id),
                "artifact_type": "analysis",
                "title": prd_content['title'],
                "description": f"Requirements analysis focused on: {', '.join(selected_options)}",
                "version": 1,
                "status": "draft",
                "task_completed": True,
            })
            
        except Exception as e:
            logger.error(f"[{self.name}] Failed to create artifact: {e}", exc_info=True)
            # Fallback to regular message if artifact creation fails
            await self.message_user("response", response, {
                "message_type": "requirements_analysis",
                "task_completed": True,
                "data": {
                    "analysis": response,
                    "aspects": selected_options,
                    "resumed": True
                }
            })
        
        return TaskResult(
            success=True,
            output=response,
            structured_data={
                "resumed": True,
                "selected_aspects": selected_options,
                "original_message": original_message,
                "task_completed": True,
                "artifact_id": str(artifact_id) if 'artifact_id' in locals() else None
            }
        )
