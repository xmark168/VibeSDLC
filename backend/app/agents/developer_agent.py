"""Developer Agent using CrewAI for VibeSDLC"""

import logging
import asyncio
import time
from datetime import datetime
from crewai import Agent, Task, Crew
from app.kafka.schemas import AgentTask, AgentResponse, AgentTaskStatus, AgentTaskType
from app.kafka.producer import kafka_producer
from app.kafka.consumer import agent_task_consumer
from app.kafka.topics import KafkaTopics

logger = logging.getLogger(__name__)


class DeveloperAgent:
    """Developer Agent that processes tasks from Kafka"""

    def __init__(self):
        self.agent_id = "developer_001"
        self.agent_type = "developer"
        self.crew_agent = None
        self._initialize_crew_agent()

    def _initialize_crew_agent(self):
        """Initialize CrewAI agent"""
        self.crew_agent = Agent(
            role="Software Developer",
            goal="Write clean, efficient, and well-documented code",
            backstory="""You are an experienced software developer with expertise in
            Python, FastAPI, and modern web development. You excel at writing clean code,
            following best practices, and creating maintainable solutions.""",
            verbose=True,
            allow_delegation=False
        )
        logger.info(f"Developer agent '{self.agent_id}' initialized")

    async def handle_task(self, task_data: dict):
        """Handle incoming task from Kafka"""
        try:
            # Parse task
            task = AgentTask(**task_data)
            logger.info(f"Agent {self.agent_id} received task: {task.task_id} (type: {task.task_type})")

            start_time = time.time()

            # Process based on task type
            if task.task_type == AgentTaskType.HELLO:
                result = await self._handle_hello_task(task)
            elif task.task_type == AgentTaskType.ANALYZE_STORY:
                result = await self._handle_analyze_story_task(task)
            elif task.task_type == AgentTaskType.GENERATE_CODE:
                result = await self._handle_generate_code_task(task)
            else:
                result = {"message": f"Unknown task type: {task.task_type}"}

            execution_time = int((time.time() - start_time) * 1000)

            # Send response back to Kafka
            response = AgentResponse(
                task_id=task.task_id,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=AgentTaskStatus.COMPLETED,
                result=result,
                completed_at=datetime.utcnow(),
                execution_time_ms=execution_time
            )

            kafka_producer.send_agent_response(response)
            logger.info(f"Task {task.task_id} completed in {execution_time}ms")

        except Exception as e:
            logger.error(f"Error handling task: {e}")
            # Send error response
            response = AgentResponse(
                task_id=task_data.get("task_id", "unknown"),
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=AgentTaskStatus.FAILED,
                result={},
                error=str(e),
                completed_at=datetime.utcnow()
            )
            kafka_producer.send_agent_response(response)

    async def _handle_hello_task(self, task: AgentTask) -> dict:
        """Handle simple hello task"""
        message = task.payload.get("message", "Hello!")

        # Create a simple CrewAI task
        crew_task = Task(
            description=f"Respond to this greeting message: '{message}'",
            agent=self.crew_agent,
            expected_output="A friendly greeting response"
        )

        # Execute the task with CrewAI
        crew = Crew(
            agents=[self.crew_agent],
            tasks=[crew_task],
            verbose=True
        )

        # Run the crew (this might take a moment)
        result = crew.kickoff()

        return {
            "message": f"Hello! I'm {self.agent_id}, a developer agent powered by CrewAI.",
            "greeting": message,
            "crew_response": str(result),
            "status": "ready_to_code"
        }

    async def _handle_analyze_story_task(self, task: AgentTask) -> dict:
        """Handle story analysis task"""
        story_data = task.payload.get("story", {})
        story_title = story_data.get("title", "Untitled Story")

        crew_task = Task(
            description=f"Analyze this user story and provide technical insights: {story_title}",
            agent=self.crew_agent,
            expected_output="Technical analysis of the user story"
        )

        crew = Crew(
            agents=[self.crew_agent],
            tasks=[crew_task],
            verbose=True
        )

        result = crew.kickoff()

        return {
            "story_id": task.story_id,
            "analysis": str(result),
            "estimated_complexity": "medium",
            "suggestions": ["Consider adding unit tests", "Document API endpoints"]
        }

    async def _handle_generate_code_task(self, task: AgentTask) -> dict:
        """Handle code generation task"""
        requirements = task.payload.get("requirements", "")

        crew_task = Task(
            description=f"Generate code based on these requirements: {requirements}",
            agent=self.crew_agent,
            expected_output="Generated code with documentation"
        )

        crew = Crew(
            agents=[self.crew_agent],
            tasks=[crew_task],
            verbose=True
        )

        result = crew.kickoff()

        return {
            "code": str(result),
            "language": "python",
            "documentation": "Generated code with best practices"
        }

    async def start(self):
        """Start the agent and begin consuming tasks"""
        logger.info(f"Starting developer agent: {self.agent_id}")

        # Register task handler
        agent_task_consumer.register_handler(
            KafkaTopics.AGENT_TASKS,
            self.handle_task
        )

        # Initialize consumer
        agent_task_consumer.initialize([KafkaTopics.AGENT_TASKS])

        # Start consuming
        await agent_task_consumer.start_consuming()


# Global developer agent instance
developer_agent = DeveloperAgent()
