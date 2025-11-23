"""Base Agent Class - Abstracts Kafka complexity from agent implementations.

This is the new simplified agent architecture where:
- Agents inherit from BaseAgent
- Implement handle_task() method
- Kafka consumer/producer logic is hidden
- Simple API: update_progress(), publish_response()
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

from app.kafka.producer import KafkaProducer, get_kafka_producer
from app.kafka.event_schemas import (
    AgentResponseEvent,
    AgentProgressEvent,
    AgentTaskType,
    KafkaTopics,
    RouterTaskEvent,
)
from app.models import Agent as AgentModel, AgentStatus


logger = logging.getLogger(__name__)


# ===== Data Classes =====

@dataclass
class TaskContext:
    """Context for a task assigned to an agent.

    This is a simplified view of RouterTaskEvent for agent consumption.
    Agents don't need to know about Kafka event structure.
    """

    task_id: UUID
    task_type: AgentTaskType
    priority: str
    routing_reason: str

    # Original event data (for user messages)
    message_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    content: str = ""
    message_type: str = "text"

    # Full context for advanced use
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


@dataclass
class TaskResult:
    """Result of task execution.

    Returned by agent's handle_task() method.
    """

    success: bool
    output: str  # Text response to user
    structured_data: Optional[Dict[str, Any]] = None  # Structured output (PRD, stories, etc.)
    requires_approval: bool = False  # Whether result needs user approval
    error_message: Optional[str] = None


# ===== Base Agent Class =====

class BaseAgent(ABC):
    """Abstract base class for all agents.

    New simplified architecture:
    - Kafka consumer/producer logic hidden from subclasses
    - Agents only implement handle_task()
    - Simple helpers for progress tracking and publishing

    Usage:
        class TeamLeader(BaseAgent):
            async def handle_task(self, task: TaskContext) -> TaskResult:
                await self.update_progress(1, 3, "Analyzing...")
                result = await self._analyze(task.content)
                await self.update_progress(2, 3, "Responding...")
                response = await self._respond(result)
                return TaskResult(success=True, output=response)
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize base agent.

        Args:
            agent_model: Agent database model instance
            **kwargs: Additional arguments (heartbeat_interval, max_idle_time) for compatibility
        """
        self.agent_id = agent_model.id
        self.project_id = agent_model.project_id
        self.role_type = agent_model.role_type
        self.name = agent_model.human_name
        self.agent_model = agent_model

        # For AgentPool compatibility
        self.heartbeat_interval = kwargs.get("heartbeat_interval", 30)
        self.max_idle_time = kwargs.get("max_idle_time", 300)

        # Agent state and statistics
        self.state = AgentStatus.idle  # Current agent state
        self.total_executions = 0  # Total tasks completed
        self.successful_executions = 0  # Successful tasks
        self.failed_executions = 0  # Failed tasks

        # Callbacks (for AgentPool compatibility)
        self.on_state_change = None
        self.on_execution_complete = None
        self.on_heartbeat = None

        # Current task being processed (for progress tracking)
        self._current_task_id: Optional[UUID] = None

        # Kafka producer (lazy init)
        self._producer: Optional[KafkaProducer] = None

        # Consumer will be created by start()
        self._consumer = None

        logger.info(f"Initialized {self.role_type} agent: {self.name} ({self.agent_id})")

    # ===== Abstract Method: Subclasses Must Implement =====

    @abstractmethod
    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle assigned task.

        This is the ONLY method agents need to implement.

        Args:
            task: TaskContext with task details

        Returns:
            TaskResult with output and success status

        Example:
            async def handle_task(self, task: TaskContext) -> TaskResult:
                # Extract message
                message = task.content

                # Update progress
                await self.update_progress(1, 2, "Processing...")

                # Do work
                result = await self._process(message)

                await self.update_progress(2, 2, "Complete")

                # Return result
                return TaskResult(
                    success=True,
                    output=result,
                    structured_data={"key": "value"}
                )
        """
        pass

    # ===== Public API for Agents =====

    async def update_progress(
        self,
        current_step: int,
        total_steps: int,
        message: str
    ) -> None:
        """Update task progress (publishes to Kafka automatically).

        Args:
            current_step: Current step number (1-based)
            total_steps: Total number of steps
            message: Progress message describing current step

        Example:
            await self.update_progress(1, 3, "Analyzing requirements")
            await self.update_progress(2, 3, "Generating stories")
            await self.update_progress(3, 3, "Complete")
        """
        if not self._current_task_id:
            logger.warning(f"[{self.name}] Cannot update progress: no active task")
            return

        try:
            producer = await self._get_producer()

            progress_event = AgentProgressEvent(
                agent_name=self.name,
                agent_id=str(self.agent_id),
                execution_id=self._current_task_id,
                step_number=current_step,
                total_steps=total_steps,
                step_description=message,
                status="in_progress" if current_step < total_steps else "completed",
                project_id=self.project_id,
            )

            await producer.publish(
                topic=KafkaTopics.AGENT_PROGRESS,
                event=progress_event,
            )

            logger.info(
                f"[{self.name}] Progress: {current_step}/{total_steps} - {message}"
            )
        except Exception as e:
            logger.error(f"[{self.name}] Failed to publish progress: {e}")

    async def publish_response(
        self,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None,
        requires_approval: bool = False,
        message_id: Optional[UUID] = None,
    ) -> None:
        """Publish response to user (via Kafka, abstracted).

        Args:
            content: Response text content
            structured_data: Optional structured data (PRD, stories, etc.)
            requires_approval: Whether response needs user approval
            message_id: Original message ID (if responding to message)

        Example:
            await self.publish_response(
                content="I've analyzed your requirements...",
                structured_data={"stories": [...]},
                requires_approval=True
            )
        """
        try:
            producer = await self._get_producer()

            response_event = AgentResponseEvent(
                message_id=message_id or self._current_task_id,
                task_id=self._current_task_id,  # Include task ID for tracking
                execution_id=self._current_execution_id,  # Link to activity timeline
                agent_name=self.name,
                agent_type=self.role_type,
                content=content,
                structured_data=structured_data,
                requires_approval=requires_approval,
                project_id=self.project_id,
                user_id=None,  # Will be set from context if available
            )

            await producer.publish(
                topic=KafkaTopics.AGENT_RESPONSES,
                event=response_event,
            )

            logger.info(
                f"[{self.name}] Published response: {len(content)} chars, "
                f"task_id={self._current_task_id}, execution_id={self._current_execution_id}, "
                f"approval_required={requires_approval}"
            )
        except Exception as e:
            logger.error(f"[{self.name}] Failed to publish response: {e}")

    # ===== Consumer Management (Internal) =====

    async def start(self) -> bool:
        """Start the agent's Kafka consumer and task queue worker.

        Called during agent initialization.
        
        Returns:
            True if started successfully, False otherwise
        """
        from app.agents.core.base_agent_consumer import BaseAgentInstanceConsumer

        try:
            # Start task queue worker
            self._queue_running = True
            self._queue_worker_task = asyncio.create_task(self._task_queue_worker())
            
            # Create consumer with wrapper that calls our handle_task
            self._consumer = AgentTaskConsumer(self)
            await self._consumer.start()

            logger.info(f"[{self.name}] Agent consumer and task queue started")
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Failed to start consumer: {e}")
            return False

    async def stop(self) -> None:
        """Stop the agent's Kafka consumer and task queue worker.

        Called during shutdown.
        """
        # Stop queue worker
        self._queue_running = False
        if self._queue_worker_task:
            self._queue_worker_task.cancel()
            try:
                await self._queue_worker_task
            except asyncio.CancelledError:
                pass
        
        # Stop consumer
        if self._consumer:
            await self._consumer.stop()
            logger.info(f"[{self.name}] Agent consumer and task queue stopped")

    async def health_check(self) -> dict:
        """Check if agent is healthy.
        
        Returns:
            Dict with health status: {"healthy": bool, "reason": str}
        """
        try:
            # Check if consumer is running
            if not self._consumer:
                return {
                    "healthy": False,
                    "reason": "Consumer not started"
                }
            
            # Agent is healthy if it has a consumer
            return {
                "healthy": True,
                "reason": "Consumer running"
            }
        except Exception as e:
            logger.error(f"[{self.name}] Health check failed: {e}")
            return {
                "healthy": False,
                "reason": f"Exception: {str(e)}"
            }

    # ===== Internal Methods =====

    async def _get_producer(self) -> KafkaProducer:
        """Get Kafka producer (lazy init).

        Returns:
            KafkaProducer instance
        """
        if self._producer is None:
            self._producer = await get_kafka_producer()
        return self._producer

    async def _task_queue_worker(self) -> None:
        """Worker loop that processes tasks from queue one by one.
        
        This ensures:
        - Tasks are processed sequentially (no concurrent execution)
        - No state overwrite (task_id, execution_id)
        - Proper busy status management
        """
        logger.info(f"[{self.name}] Task queue worker started")
        
        while self._queue_running:
            try:
                # Wait for next task (with timeout to check _queue_running)
                try:
                    task_data = await asyncio.wait_for(
                        self._task_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue  # Check if still running
                
                # Process task
                await self._execute_task(task_data)
                
                # Mark task as done in queue
                self._task_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info(f"[{self.name}] Task queue worker cancelled")
                break
            except Exception as e:
                logger.error(f"[{self.name}] Task queue worker error: {e}", exc_info=True)
        
        logger.info(f"[{self.name}] Task queue worker stopped")

    async def _process_router_task(self, task_data: Dict[str, Any]) -> None:
        """Enqueue task from router for processing.

        This is called by the Kafka consumer. It:
        1. Checks if queue has space
        2. Enqueues task for sequential processing
        3. Worker loop will process it

        Args:
            task_data: RouterTaskEvent as dict
        """
        task_id = task_data.get("task_id", "unknown")
        
        try:
            # Try to add to queue (non-blocking)
            self._task_queue.put_nowait(task_data)
            
            queue_size = self._task_queue.qsize()
            logger.info(
                f"[{self.name}] Task {task_id} enqueued "
                f"(queue: {queue_size}/{self._task_queue.maxsize})"
            )
            
        except asyncio.QueueFull:
            logger.error(
                f"[{self.name}] Task queue FULL! Rejecting task {task_id}. "
                f"Agent is overloaded ({self._task_queue.maxsize} tasks pending)"
            )
            # TODO: Publish task rejection event back to router

    async def _execute_task(self, task_data: Dict[str, Any]) -> None:
        """Execute a single task (called by worker loop).

        This is the actual task execution logic. It:
        1. Converts RouterTaskEvent → TaskContext
        2. Calls agent's handle_task()
        3. Publishes response

        Args:
            task_data: RouterTaskEvent as dict
        """
        try:
            # Extract task info
            task_id = task_data.get("task_id")
            self._current_task_id = task_id
            self._current_execution_id = uuid4()  # Generate execution ID for linking response to activity

            # Extract context
            context = task_data.get("context", {})

            # Create TaskContext
            task = TaskContext(
                task_id=task_id,
                task_type=AgentTaskType(task_data.get("task_type", "message")),
                priority=task_data.get("priority", "medium"),
                routing_reason=task_data.get("routing_reason", ""),
                message_id=context.get("message_id"),
                user_id=context.get("user_id"),
                project_id=context.get("project_id") or self.project_id,
                content=context.get("content", ""),
                message_type=context.get("message_type", "text"),
                context=context,
            )

            logger.info(
                f"[{self.name}] Processing task {task_id}: "
                f"type={task.task_type}, reason={task.routing_reason}"
            )

            # Update state to busy
            self.state = AgentStatus.busy

            # Call agent's implementation
            result = await self.handle_task(task)
            
            # Update statistics
            self.total_executions += 1
            if result.success:
                self.successful_executions += 1
            else:
                self.failed_executions += 1
            
            # Return to idle
            self.state = AgentStatus.idle

            # Publish response if successful
            if result.success:
                await self.publish_response(
                    content=result.output,
                    structured_data=result.structured_data,
                    requires_approval=result.requires_approval,
                    message_id=task.message_id,
                )
                logger.info(f"[{self.name}] Task {task_id} completed successfully")
            else:
                logger.error(
                    f"[{self.name}] Task {task_id} failed: {result.error_message}"
                )

        except Exception as e:
            logger.error(
                f"[{self.name}] Error processing task {task_id}: {e}",
                exc_info=True
            )
        finally:
            self._current_task_id = None
            self._current_execution_id = None


# ===== Internal Consumer Wrapper =====

class AgentTaskConsumer:
    """Internal consumer wrapper that connects BaseAgent to Kafka.

    This is an implementation detail - agents don't interact with this directly.
    """

    def __init__(self, agent: BaseAgent):
        """Initialize consumer wrapper.

        Args:
            agent: BaseAgent instance to process tasks for
        """
        self.agent = agent
        self._consumer_instance = None

    async def start(self) -> None:
        """Start consuming tasks from Kafka."""
        from app.agents.core.base_agent_consumer import BaseAgentInstanceConsumer

        # Create a dynamic consumer class that wraps the agent
        class DynamicConsumer(BaseAgentInstanceConsumer):
            def __init__(inner_self, agent_model: AgentModel, base_agent: BaseAgent):
                super().__init__(agent_model)
                inner_self.base_agent = base_agent

            async def process_task(inner_self, task_data: Dict[str, Any]) -> None:
                """Delegate to BaseAgent's _process_router_task."""
                await inner_self.base_agent._process_router_task(task_data)

        # Create consumer instance
        self._consumer_instance = DynamicConsumer(self.agent.agent_model, self.agent)

        # Start consumer
        await self._consumer_instance.start()

    async def stop(self) -> None:
        """Stop consuming tasks."""
        if self._consumer_instance:
            await self._consumer_instance.stop()
