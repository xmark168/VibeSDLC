"""Agent Task Queue - High-level API for task management.

Provides a simple queue-like interface that hides Kafka complexity.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from app.kafka.producer import get_kafka_producer
from app.kafka.event_schemas import (
    AgentTaskCompletedEvent,
    AgentTaskFailedEvent,
    AgentTaskCancelledEvent,
    AgentTaskProgressEvent,
    AgentTaskStartedEvent,
    KafkaTopics,
)

logger = logging.getLogger(__name__)


class AgentTaskQueue:
    """High-level task queue API for agents.

    Provides simple methods to manage tasks without dealing with Kafka directly.

    Example:
        queue = AgentTaskQueue(agent_id, agent_name, project_id)

        # Report task started
        await queue.start_task(task_id, execution_id)

        # Report progress
        await queue.report_progress(task_id, 50, "Halfway done", 5, 10)

        # Complete task
        await queue.complete_task(task_id, {"files": 5}, duration=120)
    """

    def __init__(
        self,
        agent_id: UUID,
        agent_name: str,
        project_id: Optional[UUID] = None
    ):
        """Initialize task queue for an agent.

        Args:
            agent_id: Agent's UUID
            agent_name: Agent's human-readable name
            project_id: Optional project ID
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.project_id = project_id
        self._producer = None

    async def _get_producer(self):
        """Get or create Kafka producer."""
        if not self._producer:
            self._producer = await get_kafka_producer()
        return self._producer

    async def start_task(
        self,
        task_id: UUID,
        execution_id: UUID,
        started_at: Optional[datetime] = None
    ) -> bool:
        """Publish task started event.

        Args:
            task_id: Task UUID
            execution_id: Execution UUID
            started_at: Optional start time (defaults to now)

        Returns:
            True if published successfully
        """
        try:
            producer = await self._get_producer()

            event = AgentTaskStartedEvent(
                event_id=str(uuid4()),
                task_id=task_id,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                execution_id=execution_id,
                started_at=started_at or datetime.now(timezone.utc),
                project_id=self.project_id,
            )

            success = await producer.publish(KafkaTopics.AGENT_TASKS, event)
            if success:
                logger.info(f"Task {task_id} started by {self.agent_name}")
            return success

        except Exception as e:
            logger.error(f"Failed to publish task started: {e}")
            return False

    async def report_progress(
        self,
        task_id: UUID,
        progress_percentage: int,
        current_step: str,
        steps_completed: int,
        total_steps: int,
        execution_id: Optional[UUID] = None,
        estimated_completion: Optional[datetime] = None
    ) -> bool:
        """Report task progress.

        Args:
            task_id: Task UUID
            progress_percentage: Progress 0-100
            current_step: Description of current step
            steps_completed: Number of completed steps
            total_steps: Total number of steps
            execution_id: Optional execution UUID
            estimated_completion: Optional ETA

        Returns:
            True if published successfully
        """
        try:
            producer = await self._get_producer()

            event = AgentTaskProgressEvent(
                event_id=str(uuid4()),
                task_id=task_id,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                execution_id=execution_id or uuid4(),
                progress_percentage=min(100, max(0, progress_percentage)),
                current_step=current_step,
                steps_completed=steps_completed,
                total_steps=total_steps,
                estimated_completion=estimated_completion,
                project_id=self.project_id,
            )

            success = await producer.publish(KafkaTopics.AGENT_TASKS, event)
            if success:
                logger.debug(
                    f"Task {task_id} progress: {progress_percentage}% - {current_step}"
                )
            return success

        except Exception as e:
            logger.error(f"Failed to publish task progress: {e}")
            return False

    async def complete_task(
        self,
        task_id: UUID,
        execution_id: UUID,
        result: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None,
        duration_seconds: int = 0,
        completed_at: Optional[datetime] = None
    ) -> bool:
        """Mark task as completed.

        Args:
            task_id: Task UUID
            execution_id: Execution UUID
            result: Optional task result data
            artifacts: Optional artifacts (files, PRs, etc.)
            duration_seconds: Task duration in seconds
            completed_at: Optional completion time (defaults to now)

        Returns:
            True if published successfully
        """
        try:
            producer = await self._get_producer()

            event = AgentTaskCompletedEvent(
                event_id=str(uuid4()),
                task_id=task_id,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                execution_id=execution_id,
                completed_at=completed_at or datetime.now(timezone.utc),
                duration_seconds=duration_seconds,
                result=result,
                artifacts=artifacts,
                project_id=self.project_id,
            )

            success = await producer.publish(KafkaTopics.AGENT_TASKS, event)
            if success:
                logger.info(
                    f"Task {task_id} completed by {self.agent_name} "
                    f"(duration: {duration_seconds}s)"
                )
            return success

        except Exception as e:
            logger.error(f"Failed to publish task completed: {e}")
            return False

    async def fail_task(
        self,
        task_id: UUID,
        execution_id: UUID,
        error_message: str,
        error_type: Optional[str] = None,
        retry_count: int = 0,
        can_retry: bool = True,
        failed_at: Optional[datetime] = None
    ) -> bool:
        """Mark task as failed.

        Args:
            task_id: Task UUID
            execution_id: Execution UUID
            error_message: Error description
            error_type: Optional error type/category
            retry_count: Number of retry attempts
            can_retry: Whether task can be retried
            failed_at: Optional failure time (defaults to now)

        Returns:
            True if published successfully
        """
        try:
            producer = await self._get_producer()

            event = AgentTaskFailedEvent(
                event_id=str(uuid4()),
                task_id=task_id,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                execution_id=execution_id,
                failed_at=failed_at or datetime.now(timezone.utc),
                error_message=error_message,
                error_type=error_type,
                retry_count=retry_count,
                can_retry=can_retry,
                project_id=self.project_id,
            )

            success = await producer.publish(KafkaTopics.AGENT_TASKS, event)
            if success:
                logger.error(
                    f"Task {task_id} failed by {self.agent_name}: {error_message}"
                )
            return success

        except Exception as e:
            logger.error(f"Failed to publish task failed: {e}")
            return False

    async def cancel_task(
        self,
        task_id: UUID,
        cancelled_by: str,
        reason: Optional[str] = None,
        cancelled_at: Optional[datetime] = None
    ) -> bool:
        """Cancel a task.

        Args:
            task_id: Task UUID
            cancelled_by: Who cancelled (user_id or agent_name)
            reason: Optional cancellation reason
            cancelled_at: Optional cancellation time (defaults to now)

        Returns:
            True if published successfully
        """
        try:
            producer = await self._get_producer()

            event = AgentTaskCancelledEvent(
                event_id=str(uuid4()),
                task_id=task_id,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                cancelled_by=cancelled_by,
                cancelled_at=cancelled_at or datetime.now(timezone.utc),
                reason=reason,
                project_id=self.project_id,
            )

            success = await producer.publish(KafkaTopics.AGENT_TASKS, event)
            if success:
                logger.info(f"Task {task_id} cancelled by {cancelled_by}")
            return success

        except Exception as e:
            logger.error(f"Failed to publish task cancelled: {e}")
            return False
