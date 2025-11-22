"""Enhanced base role with lifecycle management, heartbeat, and pool support.

"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Callable, TYPE_CHECKING
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

if TYPE_CHECKING:
    from app.models import Agent as AgentModel
    from app.agents.core.base_agent_consumer import BaseAgentInstanceConsumer

logger = logging.getLogger(__name__)


class AgentLifecycleState(str, Enum):
    """Agent lifecycle states."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    TERMINATED = "terminated"


class BaseAgentRole(ABC):
    """Enhanced base class for agent roles with lifecycle management.

    Features:
    - Lifecycle state management (created -> running -> stopped)
    - Heartbeat mechanism for health monitoring
    - Consumer pattern support
    - Graceful shutdown
    - Resource cleanup
    - Pool management support
    """

    def __init__(
        self,
        agent_id: Optional[UUID] = None,
        agent_model: Optional["AgentModel"] = None,
        config_path: Optional[Path] = None,
        heartbeat_interval: int = 30,
        max_idle_time: int = 300,
    ):
        """Initialize the agent role.

        Args:
            agent_id: Unique agent instance ID (deprecated, use agent_model)
            agent_model: Agent database model instance (new approach)
            config_path: Path to agent config.yaml
            heartbeat_interval: Seconds between heartbeats
            max_idle_time: Max seconds idle before auto-shutdown
        """
        # Support both old and new initialization
        if agent_model:
            self.agent_id = agent_model.id
            self.agent_model = agent_model
            self.project_id = agent_model.project_id
            self.human_name = agent_model.human_name
        else:
            self.agent_id = agent_id or uuid4()
            self.agent_model = None
            self.project_id = None
            self.human_name = None

        self.config_path = config_path or self._get_default_config_path()
        self.heartbeat_interval = heartbeat_interval
        self.max_idle_time = max_idle_time

        # State management
        self.state = AgentLifecycleState.CREATED
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None

        # Execution tracking
        self.execution_id: Optional[UUID] = None
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0

        # Configuration
        self.config: Dict[str, Any] = {}
        self._load_config()

        # CrewAI components
        self.agent: Optional[Agent] = None
        self.crew: Optional[Crew] = None

        # Kafka consumer (new approach)
        self.consumer: Optional["BaseAgentInstanceConsumer"] = None

        # Async tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._consumer_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Callbacks
        self.on_heartbeat: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        self.on_execution_complete: Optional[Callable] = None

        logger.info(f"Agent {self.role_name} (ID: {self.agent_id}) created")

    # ===== Abstract Properties =====

    @property
    @abstractmethod
    def role_name(self) -> str:
        """Return the unique role name (e.g., 'TeamLeader')."""
        pass

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the agent type (e.g., 'team_leader')."""
        pass

    @property
    @abstractmethod
    def kafka_topic(self) -> str:
        """Return the Kafka topic this agent consumes from."""
        pass

    # ===== Abstract Methods =====

    @abstractmethod
    def create_agent(self) -> Agent:
        """Create and return the CrewAI agent.

        Returns:
            Configured CrewAI Agent instance
        """
        pass

    @abstractmethod
    def create_tasks(self, context: Dict[str, Any]) -> list[Task]:
        """Create tasks for execution.

        Args:
            context: Execution context

        Returns:
            List of CrewAI tasks
        """
        pass

    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message from Kafka.

        Args:
            message: Message payload

        Returns:
            Processing result
        """
        pass

    # ===== Configuration =====

    def _get_default_config_path(self) -> Path:
        """Get default config path."""
        return Path(__file__).parent.parent / "roles" / self.agent_type / "config.yaml"

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"Loaded config for {self.role_name} from {self.config_path}")
            else:
                logger.warning(f"Config not found: {self.config_path}, using defaults")
                self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "agent": {
                "role": self.role_name,
                "goal": f"Execute tasks as {self.role_name}",
                "backstory": f"You are a {self.role_name} agent.",
                "verbose": True,
                "allow_delegation": False,
                "model": "openai/gpt-4o-mini",
                "temperature": 0.3,
            },
            "defaults": {
                "max_iter": 15,
                "memory": True,
                "cache": True,
                "max_execution_time": 300,
            }
        }

    # ===== Lifecycle Management =====

    async def start(self) -> bool:
        """Start the agent and its services.

        Returns:
            True if started successfully
        """
        if self.state != AgentLifecycleState.CREATED:
            logger.warning(f"Agent {self.agent_id} already started or stopped")
            return False

        try:
            self._set_state(AgentLifecycleState.STARTING)

            # Create agent if needed
            if self.agent is None:
                self.agent = self.create_agent()

            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Start consumer
            self._consumer_task = asyncio.create_task(self._consumer_loop())

            self.started_at = datetime.now(timezone.utc)
            self._set_state(AgentLifecycleState.IDLE)

            logger.info(f"Agent {self.role_name} (ID: {self.agent_id}) started")
            return True

        except Exception as e:
            logger.error(f"Failed to start agent {self.agent_id}: {e}", exc_info=True)
            self._set_state(AgentLifecycleState.ERROR)
            return False

    async def stop(self, graceful: bool = True) -> bool:
        """Stop the agent and cleanup resources.

        Args:
            graceful: If True, wait for current execution to finish

        Returns:
            True if stopped successfully
        """
        if self.state in [AgentLifecycleState.STOPPED, AgentLifecycleState.TERMINATED]:
            logger.warning(f"Agent {self.agent_id} already stopped")
            return False

        try:
            self._set_state(AgentLifecycleState.STOPPING)
            self._shutdown_event.set()

            # Cancel heartbeat
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass

            # Stop consumer
            if self._consumer_task:
                if graceful:
                    # Wait for current execution
                    logger.info(f"Waiting for agent {self.agent_id} to finish...")
                    await self._consumer_task
                else:
                    self._consumer_task.cancel()
                    try:
                        await self._consumer_task
                    except asyncio.CancelledError:
                        pass

            # Cleanup resources
            await self._cleanup()

            self.stopped_at = datetime.now(timezone.utc)
            self._set_state(AgentLifecycleState.STOPPED)

            logger.info(f"Agent {self.role_name} (ID: {self.agent_id}) stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop agent {self.agent_id}: {e}", exc_info=True)
            self._set_state(AgentLifecycleState.ERROR)
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check.

        Returns:
            Health status dictionary
        """
        now = datetime.now(timezone.utc)
        uptime = (now - self.started_at).total_seconds() if self.started_at else 0
        idle_time = (now - self.last_activity).total_seconds() if self.last_activity else 0

        return {
            "agent_id": str(self.agent_id),
            "role_name": self.role_name,
            "state": self.state.value,
            "healthy": self.state == AgentLifecycleState.RUNNING,
            "uptime_seconds": uptime,
            "idle_seconds": idle_time,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": self.successful_executions / self.total_executions if self.total_executions > 0 else 0,
        }

    def _set_state(self, new_state: AgentLifecycleState) -> None:
        """Set agent state and trigger callback.

        Args:
            new_state: New lifecycle state
        """
        old_state = self.state
        self.state = new_state

        logger.debug(f"Agent {self.agent_id} state: {old_state} -> {new_state}")

        # Trigger callback
        if self.on_state_change:
            asyncio.create_task(self.on_state_change(self, old_state, new_state))

    # ===== Heartbeat =====

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop for monitoring."""
        while not self._shutdown_event.is_set():
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error for agent {self.agent_id}: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def _send_heartbeat(self) -> None:
        """Send heartbeat event."""
        self.last_heartbeat = datetime.now(timezone.utc)

        # Publish heartbeat status
        await self._publish_status(
            AgentStatusType.IDLE if self.state == AgentLifecycleState.IDLE else AgentStatusType.THINKING,
            current_action=f"Heartbeat - State: {self.state.value}"
        )

        # Trigger callback
        if self.on_heartbeat:
            await self.on_heartbeat(self)

        # Check for auto-shutdown
        if self.last_activity:
            idle_time = (datetime.now(timezone.utc) - self.last_activity).total_seconds()
            if idle_time > self.max_idle_time:
                logger.warning(f"Agent {self.agent_id} idle for {idle_time}s, auto-stopping")
                await self.stop()

    # ===== Consumer Loop =====

    async def _consumer_loop(self) -> None:
        """Consumer loop for processing messages.

        Creates and starts the BaseAgentInstanceConsumer if agent_model is provided.
        Falls back to placeholder behavior for backward compatibility.
        """
        if not self.agent_model:
            # Backward compatibility: placeholder loop
            logger.warning(
                f"Agent {self.agent_id} started without agent_model, "
                "consumer functionality disabled"
            )
            while not self._shutdown_event.is_set():
                try:
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    break
            return

        logger.info(f"Starting Kafka consumer for agent {self.human_name} ({self.role_name})")

        try:
            # Import here to avoid circular dependency
            from app.agents.core.base_agent_consumer import BaseAgentInstanceConsumer

            # Create consumer instance (will be created by subclass)
            self.consumer = self._create_consumer()

            if not self.consumer:
                logger.error(f"Failed to create consumer for agent {self.agent_id}")
                return

            # Start consumer
            await self.consumer.start()

            logger.info(f"Kafka consumer started for agent {self.human_name}")

            # Keep loop alive while consumer runs
            while not self._shutdown_event.is_set():
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info(f"Consumer loop cancelled for agent {self.agent_id}")
        except Exception as e:
            logger.error(f"Consumer loop error for agent {self.agent_id}: {e}", exc_info=True)
        finally:
            # Stop consumer
            if self.consumer:
                try:
                    await self.consumer.stop()
                    logger.info(f"Consumer stopped for agent {self.human_name}")
                except Exception as e:
                    logger.error(f"Error stopping consumer: {e}")

    def _create_consumer(self) -> Optional["BaseAgentInstanceConsumer"]:
        """Create the consumer instance for this agent.

        Subclasses should override this to return their specific consumer implementation.
        The consumer should extend BaseAgentInstanceConsumer and implement process_user_message().

        Returns:
            Consumer instance or None
        """
        logger.warning(
            f"Agent {self.role_name} did not implement _create_consumer(), "
            "consumer functionality will be disabled"
        )
        return None

    # ===== Execution =====

    async def execute(
        self,
        context: Dict[str, Any],
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute agent workflow.

        Args:
            context: Execution context
            project_id: Optional project ID
            user_id: Optional user ID

        Returns:
            Execution result
        """
        self.execution_id = uuid4()
        self.total_executions += 1
        self.last_activity = datetime.now(timezone.utc)
        self._set_state(AgentLifecycleState.BUSY)

        result = {"success": False, "output": "", "error": None, "execution_id": str(self.execution_id)}

        try:
            # Publish thinking status
            await self._publish_status(
                AgentStatusType.THINKING,
                current_action="Analyzing request",
                project_id=project_id,
            )

            # Create crew if needed
            if self.crew is None:
                self.crew = self._create_crew(context)

            # Publish acting status
            await self._publish_status(
                AgentStatusType.ACTING,
                current_action="Executing tasks",
                project_id=project_id,
            )

            # Execute crew
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

            if hasattr(crew_result, "pydantic") and crew_result.pydantic:
                result["pydantic"] = crew_result.pydantic

            result["success"] = True
            self.successful_executions += 1

            # Publish idle status
            await self._publish_status(
                AgentStatusType.IDLE,
                project_id=project_id,
            )

            logger.info(f"{self.role_name} execution {self.execution_id} completed")

        except Exception as e:
            logger.error(f"{self.role_name} execution failed: {e}", exc_info=True)
            result["error"] = str(e)
            self.failed_executions += 1

            await self._publish_status(
                AgentStatusType.ERROR,
                error_message=str(e),
                project_id=project_id,
            )

        finally:
            self._set_state(AgentLifecycleState.IDLE)
            self.last_activity = datetime.now(timezone.utc)

            # Trigger callback
            if self.on_execution_complete:
                await self.on_execution_complete(self, result)

        return result

    def _create_crew(self, context: Dict[str, Any]) -> Crew:
        """Create CrewAI Crew instance.

        Args:
            context: Execution context

        Returns:
            Configured Crew instance
        """
        if self.agent is None:
            self.agent = self.create_agent()

        tasks = self.create_tasks(context)
        defaults = self.config.get("defaults", {})

        return Crew(
            agents=[self.agent],
            tasks=tasks,
            process=Process.sequential,
            verbose=defaults.get("verbose", True),
            memory=defaults.get("memory", True),
            cache=defaults.get("cache", True),
            max_rpm=defaults.get("max_rpm", 10),
        )

    # ===== Kafka Publishing =====

    async def _publish_status(
        self,
        status: AgentStatusType,
        current_action: Optional[str] = None,
        project_id: Optional[UUID] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Publish agent status event.

        Args:
            status: Agent status
            current_action: Current action
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
                agent_name=self.role_name,
                agent_id=str(self.agent_id),
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

    # ===== Cleanup =====

    async def _cleanup(self) -> None:
        """Cleanup resources."""
        try:
            self.crew = None
            self.execution_id = None
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def reset(self) -> None:
        """Reset for new execution."""
        self.crew = None
        self.execution_id = None
