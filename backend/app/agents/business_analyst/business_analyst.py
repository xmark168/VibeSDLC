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
            user_message = task.content

            logger.info(f"[{self.name}] Processing BA task: {user_message[:50]}...")

            # Status update
            await self.message_user("thinking", "Analyzing business requirements...")

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
