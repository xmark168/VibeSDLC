
"""Router for UserMessage Router."""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import Session

from app.kafka.event_schemas import AgentTaskType, BaseKafkaEvent
from app.models import Agent, Project
from app.core.db import engine
from app.agents.routers.base import BaseEventRouter

logger = logging.getLogger(__name__)

class UserMessageRouter(BaseEventRouter):
    MENTION_PATTERN = re.compile(r"@(\w+)")

    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "user.message.sent"
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        project_id = event_dict.get("project_id")
        content = event_dict.get("content", "")
        message_id = event_dict.get("message_id")

        self.logger.info(f"[USER_MESSAGE_ROUTER] Routing user message {message_id} in project {project_id}")

        mentions = self.MENTION_PATTERN.findall(content)

        if mentions:
            await self._route_with_mention(event_dict, mentions[0], project_id)
        else:
            await self._route_with_context(event_dict, project_id)

    async def _route_with_context(
        self,
        event_dict: Dict[str, Any],
        project_id: UUID
    ) -> None:
        """Route based on active conversation context."""
        with Session(engine) as session:
            project = session.get(Project, project_id)
            
            if not project:
                self.logger.error(f"Project {project_id} not found!")
                return
            
            active_agent_id = project.active_agent_id
            active_updated_at = project.active_agent_updated_at
            
            if active_agent_id and active_updated_at:
                if active_updated_at.tzinfo is None:
                    active_updated_at = active_updated_at.replace(tzinfo=timezone.utc)
                
                time_since_update = datetime.now(timezone.utc) - active_updated_at
                timeout_minutes = self._get_timeout_for_project(project)
                timeout_seconds = timeout_minutes * 60
                
                if time_since_update.total_seconds() < timeout_seconds:
                    agent = session.get(Agent, active_agent_id)
                    
                    if agent:
                        connection_status = "online" if project.websocket_connected else "offline"
                        self.logger.info(
                            f"[CONTEXT_ROUTING] Routing to active agent: {agent.human_name} "
                            f"(last active {int(time_since_update.total_seconds())}s ago, "
                            f"user {connection_status}, timeout={timeout_minutes}min)"
                        )
                        
                        task_type = self._infer_task_type(event_dict, agent.role_type)
                        
                        await self.publish_task(
                            agent_id=agent.id,
                            task_type=task_type,
                            source_event=event_dict,
                            routing_reason=f"conversation_context:{agent.human_name}",
                            priority="high",
                        )
                        return
                else:
                    connection_status = "online" if project.websocket_connected else "offline"
                    self.logger.info(
                        f"[CONTEXT_ROUTING] Context expired after {timeout_minutes}min "
                        f"(user {connection_status}), clearing context"
                    )
                    await self._clear_conversation_context(session, project_id)
            
            await self._route_to_team_leader(event_dict, project_id)

    def _get_timeout_for_project(self, project: Project) -> int:
        # Fallback defaults if router_settings not initialized
        TIMEOUT_ONLINE = 30  # minutes
        TIMEOUT_OFFLINE = 60  # minutes
        GRACE_PERIOD = 300  # 5 minutes in seconds
        
        if project.websocket_connected:
            return getattr(self, 'router_settings', None) and self.router_settings.CONTEXT_TIMEOUT_ONLINE_MINUTES or TIMEOUT_ONLINE
        if project.websocket_last_seen:
            websocket_last_seen = project.websocket_last_seen
            if websocket_last_seen.tzinfo is None:
                websocket_last_seen = websocket_last_seen.replace(tzinfo=timezone.utc)
            
            offline_duration = datetime.now(timezone.utc) - websocket_last_seen
            
            grace_period = getattr(self, 'router_settings', None) and self.router_settings.GRACE_PERIOD_SECONDS or GRACE_PERIOD
            if offline_duration.total_seconds() < grace_period:
                return getattr(self, 'router_settings', None) and self.router_settings.CONTEXT_TIMEOUT_ONLINE_MINUTES or TIMEOUT_ONLINE
        
        return getattr(self, 'router_settings', None) and self.router_settings.CONTEXT_TIMEOUT_OFFLINE_MINUTES or TIMEOUT_OFFLINE

    async def _route_with_mention(
        self, event_dict: Dict[str, Any], mentioned_name: str, project_id: UUID
    ) -> None:
        """Route message to mentioned agent (one-off request, doesn't switch context)."""
        with Session(engine) as session:
            from app.services import AgentService
            agent_service = AgentService(session)
            agent = agent_service.get_by_project_and_name(
                project_id=project_id,
                name=mentioned_name,
                case_sensitive=False
            )

            if agent:
                
                task_type = self._infer_task_type(event_dict, agent.role_type)

                await self.publish_task(
                    agent_id=agent.id,
                    task_type=task_type,
                    source_event=event_dict,
                    routing_reason=f"@mention:{mentioned_name}",
                    priority="high",  # Mentions are high priority
                )
                self.logger.info(
                    f"Routed message to mentioned agent: {agent.name} ({agent.id}), "
                    f"task_type={task_type.value}"
                )
            else:
                self.logger.warning(
                    f"Mentioned agent '@{mentioned_name}' not found in project {project_id}, "
                    f"routing to Team Leader"
                )
                await self._route_to_team_leader(event_dict, project_id)

    async def _update_conversation_context(
        self,
        session: Session,
        project_id: UUID,
        agent_id: UUID
    ) -> None:
        """Update active agent in conversation context."""
        try:
            project = session.get(Project, project_id)
            if project:
                project.active_agent_id = agent_id
                project.active_agent_updated_at = datetime.now(timezone.utc)
                session.add(project)
                session.commit()
                self.logger.info(f"[CONTEXT_UPDATE] Set active agent for project {project_id}: {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to update conversation context: {e}", exc_info=True)
            session.rollback()

    async def _clear_conversation_context(
        self,
        session: Session,
        project_id: UUID
    ) -> None:
        """Clear conversation context."""
        try:
            project = session.get(Project, project_id)
            if project:
                project.active_agent_id = None
                project.active_agent_updated_at = None
                session.add(project)
                session.commit()
                self.logger.info(f"[CONTEXT_CLEAR] Cleared conversation context for project {project_id}")
        except Exception as e:
            self.logger.error(f"Failed to clear conversation context: {e}", exc_info=True)
            session.rollback()
    
    async def _broadcast_ownership_change(
        self,
        project_id: UUID,
        new_agent: Agent,
        previous_agent_id: Optional[UUID],
        reason: str
    ) -> None:
        """Broadcast conversation ownership change to all clients (MetaGPT-style)."""
        from app.websocket.connection_manager import connection_manager
        
        previous_agent = None
        previous_agent_name = None
        
        if previous_agent_id:
            try:
                with Session(engine) as session:
                    previous_agent = session.get(Agent, previous_agent_id)
                    if previous_agent:
                        previous_agent_name = previous_agent.human_name
            except Exception as e:
                self.logger.error(f"Failed to get previous agent: {e}")
        
        await connection_manager.broadcast_to_project(
            {
                "type": "conversation.ownership_changed",
                "project_id": str(project_id),
                "previous_agent_id": str(previous_agent_id) if previous_agent_id else None,
                "previous_agent_name": previous_agent_name,
                "new_agent_id": str(new_agent.id),
                "new_agent_name": new_agent.human_name,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            project_id
        )
        
        self.logger.info(
            f"[OWNERSHIP] {previous_agent_name or 'None'} → {new_agent.human_name} ({reason})"
        )
    
    async def _broadcast_ownership_released(
        self,
        project_id: UUID,
        agent: Agent,
        reason: str
    ) -> None:
        """Broadcast conversation ownership release to all clients."""
        from app.websocket.connection_manager import connection_manager
        
        await connection_manager.broadcast_to_project(
            {
                "type": "conversation.ownership_released",
                "project_id": str(project_id),
                "agent_id": str(agent.id),
                "agent_name": agent.human_name,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            project_id
        )
        
        self.logger.info(f"[OWNERSHIP] Released by {agent.human_name} ({reason})")

    async def _route_to_team_leader(
        self, event_dict: Dict[str, Any], project_id: UUID
    ) -> None:
        """Route message to Team Leader (default behavior)."""
        with Session(engine) as session:
            from app.services import AgentService
            agent_service = AgentService(session)
            team_leader = agent_service.get_by_project_and_role(
                project_id=project_id,
                role_type="team_leader"
            )

            if team_leader:
                await self.publish_task(
                    agent_id=team_leader.id,
                    task_type=AgentTaskType.MESSAGE,
                    source_event=event_dict,
                    routing_reason="no_mention_default_team_leader",
                    priority="medium",
                )
                self.logger.info(f"Routed message to Team Leader: {team_leader.name} ({team_leader.id})")
            else:
                self.logger.error(f"No Team Leader found in project {project_id}, cannot route message!")

    def _infer_task_type(self, event_dict: Dict[str, Any], agent_role: str = None) -> AgentTaskType:
        message_type = event_dict.get("message_type", "text")
        content = event_dict.get("content", "").lower()
        if message_type == "product_brief" or message_type == "product_vision":
            return AgentTaskType.ANALYZE_REQUIREMENTS
        elif message_type == "prd":
            return AgentTaskType.CREATE_STORIES
        elif message_type == "code_review":
            return AgentTaskType.CODE_REVIEW

        if "review" in content and "code" in content:
            return AgentTaskType.CODE_REVIEW
        elif "test" in content or "bug" in content:
            return AgentTaskType.WRITE_TESTS if "test" in content else AgentTaskType.FIX_BUG
        elif "implement" in content or "develop" in content:
            return AgentTaskType.IMPLEMENT_STORY
        elif "refactor" in content:
            return AgentTaskType.REFACTOR
        elif "analyze" in content or "requirements" in content:
            return AgentTaskType.ANALYZE_REQUIREMENTS
        elif "story" in content or "stories" in content:
            return AgentTaskType.CREATE_STORIES

        if agent_role:
            role_defaults = {
                "business_analyst": AgentTaskType.ANALYZE_REQUIREMENTS,
                "developer": AgentTaskType.IMPLEMENT_STORY,
                "tester": AgentTaskType.WRITE_TESTS,
                "team_leader": AgentTaskType.MESSAGE,
            }
            return role_defaults.get(agent_role, AgentTaskType.MESSAGE)

        return AgentTaskType.MESSAGE
