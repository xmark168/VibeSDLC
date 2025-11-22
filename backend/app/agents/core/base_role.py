"""Enhanced base role with lifecycle management, heartbeat, and pool support.

"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
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

# Import AgentStatus for runtime use
from app.models import AgentStatus, AgentExecution, AgentExecutionStatus

logger = logging.getLogger(__name__)


# ===== Lifecycle Logging Helpers =====

def _log_lifecycle(agent_name: str, agent_id: UUID, event: str, details: str = "") -> None:
    """Log a lifecycle event with standard format."""
    detail_str = f" - {details}" if details else ""
    logger.info(f"[LIFECYCLE] Agent {agent_name} ({agent_id}): {event}{detail_str}")


def _log_message(agent_name: str, event: str, message_id: Optional[str] = None, details: str = "") -> None:
    """Log a message event with standard format."""
    msg_str = f" message={message_id}" if message_id else ""
    detail_str = f" - {details}" if details else ""
    logger.info(f"[MESSAGE] Agent {agent_name}:{msg_str} {event}{detail_str}")


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
        self.state = AgentStatus.created
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
        if self.state != AgentStatus.created:
            logger.warning(f"Agent {self.agent_id} already started or stopped")
            return False

        try:
            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STARTING", "initializing...")
            self._set_state(AgentStatus.starting)

            # Create agent if needed
            if self.agent is None:
                _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STARTING", "creating CrewAI agent...")
                self.agent = self.create_agent()

            # Start heartbeat
            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STARTING", "starting heartbeat...")
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Start consumer
            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STARTING", "starting consumer...")
            self._consumer_task = asyncio.create_task(self._consumer_loop())

            self.started_at = datetime.now(timezone.utc)
            self._set_state(AgentStatus.idle)

            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STARTED", "ready and waiting for messages")
            return True

        except Exception as e:
            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "START_FAILED", str(e))
            logger.error(f"Failed to start agent {self.agent_id}: {e}", exc_info=True)
            self._set_state(AgentStatus.error)
            return False

    async def stop(self, graceful: bool = True) -> bool:
        """Stop the agent and cleanup resources.

        Args:
            graceful: If True, wait for current execution to finish

        Returns:
            True if stopped successfully
        """
        if self.state in [AgentStatus.stopped, AgentStatus.terminated]:
            logger.warning(f"Agent {self.agent_id} already stopped")
            return False

        try:
            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STOPPING", f"graceful={graceful}")
            self._set_state(AgentStatus.stopping)
            self._shutdown_event.set()

            # Cancel heartbeat
            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STOPPING", "stopping heartbeat...")
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass

            # Stop consumer
            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STOPPING", "stopping consumer...")
            if self._consumer_task:
                if graceful:
                    # Wait for current execution
                    _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STOPPING", "waiting for current execution to finish...")
                    await self._consumer_task
                else:
                    self._consumer_task.cancel()
                    try:
                        await self._consumer_task
                    except asyncio.CancelledError:
                        pass

            # Cleanup resources
            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STOPPING", "cleaning up resources...")
            await self._cleanup()

            self.stopped_at = datetime.now(timezone.utc)
            self._set_state(AgentStatus.stopped)

            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STOPPED", "agent terminated successfully")
            return True

        except Exception as e:
            _log_lifecycle(self.human_name or self.role_name, self.agent_id, "STOP_FAILED", str(e))
            logger.error(f"Failed to stop agent {self.agent_id}: {e}", exc_info=True)
            self._set_state(AgentStatus.error)
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
            "healthy": self.state in [AgentStatus.idle, AgentStatus.busy],
            "uptime_seconds": uptime,
            "idle_seconds": idle_time,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": self.successful_executions / self.total_executions if self.total_executions > 0 else 0,
        }

    def _set_state(self, new_state: AgentStatus) -> None:
        """Set agent state and trigger callback.

        Args:
            new_state: New agent status
        """
        old_state = self.state
        self.state = new_state

        # Log state transition with standard format
        _log_lifecycle(
            self.human_name or self.role_name,
            self.agent_id,
            "STATE_CHANGED",
            f"{old_state.value} → {new_state.value}"
        )

        # Sync to database if agent_model exists
        if self.agent_model:
            asyncio.create_task(self._sync_state_to_db(new_state))

        # Trigger callback
        if self.on_state_change:
            asyncio.create_task(self.on_state_change(self, old_state, new_state))

    async def _sync_state_to_db(self, new_state: AgentStatus) -> None:
        """Sync agent state to database.

        Args:
            new_state: New agent status to persist
        """
        try:
            from sqlmodel import Session
            from app.core.db import engine
            from app.models import Agent as AgentModel

            with Session(engine) as db_session:
                db_agent = db_session.get(AgentModel, self.agent_id)
                if db_agent:
                    db_agent.status = new_state
                    db_session.add(db_agent)
                    db_session.commit()
                    logger.debug(f"Synced agent {self.agent_id} status to DB: {new_state.value}")
                else:
                    logger.warning(f"Agent {self.agent_id} not found in database for state sync")
        except Exception as e:
            logger.error(f"Failed to sync state to database for agent {self.agent_id}: {e}", exc_info=True)

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
            AgentStatusType.IDLE if self.state == AgentStatus.idle else AgentStatusType.THINKING,
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

    # ===== Execution Persistence =====

    def _create_execution_record(
        self,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        trigger_message_id: Optional[UUID] = None,
    ) -> Optional[UUID]:
        """Create an AgentExecution record in database.

        Args:
            project_id: Project ID for the execution
            user_id: User who triggered the execution
            trigger_message_id: Message that triggered the execution

        Returns:
            Execution ID if created successfully, None otherwise
        """
        if not project_id:
            project_id = self.project_id

        if not project_id:
            logger.warning(f"Cannot create execution record without project_id for agent {self.agent_id}")
            return None

        try:
            from sqlmodel import Session
            from app.core.db import engine

            execution = AgentExecution(
                project_id=project_id,
                agent_name=self.human_name or self.role_name,
                agent_type=self.role_name,
                status=AgentExecutionStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
                trigger_message_id=trigger_message_id,
                user_id=user_id,
            )

            with Session(engine) as db_session:
                db_session.add(execution)
                db_session.commit()
                db_session.refresh(execution)

                _log_lifecycle(
                    self.human_name or self.role_name,
                    self.agent_id,
                    "EXECUTION_STARTED",
                    f"execution_id={execution.id}"
                )
                return execution.id

        except Exception as e:
            logger.error(f"Failed to create execution record: {e}", exc_info=True)
            return None

    def _update_execution_record(
        self,
        execution_id: UUID,
        success: bool,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None,
        token_used: int = 0,
    ) -> None:
        """Update an AgentExecution record with results.

        Args:
            execution_id: ID of the execution record
            success: Whether execution was successful
            result: Execution result data
            error_message: Error message if failed
            token_used: Number of tokens used
        """
        try:
            from sqlmodel import Session
            from app.core.db import engine

            with Session(engine) as db_session:
                execution = db_session.get(AgentExecution, execution_id)
                if execution:
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.status = (
                        AgentExecutionStatus.COMPLETED if success
                        else AgentExecutionStatus.FAILED
                    )

                    # Calculate duration
                    if execution.started_at:
                        duration = (execution.completed_at - execution.started_at).total_seconds() * 1000
                        execution.duration_ms = int(duration)

                    execution.token_used = token_used
                    execution.result = result
                    execution.error_message = error_message

                    db_session.add(execution)
                    db_session.commit()

                    status_str = "COMPLETED" if success else "FAILED"
                    _log_lifecycle(
                        self.human_name or self.role_name,
                        self.agent_id,
                        f"EXECUTION_{status_str}",
                        f"execution_id={execution_id}, duration={execution.duration_ms}ms"
                    )
                else:
                    logger.warning(f"Execution record {execution_id} not found for update")

        except Exception as e:
            logger.error(f"Failed to update execution record: {e}", exc_info=True)

    # ===== Execution =====

    async def execute(
        self,
        context: Dict[str, Any],
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        message_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute agent workflow.

        Args:
            context: Execution context
            project_id: Optional project ID
            user_id: Optional user ID
            message_id: Optional trigger message ID for tracking

        Returns:
            Execution result
        """
        self.execution_id = uuid4()
        self.total_executions += 1
        self.last_activity = datetime.now(timezone.utc)
        self._set_state(AgentStatus.busy)

        # Create execution record in database
        db_execution_id = self._create_execution_record(
            project_id=project_id,
            user_id=user_id,
            trigger_message_id=message_id,
        )

        result = {"success": False, "output": "", "error": None, "execution_id": str(self.execution_id)}
        error_msg = None

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

        except Exception as e:
            logger.error(f"[EXECUTION] {self.role_name} execution failed: {e}", exc_info=True)
            result["error"] = str(e)
            error_msg = str(e)
            self.failed_executions += 1

            await self._publish_status(
                AgentStatusType.ERROR,
                error_message=str(e),
                project_id=project_id,
            )

        finally:
            self._set_state(AgentStatus.idle)
            self.last_activity = datetime.now(timezone.utc)

            # Update execution record in database
            if db_execution_id:
                self._update_execution_record(
                    execution_id=db_execution_id,
                    success=result.get("success", False),
                    result=result,
                    error_message=error_msg,
                )

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
