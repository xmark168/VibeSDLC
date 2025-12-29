
"""Router for TaskCompletion Router."""

import logging
from typing import Any, Dict
from uuid import UUID

from sqlmodel import Session

from app.kafka.event_schemas import AgentTaskType, BaseKafkaEvent
from app.kafka.producer import KafkaProducer
from app.models import Agent, Project, Story
from app.core.db import engine
from app.agents.routers.base import BaseEventRouter

logger = logging.getLogger(__name__)

class TaskCompletionRouter(BaseEventRouter):
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        
        if event_dict.get("event_type") in ["agent.response", "agent.response.created"]:
            structured_data = event_dict.get("structured_data", {})
            return structured_data.get("task_completed") == True
        
        return False
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        project_id = event_dict.get("project_id")
        agent_name = event_dict.get("agent_name")
        
        if not project_id:
            return
        
        with Session(engine) as session:
            project = session.get(
                Project,
                UUID(project_id) if isinstance(project_id, str) else project_id
            )
            
            if project and project.active_agent_id:
                agent = session.get(Agent, project.active_agent_id)
                
                project.active_agent_id = None
                project.active_agent_updated_at = None
                session.add(project)
                session.commit()
                
                self.logger.info(
                    f"[TASK_COMPLETION] Cleared conversation context for project {project_id} "
                    f"after {agent_name} completed task"
                )
                
                if agent:
                    await self._broadcast_ownership_released(
                        project_id=UUID(project_id) if isinstance(project_id, str) else project_id,
                        agent=agent,
                        reason="task_completed"
                    )
