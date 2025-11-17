"""
Story Assistant Consumer (Business Analyst Agent)

Handles story creation, refinement, and acceptance criteria generation
"""

import logging
import uuid
from typing import Dict, Any
from uuid import UUID
from datetime import datetime

from crewai import Task, Crew

from app.crews.events.kafka_consumer import create_consumer
from app.crews.events.kafka_producer import get_kafka_producer
from app.crews.events.event_schemas import KafkaTopics, AgentResponseEvent
from app.crews.agents.business_analyst import get_business_analyst_agent

logger = logging.getLogger(__name__)


class StoryAssistantConsumer:
    """
    Business Analyst agent consumer for story-related tasks

    Capabilities:
    - Generate user stories from high-level descriptions
    - Write acceptance criteria (Given-When-Then format)
    - Refine existing stories
    - Break down epics into stories
    - Suggest story points
    """

    def __init__(self):
        self.consumer = None
        self.producer = None
        self.ba_agent = None
        self.running = False

    async def start(self):
        """Start the story assistant consumer"""
        try:
            logger.info("Starting Story Assistant (BA) Consumer...")

            # Get BA agent
            self.ba_agent = get_business_analyst_agent()

            # Get Kafka producer
            self.producer = await get_kafka_producer()

            # Create consumer
            self.consumer = await create_consumer(
                consumer_id="story_assistant_ba",
                topics=[KafkaTopics.AGENT_TASKS_BA],
                group_id="ba_agents_group",
                auto_offset_reset="latest"
            )

            # Register task handler
            self.consumer.register_handler("agent.task", self.handle_task)

            self.running = True
            logger.info("Story Assistant Consumer started successfully")

            # Start consuming
            await self.consumer.consume()

        except Exception as e:
            logger.error(f"Error starting Story Assistant Consumer: {e}")
            raise

    async def stop(self):
        """Stop the consumer"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        logger.info("Story Assistant Consumer stopped")

    async def handle_task(self, event_data: Dict[str, Any]):
        """
        Handle incoming BA tasks

        Event structure:
        {
            "task_id": UUID,
            "agent_type": "ba",
            "project_id": UUID,
            "user_message_id": UUID,
            "task_description": str,
            "context": dict
        }
        """
        try:
            task_id = UUID(event_data["task_id"])
            project_id = UUID(event_data["project_id"])
            user_message_id = UUID(event_data["user_message_id"])
            task_description = event_data["task_description"]
            context = event_data.get("context", {})

            logger.info(f"Processing BA task {task_id}: {task_description[:50]}...")

            # Determine task type and execute
            response_content, structured_data = await self.execute_task(
                task_description,
                context
            )

            # Publish response event
            response_id = uuid.uuid4()
            response_event = AgentResponseEvent(
                response_id=response_id,
                task_id=task_id,
                agent_type="ba",
                project_id=project_id,
                content=response_content,
                structured_data=structured_data,
                metadata={
                    "user_message_id": str(user_message_id),
                    "task_type": self.classify_task(task_description),
                },
                timestamp=datetime.utcnow()
            )

            await self.producer.publish_event(
                topic=KafkaTopics.AGENT_RESPONSES,
                event=response_event.model_dump(),
                key=str(project_id)
            )

            logger.info(f"BA task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Error handling BA task: {e}")
            # TODO: Publish error event or retry

    def classify_task(self, task_description: str) -> str:
        """Classify the type of BA task"""
        desc_lower = task_description.lower()

        if any(kw in desc_lower for kw in ["create story", "generate story", "new story"]):
            return "story_generation"
        elif any(kw in desc_lower for kw in ["refine", "improve", "enhance story"]):
            return "story_refinement"
        elif any(kw in desc_lower for kw in ["acceptance criteria", "given when then"]):
            return "acceptance_criteria"
        elif any(kw in desc_lower for kw in ["break down", "split", "epic"]):
            return "epic_breakdown"
        elif any(kw in desc_lower for kw in ["estimate", "story points"]):
            return "estimation"
        else:
            return "general_analysis"

    async def execute_task(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """
        Execute the BA task using CrewAI agent

        Returns: (response_content, structured_data)
        """
        task_type = self.classify_task(task_description)

        # Create appropriate task based on type
        if task_type == "story_generation":
            return await self.generate_story(task_description, context)
        elif task_type == "story_refinement":
            return await self.refine_story(task_description, context)
        elif task_type == "acceptance_criteria":
            return await self.generate_acceptance_criteria(task_description, context)
        elif task_type == "epic_breakdown":
            return await self.breakdown_epic(task_description, context)
        elif task_type == "estimation":
            return await self.estimate_story(task_description, context)
        else:
            return await self.general_analysis(task_description, context)

    async def generate_story(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Generate a user story from description"""
        try:
            # Create CrewAI task
            task = Task(
                description=f"""
                Create a well-structured user story based on this description:

                {description}

                The user story should include:
                1. Title: Clear, concise title
                2. Description: User story in format "As a [user], I want [goal], so that [benefit]"
                3. Acceptance Criteria: At least 3 testable criteria in Given-When-Then format
                4. Story Points: Estimated complexity (1, 2, 3, 5, 8, 13)
                5. Type: UserStory or EnablerStory

                Return the response in a structured format.
                """,
                expected_output="A complete user story with all required fields",
                agent=self.ba_agent,
            )

            # Execute with crew
            crew = Crew(
                agents=[self.ba_agent],
                tasks=[task],
                verbose=False
            )

            result = crew.kickoff()

            # Parse result (simplified - in production, use structured output)
            story_data = {
                "title": "Generated User Story",
                "description": str(result),
                "acceptance_criteria": "Will be parsed from agent output",
                "story_points": 5,
                "type": "UserStory",
            }

            response_content = f"I've created a user story based on your description:\n\n{result}"

            return response_content, story_data

        except Exception as e:
            logger.error(f"Error generating story: {e}")
            return f"I encountered an error while generating the story: {str(e)}", {}

    async def refine_story(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Refine an existing story"""
        try:
            task = Task(
                description=f"""
                Review and refine this user story:

                {description}

                Provide specific suggestions for:
                1. Clarity improvements
                2. Better acceptance criteria
                3. Missing edge cases
                4. Testability enhancements
                """,
                expected_output="Detailed refinement suggestions",
                agent=self.ba_agent,
            )

            crew = Crew(
                agents=[self.ba_agent],
                tasks=[task],
                verbose=False
            )

            result = crew.kickoff()

            response_content = f"Here are my suggestions to refine the story:\n\n{result}"

            return response_content, {"refinement_suggestions": str(result)}

        except Exception as e:
            logger.error(f"Error refining story: {e}")
            return f"Error refining story: {str(e)}", {}

    async def generate_acceptance_criteria(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Generate acceptance criteria for a story"""
        try:
            task = Task(
                description=f"""
                Generate comprehensive acceptance criteria for this story:

                {description}

                Use Given-When-Then format for each criterion.
                Include at least 5 different scenarios covering:
                - Happy path
                - Edge cases
                - Error conditions
                - Validation rules
                """,
                expected_output="List of acceptance criteria in Given-When-Then format",
                agent=self.ba_agent,
            )

            crew = Crew(
                agents=[self.ba_agent],
                tasks=[task],
                verbose=False
            )

            result = crew.kickoff()

            response_content = f"Here are the acceptance criteria:\n\n{result}"

            return response_content, {"acceptance_criteria": str(result)}

        except Exception as e:
            logger.error(f"Error generating acceptance criteria: {e}")
            return f"Error generating acceptance criteria: {str(e)}", {}

    async def breakdown_epic(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Break down an epic into user stories"""
        try:
            task = Task(
                description=f"""
                Break down this epic into smaller user stories:

                {description}

                For each story, provide:
                - Title
                - Brief description
                - Estimated story points
                - Dependencies (if any)

                Aim for stories that can be completed in 1-2 days.
                """,
                expected_output="List of user stories from the epic",
                agent=self.ba_agent,
            )

            crew = Crew(
                agents=[self.ba_agent],
                tasks=[task],
                verbose=False
            )

            result = crew.kickoff()

            response_content = f"I've broken down the epic into these stories:\n\n{result}"

            return response_content, {"stories": str(result)}

        except Exception as e:
            logger.error(f"Error breaking down epic: {e}")
            return f"Error breaking down epic: {str(e)}", {}

    async def estimate_story(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Estimate story points"""
        try:
            task = Task(
                description=f"""
                Estimate story points for this story:

                {description}

                Use Fibonacci scale: 1, 2, 3, 5, 8, 13

                Consider:
                - Complexity
                - Uncertainty
                - Effort required

                Provide rationale for the estimate.
                """,
                expected_output="Story point estimate with rationale",
                agent=self.ba_agent,
            )

            crew = Crew(
                agents=[self.ba_agent],
                tasks=[task],
                verbose=False
            )

            result = crew.kickoff()

            response_content = f"Story point estimation:\n\n{result}"

            return response_content, {"estimation": str(result)}

        except Exception as e:
            logger.error(f"Error estimating story: {e}")
            return f"Error estimating story: {str(e)}", {}

    async def general_analysis(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Handle general BA questions"""
        try:
            task = Task(
                description=f"""
                As a Business Analyst, help with this request:

                {description}

                Provide professional, actionable guidance.
                """,
                expected_output="Professional BA guidance",
                agent=self.ba_agent,
            )

            crew = Crew(
                agents=[self.ba_agent],
                tasks=[task],
                verbose=False
            )

            result = crew.kickoff()

            response_content = str(result)

            return response_content, {}

        except Exception as e:
            logger.error(f"Error in general analysis: {e}")
            return f"Error processing request: {str(e)}", {}


# Global instance
story_assistant_consumer = StoryAssistantConsumer()
