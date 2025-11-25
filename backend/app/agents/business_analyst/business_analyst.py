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

from crewai import Agent, Crew, Task

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
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
        """Initialize Business Analyst.

        Args:
            agent_model: Agent database model
            **kwargs: Additional arguments (heartbeat_interval, max_idle_time)
        """
        super().__init__(agent_model, **kwargs)

        # Create CrewAI agent with inline config
        self.crew_agent = self._create_crew_agent()

        logger.info(f"Business Analyst initialized: {self.name}")

    def _create_crew_agent(self) -> Agent:
        """Create CrewAI agent for Business Analyst.

        Returns:
            Configured CrewAI Agent
        """
        agent = Agent(
            role="Business Analyst",
            goal="Analyze business requirements, clarify user needs, and create clear specifications",
            backstory="""You are an experienced Business Analyst who excels at:
- Understanding business problems and user needs
- Asking clarifying questions to gather complete requirements
- Creating clear, structured specifications and documentation
- Identifying edge cases and potential issues early
- Translating business needs into actionable requirements

When users ask for requirements analysis or PRDs, you provide structured, 
comprehensive documentation that helps the development team understand what to build.""",
            verbose=True,
            allow_delegation=False,
            llm="openai/gpt-4",
        )

        return agent

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router.

        Args:
            task: TaskContext with user message and metadata

        Returns:
            TaskResult with requirements analysis response
        """
        try:
            # Check if this is a RESUME task (after user answered question)
            from app.kafka.event_schemas import AgentTaskType
            if task.task_type == AgentTaskType.RESUME_WITH_ANSWER:
                return await self._handle_resume(task)
            
            user_message = task.content

            logger.info(f"[{self.name}] Processing BA task: {user_message[:50]}...")
            
            # Check if message is vague and needs clarification
            if self._needs_clarification(user_message):
                logger.info(f"[{self.name}] Message is vague, asking clarification...")
                
                # Ask clarification question
                await self.ask_clarification_question(
                    question="Bạn muốn phân tích khía cạnh nào của dự án?",
                    question_type="multichoice",
                    options=["Requirements", "Architecture", "Risks", "User Stories"],
                    allow_multiple=True
                )
                
                # Return early - task is now PAUSED
                return TaskResult(
                    success=True,
                    output="⏸️ Đang chờ bạn trả lời câu hỏi...",
                    structured_data={"status": "waiting_clarification"}
                )

            # NOTE: Base agent already sent "thinking" event, no need to duplicate

            # Create CrewAI task for requirements analysis
            crew_task = Task(
                description=f"""
                Analyze the following business request and provide requirements analysis:

                {user_message}

                Your analysis should include:
                1. Clear understanding of the business problem or need
                2. Key requirements identified
                3. Potential user stories or use cases
                4. Questions for clarification (if needed)
                5. Suggested next steps

                If this is a complex analysis requiring multi-phase workflow (detailed PRD, 
                user stories, epics), suggest using the dedicated BA workflow API.

                Provide structured, actionable output that can guide development.
                """,
                expected_output="Structured requirements analysis with clear next steps",
                agent=self.crew_agent,
            )

            # Execute crew
            crew = Crew(
                agents=[self.crew_agent],
                tasks=[crew_task],
                verbose=True,
            )

            # Run CrewAI asynchronously using native async support
            result = await crew.kickoff_async(inputs={})

            # Extract response
            response = str(result)

            logger.info(f"[{self.name}] Requirements analysis completed: {len(response)} chars")
            
            # Send response back to user
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
    
    def _needs_clarification(self, message: str) -> bool:
        """Check if message is vague and needs clarification.
        
        Simple heuristic: Check for vague keywords without specific details.
        """
        message_lower = message.lower()
        
        # Vague keywords that suggest need for clarification
        vague_patterns = [
            "phân tích",
            "analyze", 
            "help",
            "dự án",
            "project",
            "requirements",
            "yêu cầu"
        ]
        
        # Check if message is short and contains vague keywords
        if len(message.split()) < 10:  # Short message
            if any(pattern in message_lower for pattern in vague_patterns):
                # Additional check: if message has specific details, don't ask
                specific_indicators = [
                    "api",
                    "database",
                    "user login",
                    "payment",
                    "authentication",
                    "crud",
                    "dashboard"
                ]
                has_specific = any(ind in message_lower for ind in specific_indicators)
                return not has_specific
        
        return False
    
    async def _handle_resume(self, task: TaskContext) -> TaskResult:
        """Handle resume after user answered clarification question.
        
        Args:
            task: TaskContext with RESUME_WITH_ANSWER type
            
        Returns:
            TaskResult with analysis based on clarified intent
        """
        # Extract answer from context
        answer = task.context.get("answer", "")
        selected_options = task.context.get("selected_options", [])
        original_context = task.context.get("original_context", {})
        original_message = original_context.get("original_message", "")
        
        logger.info(
            f"[{self.name}] Resuming with answer: {answer}, "
            f"selected: {selected_options}, original: {original_message}"
        )
        
        # Build focused analysis based on selected aspects
        analysis_prompt = f"""
        Original request: {original_message}
        
        User wants analysis focused on: {', '.join(selected_options)}
        
        Provide detailed analysis for the selected aspects:
        """
        
        for aspect in selected_options:
            if aspect == "Requirements":
                analysis_prompt += "\n- Functional and non-functional requirements"
            elif aspect == "Architecture":
                analysis_prompt += "\n- System architecture and design patterns"
            elif aspect == "Risks":
                analysis_prompt += "\n- Technical and business risks"
            elif aspect == "User Stories":
                analysis_prompt += "\n- User stories and acceptance criteria"
        
        # Create focused CrewAI task
        crew_task = Task(
            description=analysis_prompt,
            expected_output="Detailed analysis of selected aspects",
            agent=self.crew_agent,
        )
        
        crew = Crew(
            agents=[self.crew_agent],
            tasks=[crew_task],
            verbose=True,
        )
        
        # Execute analysis
        result = await crew.kickoff_async(inputs={})
        response = str(result)
        
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
            
            # Send response with artifact reference
            artifact_message = (
                f"📄 **Phân tích yêu cầu hoàn tất**\n\n"
                f"Tôi đã tạo tài liệu phân tích chi tiết với các khía cạnh: {', '.join(selected_options)}\n\n"
                f"**Tài liệu:** {prd_content['title']}\n"
                f"**Artifact ID:** `{artifact_id}`\n\n"
                f"Bạn có thể xem chi tiết trong phần Artifacts.\n\n"
                f"---\n\n"
                f"**Tóm tắt:**\n{response[:300]}..."
            )
            
            await self.message_user("response", artifact_message, {
                "message_type": "artifact_created",
                "artifact_id": str(artifact_id),
                "artifact_type": "analysis",
                "task_completed": True,
                "data": {
                    "analysis": response,
                    "aspects": selected_options,
                    "resumed": True
                }
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
