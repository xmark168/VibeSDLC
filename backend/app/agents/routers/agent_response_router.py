
"""Router for AgentResponse Router."""

import logging
from typing import Any, Dict


from app.kafka.event_schemas import BaseKafkaEvent
from app.kafka.producer import KafkaProducer
from app.agents.routers.base import BaseEventRouter

logger = logging.getLogger(__name__)

class AgentResponseRouter(BaseEventRouter):
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "agent.response.created"

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        agent_name = event_dict.get("agent_name", "unknown")
        project_id = event_dict.get("project_id")
        self.logger.info(f"Agent '{agent_name}' responded in project {project_id}.")
