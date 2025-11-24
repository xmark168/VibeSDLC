"""Base Agent Class - Abstracts Kafka complexity from agent implementations.

This is the new simplified agent architecture where:
- Agents inherit from BaseAgent
- Implement handle_task() method
- Kafka consumer/producer logic is hidden
- Simple API: message_user() for all communications
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from app.kafka.producer import KafkaProducer, get_kafka_producer
from app.kafka.event_schemas import (
    AgentEvent,
    AgentResponseEvent,
    AgentProgressEvent,
    AgentTaskType,
    KafkaTopics,
    RouterTaskEvent,
)
from app.models import Agent as AgentModel, AgentStatus
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


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
    success: bool
    output: str  
    structured_data: Optional[Dict[str, Any]] = None  
    requires_approval: bool = False  
    error_message: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Architecture:
    - Kafka consumer/producer logic hidden from subclasses
    - Agents only implement handle_task()
    - Helpers for progress tracking and publishing
    """

    def __init__(self, agent_model: AgentModel, **kwargs):
        """Initialize base agent.
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
        self._current_execution_id: Optional[UUID] = None
        
        # Execution tracking
        self._execution_start_time: Optional[Any] = None  # datetime object
        self._execution_events: list = []  # List of events for current execution

        # Kafka producer (lazy init)
        self._producer: Optional[KafkaProducer] = None

        # Consumer will be created by start()
        self._consumer = None

        # Task queue for sequential processing
        self._task_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self._queue_running: bool = False
        self._queue_worker_task: Optional[asyncio.Task] = None

        logger.info(f"Initialized {self.role_type} agent: {self.name} ({self.agent_id})")

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
                await self.message_user("progress", "Processing...", {"step": 1, "total": 2})
                result = await self._process(task.content)
                await self.message_user("progress", "Complete", {"step": 2, "total": 2})
                
                return TaskResult(
                    success=True,
                    output=result,
                    structured_data={"key": "value"}
                )
        """
        pass

    async def message_user(
        self,
        event_type: str,
        content: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Send message/event to user.
        
        Args:
            event_type: Event type (thinking, tool_call, progress, response)
            content: Message content
            details: Additional structured data
            **kwargs: Extra metadata
        """
        if not self._current_task_id:
            logger.warning(f"[{self.name}] Cannot send message: no active task")
            return

        try:
            producer = await self._get_producer()


            event = AgentEvent(
                event_type=f"agent.{event_type}",
                agent_name=self.name,
                agent_id=str(self.agent_id),
                project_id=self.project_id,
                execution_id=self._current_execution_id,
                task_id=self._current_task_id,
                content=content,
                details=details or {},
                metadata={
                    "agent_type": self.role_type,
                    "agent_execution_id": str(self._current_execution_id) if self._current_execution_id else None,
                    **kwargs
                }
            )


            await producer.publish(
                topic=KafkaTopics.AGENT_EVENTS,
                event=event,
            )

            logger.info(f"[{self.name}] {event_type}: {content[:100]}")

        except Exception as e:
            logger.error(f"[{self.name}] Failed to send message: {e}")
    
    async def start_execution(self) -> None:
        """Emit: agent.messaging.start - Notify that agent began execution"""
        await self.message_user("thinking", f"{self.name} is starting...")
    
    async def emit_tool(self, tool: str, action: str, state: str = "started", **details) -> None:
        """Emit: agent.messaging.tool_call - Track tool execution
        
        Args:
            tool: Tool name (e.g., "read_file", "web_search")
            action: Human-readable action (e.g., "Reading main.py")
            state: "started", "completed", or "failed"
            **details: Additional tool details (input, output, error)
        """
        await self.message_user("tool_call", action, {"tool": tool, "state": state, **details})
    
    async def emit_message(self, content: str, message_type: str = "text", data: Any = None) -> None:
        """Emit: agent.messaging.response - Send agent message (saves to DB)
        
        Args:
            content: Message content
            message_type: "text", "prd", "backlog", "code", etc.
            data: Structured data for rich messages
        """
        await self.message_user("response", content, {"message_type": message_type, "data": data})
    
    async def finish_execution(self, summary: str = "Task completed") -> None:
        """Emit: agent.messaging.finish - Notify execution is complete"""

        await self.message_user("completed", summary)



    async def _create_execution_record(self, task: "TaskContext") -> UUID:
        """Create AgentExecution record in database"""
        from app.services import ExecutionService
        from sqlmodel import Session
        from app.core.db import engine
        
        # Use ExecutionService for async-safe execution creation
        with Session(engine) as db:
            execution_service = ExecutionService(db)
            execution_id = await execution_service.create_execution(
                project_id=self.project_id,
                agent_name=self.name,
                agent_type=self.role_type,
                trigger_message_id=task.message_id if hasattr(task, 'message_id') else None,
                user_id=task.user_id if hasattr(task, 'user_id') else None,
                task_type=task.task_type.value if hasattr(task, 'task_type') and task.task_type else None,
                task_content_preview=task.content[:200] if task.content else None,
            )
        

        return execution_id
    
    async def _complete_execution_record(
        self, 
        result: Optional["TaskResult"] = None, 
        error: Optional[str] = None,
        error_traceback: Optional[str] = None,
        success: bool = True
    ):
        """Update execution record with completion data"""
        if not self._current_execution_id:
            return
        
        from app.services import ExecutionService
        from sqlmodel import Session
        from app.core.db import engine
        
        duration_ms = None
        if self._execution_start_time:
            duration_ms = int(
                (datetime.now(timezone.utc) - self._execution_start_time).total_seconds() * 1000
            )
        
        # Use ExecutionService for async-safe execution completion
        with Session(engine) as db:
            execution_service = ExecutionService(db)
            await execution_service.complete_execution(
                execution_id=self._current_execution_id,
                success=success,
                output=result.output if result else None,
                structured_data=result.structured_data if result else None,
                error=error,
                error_traceback=error_traceback,
                events=self._execution_events,
                duration_ms=duration_ms
            )
        
        logger.info(
            f"[{self.name}] Execution {self._current_execution_id} "
            f"{'completed' if success else 'failed'} in {duration_ms}ms with {len(self._execution_events)} events"
        )

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
        """Execute a single task (called by worker loop) with execution tracking.

        This is the actual task execution logic. It:
        1. Converts RouterTaskEvent → TaskContext
        2. Creates AgentExecution record
        3. Calls agent's handle_task()
        4. Updates execution record with result
        5. Publishes response

        Args:
            task_data: RouterTaskEvent as dict
        """
        try:
            # Extract task info
            task_id = task_data.get("task_id")
            self._current_task_id = task_id
            
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
           
            # Create execution record in database
            self._current_execution_id = await self._create_execution_record(task)
            self._execution_start_time = datetime.now(timezone.utc)
            self._execution_events.clear()

            logger.info(
                f"[{self.name}] Processing task {task_id} (execution={self._current_execution_id}): "
                f"type={task.task_type}, reason={task.routing_reason}"
            )

            # Update state to busy
            self.state = AgentStatus.busy
            
            # Emit "thinking" status IMMEDIATELY so frontend shows indicator right away
            await self.message_user("thinking", f"Processing request...")

            task_failed = False
            try:
                # Notify user that agent is thinking/processing
                await self.message_user("thinking", f"Processing {task.task_type.value} request")
                
                # Call agent's implementation
                result = await self.handle_task(task)
                
                # Auto-send response message if agent returned output
                if result.success and result.output:

                    await self.emit_message(
                        content=result.output,
                        message_type=result.structured_data.get("message_type", "text") if result.structured_data else "text",
                        data=result.structured_data
                    )
                
                # Update execution record with success
                await self._complete_execution_record(result=result, success=True)
                
                # Update statistics
                self.total_executions += 1
                if result.success:
                    self.successful_executions += 1
                else:
                    self.failed_executions += 1
                
                # Emit finish signal

                if result.success:
                    await self.finish_execution("Task completed successfully")
                else:
                    await self.finish_execution(f"Task completed with issues: {result.error_message or 'Unknown'}")
                
            except Exception as e:
                task_failed = True
                
                # Emit error status to frontend
                await self.message_user("error", f"Task failed: {str(e)}", {
                    "error_type": type(e).__name__
                })
                
                # Update execution record with failure
                await self._complete_execution_record(
                    error=str(e),
                    error_traceback=traceback.format_exc(),
                    success=False
                )
                
                # Emit finish signal with error

                await self.finish_execution(f"Task failed: {str(e)[:100]}")
                
                raise  # Re-raise to let outer handler deal with it
            
            finally:
                # Return to idle
                self.state = AgentStatus.idle
                
                # Emit "idle" status to clear frontend indicator (only if no error)
                if not task_failed:
                    await self.message_user("idle", "Task completed")

            # Log completion (only if task didn't raise exception)
            if not task_failed:
                if result   .success:
                    pass
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
