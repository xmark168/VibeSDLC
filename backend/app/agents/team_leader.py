"""Team Leader Agent - Merged Role + Crew Implementation.

This is the new simplified architecture where TeamLeader:
- Inherits from BaseAgent (Kafka abstracted)
- Analyzes user requests
- Responds directly (delegation handled by Router via @mentions)
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict
from uuid import UUID

from crewai import Agent, Crew, Task

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.models import Agent as AgentModel


logger = logging.getLogger(__name__)


class TeamLeader(BaseAgent):
    """Team Leader agent - analyzes requests and responds.

    NEW ARCHITECTURE:
    - No more delegation logic (Router handles routing via @mentions)
    - Focuses on understanding user requests and providing guidance
    - Can suggest which specialist to tag for specific tasks
    """

    def __init__(self, agent_model: AgentModel):
        """Initialize Team Leader.

        Args:
            agent_model: Agent database model
        """
        super().__init__(agent_model)

        # Create CrewAI agent with inline config
        self.crew_agent = self._create_crew_agent()

        logger.info(f"Team Leader initialized: {self.name}")

    def _create_crew_agent(self) -> Agent:
        """Create CrewAI agent for Team Leader.

        Returns:
            Configured CrewAI Agent
        """
        # Create agent with inline configuration
        # CrewAI handles LLM instantiation from model string
        agent = Agent(
            role="SDLC Team Leader",
            goal="Understand user requests, provide helpful guidance, and suggest which specialist to consult",
            backstory="""You are an experienced Team Leader helping users with software development.
When users have questions or needs, you provide guidance and suggest the right specialist:
- @BusinessAnalyst for requirements analysis, PRD creation, user stories
- @Developer for code implementation, technical design, architecture
- @Tester for QA planning, test cases, quality assurance

You do NOT delegate tasks directly - users tag specialists themselves.
Your role is to understand, guide, and suggest.""",
            verbose=True,
            allow_delegation=False,  # No delegation - Router handles routing
            llm="openai/gpt-4",  # CrewAI handles LLM instantiation
        )

        return agent

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task assigned by Router.

        Args:
            task: TaskContext with user message and metadata

        Returns:
            TaskResult with response
        """
        try:
            user_message = task.content

            logger.info(f"[{self.name}] Processing message: {user_message[:50]}...")

            # Update progress
            await self.update_progress(1, 3, "Analyzing user request")

            # Create CrewAI task
            crew_task = Task(
                description=f"""Analyze this user request and provide helpful guidance:

User Message: {user_message}

Your response should:
1. Show understanding of the user's needs
2. Provide relevant guidance or suggestions
3. If the request requires a specialist, suggest which one to tag:
   - @BusinessAnalyst for requirements analysis, PRD creation, user stories
   - @Developer for code implementation, architecture, technical design
   - @Tester for testing strategy, test cases, quality assurance

Format your response as helpful advice, NOT as a delegation decision.
""",
                agent=self.crew_agent,
                expected_output="Helpful response addressing the user's request with specialist suggestions if needed"
            )

            # Execute crew
            await self.update_progress(2, 3, "Formulating response")

            crew = Crew(
                agents=[self.crew_agent],
                tasks=[crew_task],
                verbose=True,
            )

            result = crew.kickoff()

            # Extract response
            response = str(result)

            await self.update_progress(3, 3, "Complete")

            logger.info(f"[{self.name}] Generated response: {len(response)} chars")

            return TaskResult(
                success=True,
                output=response,
                structured_data={
                    "task_type": task.task_type.value,
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


# Legacy delegation logic (DEPRECATED - kept for reference)
# In new architecture, delegation happens via Router when users @mention specialists
"""
OLD DELEGATION FLOW (no longer used):

1. Team Leader analyzes message
2. Decides which specialist (BA/Dev/Tester)
3. Publishes AGENT_ROUTING event
4. Specialist consumes and processes

NEW FLOW:

1. User sends message (no @mention) → Router sends to Team Leader
2. Team Leader responds with guidance, suggests "@BusinessAnalyst for requirements"
3. User sends "@BusinessAnalyst create PRD" → Router sends directly to BA
4. BA processes and responds

This is simpler and gives users control over routing.
"""
