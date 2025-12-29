
"""Base event router class."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from app.kafka.event_schemas import (
    AgentTaskType,
    BaseKafkaEvent,
    RouterTaskEvent,
    KafkaTopics,
)
from app.kafka.producer import KafkaProducer

logger = logging.getLogger(__name__)

class BaseEventRouter(ABC):
    def __init__(self, producer: KafkaProducer):
        self.producer = producer
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        pass
    @abstractmethod
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        pass
    async def publish_task(
        self,
        agent_id: UUID,
        task_type: "AgentTaskType",
        source_event: BaseKafkaEvent | Dict[str, Any],
        routing_reason: str,
        priority: str = "medium",
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publish a RouterTaskEvent to AGENT_TASKS topic."""
        event_dict = source_event if isinstance(source_event, dict) else source_event.model_dump()

        context = {
            **event_dict,
            **(additional_context or {}),
        }

        task = RouterTaskEvent(
            task_id=uuid4(),
            task_type=task_type,
            agent_id=agent_id,
            source_event_type=event_dict.get("event_type", "unknown"),
            source_event_id=event_dict.get("event_id", "unknown"),
            routing_reason=routing_reason,
            priority=priority,
            project_id=event_dict.get("project_id"),
            user_id=event_dict.get("user_id"),
            context=context,
        )

        await self.producer.publish(
            topic=KafkaTopics.AGENT_TASKS,
            event=task,
        )

        self.logger.info(
            f"Published task {task.task_id} to agent {agent_id} "
            f"(reason: {routing_reason})"
        )

        await self._mark_message_delivered(event_dict)

    async def _mark_message_delivered(self, event_dict: Dict[str, Any]) -> None:
        message_id = event_dict.get("message_id")
        project_id = event_dict.get("project_id")
        if not message_id or not project_id:
            self.logger.debug("No message_id or project_id in event, skipping delivered broadcast")
            return
        
        try:
            from app.websocket.connection_manager import connection_manager
            
            await connection_manager.broadcast_to_project(
                project_id=str(project_id),
                message={
                    "type": "message_delivered",
                    "message_id": str(message_id),
                    "delivered_at": str(event_dict.get("timestamp"))
                }
            )
            self.logger.debug(f"Broadcasted delivered status for message {message_id}")
        except Exception as e:
            self.logger.warning(f"Failed to broadcast delivered status: {e}")
