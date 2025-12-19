
"""Router for AgentMessage Router."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from sqlmodel import Session

from app.kafka.event_schemas import  BaseKafkaEvent
from app.kafka.producer import KafkaProducer
from app.models import Project
from app.core.db import engine
from app.agents.routers.base import BaseEventRouter

logger = logging.getLogger(__name__)

class AgentMessageRouter(BaseEventRouter):
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        return event_type in ["agent.response", "agent.response.created"]
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        project_id = event_dict.get("project_id")
        agent_name = event_dict.get("agent_name")
        
        if not project_id or not agent_name:
            return
        
        details = event_dict.get("details", {})
        structured_data = event_dict.get("structured_data", {})
        task_completed = details.get("task_completed") or structured_data.get("task_completed")
        is_greeting = details.get("is_greeting", False)
        
        if is_greeting:
            self.logger.debug(f"[CONTEXT_SKIP] Skipping ownership update for greeting message")
            return
        
        with Session(engine) as session:
            from app.services import AgentService
            agent_service = AgentService(session)
            
            agent = agent_service.get_by_project_and_name(
                project_id=UUID(project_id) if isinstance(project_id, str) else project_id,
                name=agent_name,
                case_sensitive=False
            )
            
            if agent:
                project = session.get(Project, agent.project_id)
                if project:
                    if task_completed:
                        previous_agent_name = agent.human_name
                        project.active_agent_id = None
                        project.active_agent_updated_at = None
                        session.add(project)
                        session.commit()
                        
                        self.logger.info(
                            f"[CONTEXT_CLEAR] Agent {previous_agent_name} completed task, "
                            f"released ownership for project {project_id}"
                        )
                        
                        await self._send_team_leader_greeting(
                            project_id, 
                            previous_agent_name
                        )
                    else:
                        project.active_agent_id = agent.id
                        project.active_agent_updated_at = datetime.now(timezone.utc)
                        session.add(project)
                        session.commit()
                        
                        self.logger.info(
                            f"[CONTEXT_UPDATE] Agent {agent.human_name} responded, "
                            f"set as active for project {project_id}"
                        )
    
    async def _send_team_leader_greeting(
        self, 
        project_id: str | UUID, 
        completed_agent_name: str
    ) -> None:
        """Send proactive greeting from Team Leader when specialist completes task.
        
        This saves message to DB and publishes through Kafka for proper ordering.
        """
        try:
            from app.services import AgentService
            from app.models import Message, AuthorType
            from app.kafka.producer import get_kafka_producer
            from app.kafka.event_schemas import AgentEvent, KafkaTopics
            
            if isinstance(project_id, str):
                project_id = UUID(project_id)
            
            with Session(engine) as session:
                agent_service = AgentService(session)
                team_leader = agent_service.get_by_project_and_role(
                    project_id=project_id,
                    role_type="team_leader"
                )
                
                if not team_leader:
                    self.logger.warning(f"[GREETING] No Team Leader found for project {project_id}")
                    return
                
                tl_human_name = team_leader.human_name
                tl_id = team_leader.id
                
                greeting = (
                    f"Tuyệt vời! {completed_agent_name} đã hoàn thành xong rồi! 🎉 "
                    f"Bạn cần mình hỗ trợ gì tiếp theo không?"
                )
                
                message_id = uuid4()
                message = Message(
                    id=message_id,
                    project_id=project_id,
                    author_type=AuthorType.AGENT,
                    agent_id=tl_id,
                    content=greeting,
                    message_type="handoff_greeting",
                    structured_data={
                        "from_agent": completed_agent_name,
                    },
                    message_metadata={
                        "agent_name": tl_human_name,
                        "greeting_type": "specialist_completion",
                    }
                )
                session.add(message)
                session.commit()
                
                self.logger.info(f"[GREETING] Saved greeting message to DB: {message_id}")
            
            producer = await get_kafka_producer()
            event = AgentEvent(
                event_type="agent.response",
                agent_name=tl_human_name,
                agent_id=str(tl_id),
                project_id=str(project_id),
                execution_id="",
                task_id="",
                content=greeting,
                details={
                    "message_id": str(message_id),
                    "message_type": "handoff_greeting",
                    "from_agent": completed_agent_name,
                    "is_greeting": True,  # Flag to skip ownership update
                },
            )
            await producer.publish(topic=KafkaTopics.AGENT_EVENTS, event=event)
            
            self.logger.info(
                f"[GREETING] Team Leader {tl_human_name} sent greeting "
                f"after {completed_agent_name} completed task"
            )
            
        except Exception as e:
            self.logger.error(f"[GREETING] Failed to send Team Leader greeting: {e}", exc_info=True)
