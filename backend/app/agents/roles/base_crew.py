"""Base agent crew abstract class with Kafka integration.

This module provides a foundation for all agent crews with:
- YAML configuration loading
- CrewAI Crew creation
- Kafka event publishing (responses, status updates, routing)
- Common execution patterns
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import yaml
from crewai import Agent, Crew, Process, Task

from app.kafka.producer import get_kafka_producer
from app.kafka.event_schemas import (
    AgentResponseEvent,
    AgentRoutingEvent,
    AgentStatusEvent,
    AgentStatusType,
    KafkaTopics,
)

logger = logging.getLogger(__name__)


class BaseAgentCrew(ABC):
    """Abstract base class for modular agent crews.

    Each crew module should inherit from this class and implement:
    - create_agent(): Define the CrewAI agent
    - create_tasks(): Define the crew's tasks
    - execute(): Execute the crew's workflow
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the crew with configuration.

        Args:
            config_path: Path to crew's config.yaml file. If None, uses default location.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config: Dict[str, Any] = {}
        self.agent: Optional[Agent] = None
        self.crew: Optional[Crew] = None
        self.execution_id: Optional[UUID] = None
        self._load_config()

    @property
    @abstractmethod
    def crew_name(self) -> str:
        """Return the unique name of this crew."""
        pass

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the agent type (e.g., 'team_leader', 'business_analyst')."""
        pass

    def _get_default_config_path(self) -> Path:
        """Get default config path based on crew module location."""
        # Default: look for config.yaml in the same directory as the crew module
        module_path = Path(__file__).parent / self.agent_type / "config.yaml"
        return module_path

    def _load_config(self) -> None:
        """Load crew configuration from YAML file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"Loaded config for {self.crew_name} from {self.config_path}")
            else:
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration for the crew."""
        return {
            "agent": {
                "role": self.crew_name,
                "goal": f"Execute tasks as {self.crew_name}",
                "backstory": f"You are a {self.crew_name} agent.",
                "verbose": True,
                "allow_delegation": False,
                "model": "openai/gpt-4.1",
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            "defaults": {
                "max_iter": 15,
                "memory": True,
                "cache": True,
                "max_execution_time": 300,
            }
        }

    @abstractmethod
    def create_agent(self) -> Agent:
        """Create and return the CrewAI agent for this crew.

        Returns:
            Configured CrewAI Agent instance
        """
        pass

    @abstractmethod
    def create_tasks(self, context: Dict[str, Any]) -> list[Task]:
        """Create and return the tasks for this crew.

        Args:
            context: Execution context with input data

        Returns:
            List of CrewAI Task instances
        """
        pass

    def create_crew(self, context: Dict[str, Any]) -> Crew:
        """Create the CrewAI Crew with agent and tasks.

        Args:
            context: Execution context with input data

        Returns:
            Configured CrewAI Crew instance
        """
        if self.agent is None:
            self.agent = self.create_agent()

        tasks = self.create_tasks(context)
        defaults = self.config.get("defaults", {})

        self.crew = Crew(
            agents=[self.agent],
            tasks=tasks,
            process=Process.sequential,
            verbose=defaults.get("verbose", True),
            memory=defaults.get("memory", True),
            cache=defaults.get("cache", True),
            max_rpm=defaults.get("max_rpm", 10),
        )

        return self.crew

    async def publish_status(
        self,
        status: AgentStatusType,
        current_action: Optional[str] = None,
        project_id: Optional[UUID] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Publish agent status event to Kafka.

        Args:
            status: Current agent status
            current_action: Optional action being performed
            project_id: Optional project ID
            error_message: Optional error message

        Returns:
            True if published successfully
        """
        try:
            producer = await get_kafka_producer()
            event = AgentStatusEvent(
                event_id=str(uuid4()),
                event_type=status.value,
                agent_name=self.crew_name,
                status=status,
                current_action=current_action,
                execution_id=self.execution_id,
                project_id=project_id,
                error_message=error_message,
            )
            return await producer.publish(KafkaTopics.AGENT_STATUS, event)
        except Exception as e:
            logger.error(f"Failed to publish status: {e}")
            return False

    async def publish_response(
        self,
        content: str,
        message_id: UUID,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        requires_approval: bool = False,
    ) -> bool:
        """Publish agent response event to Kafka.

        Args:
            content: Response content
            message_id: Message ID
            project_id: Optional project ID
            user_id: Optional user ID
            structured_data: Optional structured response data
            requires_approval: Whether response requires human approval

        Returns:
            True if published successfully
        """
        try:
            producer = await get_kafka_producer()
            event = AgentResponseEvent(
                event_id=str(uuid4()),
                message_id=message_id,
                agent_name=self.crew_name,
                agent_type=self.agent_type,
                content=content,
                project_id=project_id,
                user_id=user_id,
                structured_data=structured_data,
                requires_approval=requires_approval,
            )
            return await producer.publish(KafkaTopics.AGENT_RESPONSES, event)
        except Exception as e:
            logger.error(f"Failed to publish response: {e}")
            return False

    async def publish_routing(
        self,
        to_agent: str,
        delegation_reason: str,
        context: Dict[str, Any],
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> bool:
        """Publish agent routing/delegation event to Kafka.

        Args:
            to_agent: Target agent name
            delegation_reason: Reason for delegation
            context: Context to pass to target agent
            project_id: Optional project ID
            user_id: Optional user ID

        Returns:
            True if published successfully
        """
        try:
            producer = await get_kafka_producer()
            event = AgentRoutingEvent(
                event_id=str(uuid4()),
                from_agent=self.crew_name,
                to_agent=to_agent,
                delegation_reason=delegation_reason,
                context=context,
                project_id=project_id,
                user_id=user_id,
            )
            return await producer.publish(KafkaTopics.AGENT_ROUTING, event)
        except Exception as e:
            logger.error(f"Failed to publish routing: {e}")
            return False

    async def execute(
        self,
        context: Dict[str, Any],
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute the crew's workflow.

        This is the main entry point for crew execution. It:
        1. Publishes THINKING status
        2. Creates crew and tasks
        3. Executes the crew
        4. Publishes IDLE status
        5. Returns results

        Args:
            context: Execution context with input data
            project_id: Optional project ID
            user_id: Optional user ID

        Returns:
            Execution result dictionary
        """
        self.execution_id = uuid4()
        result = {"success": False, "output": "", "error": None}

        try:
            # Publish thinking status
            await self.publish_status(
                AgentStatusType.THINKING,
                current_action=f"Analyzing request",
                project_id=project_id,
            )

            # Create crew if not exists
            if self.crew is None:
                self.create_crew(context)

            # Publish acting status
            await self.publish_status(
                AgentStatusType.ACTING,
                current_action=f"Executing tasks",
                project_id=project_id,
            )

            # Execute crew in thread pool (CrewAI is sync)
            loop = asyncio.get_event_loop()
            crew_result = await loop.run_in_executor(
                None,
                lambda: self.crew.kickoff(inputs=context)
            )

            # Extract result
            if hasattr(crew_result, "raw"):
                result["output"] = crew_result.raw
            else:
                result["output"] = str(crew_result)

            result["success"] = True

            # Publish idle status
            await self.publish_status(
                AgentStatusType.IDLE,
                project_id=project_id,
            )

            logger.info(f"{self.crew_name} execution completed successfully")

        except Exception as e:
            logger.error(f"{self.crew_name} execution failed: {e}", exc_info=True)
            result["error"] = str(e)

            # Publish error status
            await self.publish_status(
                AgentStatusType.ERROR,
                error_message=str(e),
                project_id=project_id,
            )

        return result

    def reset(self) -> None:
        """Reset crew state for new execution."""
        self.crew = None
        self.execution_id = None
