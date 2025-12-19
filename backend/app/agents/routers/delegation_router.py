
"""Router for Delegation Router."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.kafka.event_schemas import AgentTaskType, BaseKafkaEvent
from app.kafka.producer import KafkaProducer
from app.models import Agent, Project
from app.core.db import engine
from app.agents.routers.base import BaseEventRouter

logger = logging.getLogger(__name__)

class DelegationRouter(BaseEventRouter):
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "delegation.request"
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        project_id = event_dict.get("project_id")
        target_role = event_dict.get("target_role")
        
        if not project_id or not target_role:
            self.logger.error("Delegation request missing project_id or target_role")
            return
        
        if isinstance(project_id, str):
            project_id = UUID(project_id)
        
        agent = await self._find_best_agent(project_id, target_role)
        
        if not agent:
            self.logger.error(f"No agent found for role {target_role} in project {project_id}")
            await self._handle_delegation_failure(
                event_dict=event_dict,
                project_id=project_id,
                target_role=target_role,
                reason="agent_not_found"
            )
            return
        
        producer = await get_kafka_producer()
        
        delegation_context = event_dict.get("context", {})
        delegation_content = event_dict.get("content", "")
        
        if "content" not in delegation_context:
            delegation_context["content"] = delegation_content
        
        task_event = RouterTaskEvent(
            event_type="router.task.dispatched",
            task_id=uuid4(),
            task_type=event_dict.get("task_type", AgentTaskType.MESSAGE),
            agent_id=agent.id,
            agent_role=target_role,
            source_event_type=event_dict.get("source_event_type"),
            source_event_id=event_dict.get("source_event_id"),
            routing_reason=f"delegation_from_{event_dict.get('delegating_agent_name')}",
            priority=event_dict.get("priority", "high"),
            project_id=str(project_id),
            user_id=event_dict.get("user_id"),
            context=delegation_context
        )
        
        await producer.publish(
            topic=KafkaTopics.AGENT_TASKS,
            event=task_event
        )
        
        await self._update_active_agent(project_id, agent.id)
        
        self.logger.info(f"[DelegationRouter] Delegated to {agent.human_name} (role={target_role}) for project {project_id}")
    
    async def _find_best_agent(self, project_id: UUID, role_type: str) -> Optional[Agent]:
        with Session(engine) as session:
            agents = session.exec(
                select(Agent).where(
                    Agent.project_id == project_id,
                    Agent.role_type == role_type,
                    Agent.status.not_in(["terminated", "stopped", "error"])
                )
            ).all()
            if not agents:
                self.logger.warning(f"[DelegationRouter] No agents found for role '{role_type}' in project {project_id}")
                return None
            
            self.logger.info(
                f"[DelegationRouter] Found {len(agents)} agents for role '{role_type}': "
                f"{[(str(a.id), a.human_name, a.status) for a in agents]}"
            )
            
            idle_agents = [a for a in agents if a.status == "idle"]
            if idle_agents:
                selected = idle_agents[0]
                self.logger.info(f"[DelegationRouter] Selected idle agent: {selected.human_name} (id={selected.id})")
                return selected
            
            selected = agents[0]
            self.logger.info(f"[DelegationRouter] Selected busy agent: {selected.human_name} (id={selected.id})")
            return selected
    
    async def _update_active_agent(self, project_id: UUID, agent_id: UUID) -> None:
        with Session(engine) as session:
            project = session.get(Project, project_id)
            if project:
                project.active_agent_id = agent_id
                project.active_agent_updated_at = datetime.now(timezone.utc)
                session.add(project)
                session.commit()
    async def _handle_delegation_failure(
        self,
        event_dict: Dict[str, Any],
        project_id: UUID,
        target_role: str,
        reason: str
    ) -> None:
        """Handle delegation failure - send error back to delegating agent."""
        delegating_agent_id = event_dict.get("delegating_agent_id")
        delegating_agent_name = event_dict.get("delegating_agent_name")
        
        if not delegating_agent_id:
            self.logger.error("Cannot handle delegation failure: delegating_agent_id missing")
            return
        
        if isinstance(delegating_agent_id, str):
            delegating_agent_id = UUID(delegating_agent_id)
        
        role_names = {
            "business_analyst": "Business Analyst",
            "developer": "Developer",
            "tester": "Tester",
            "architect": "Architect"
        }
        role_display = role_names.get(target_role, target_role)
        
        error_message = (
            f"Xin lỗi, hiện tại không có {role_display} nào available trong dự án này. "
            f"Tôi sẽ cố gắng giúp bạn trực tiếp! 💪"
        )
        
        producer = await get_kafka_producer()
        
        error_task = RouterTaskEvent(
            event_type="router.task.dispatched",
            task_id=uuid4(),
            task_type=AgentTaskType.MESSAGE,
            agent_id=delegating_agent_id,
            agent_role=event_dict.get("delegating_agent_role", "team_leader"),
            source_event_type=event_dict.get("source_event_type"),
            source_event_id=event_dict.get("source_event_id"),
            routing_reason=f"delegation_failed:{target_role}:{reason}",
            priority="high",
            project_id=project_id,
            user_id=event_dict.get("user_id"),
            context={
                **event_dict.get("context", {}),
                "delegation_failed": True,
                "target_role": target_role,
                "failure_reason": reason,
                "error_message": error_message,
                "original_content": event_dict.get("content"),
            }
        )
        
        await producer.publish(
            topic=KafkaTopics.AGENT_TASKS,
            event=error_task
        )
