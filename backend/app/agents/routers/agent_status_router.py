
"""Router for AgentStatus Router."""

import logging
from typing import Any, Dict


from app.kafka.event_schemas import BaseKafkaEvent
from app.kafka.producer import KafkaProducer
from app.agents.routers.base import BaseEventRouter

logger = logging.getLogger(__name__)

class AgentStatusRouter(BaseEventRouter):
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        return event_type.startswith("agent.")

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        agent_name = event_dict.get("agent_name", "unknown")
        status = event_dict.get("status", "unknown")
        self.logger.debug(f"Agent '{agent_name}' status: {status}")
