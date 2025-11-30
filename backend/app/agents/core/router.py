"""Central Message Router for dispatching tasks to agents.
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.kafka.event_schemas import (
    AgentResponseEvent,
    AgentTaskType,
    BaseKafkaEvent,
    RouterTaskEvent,
    UserMessageEvent,
    KafkaTopics,
)
from app.kafka.producer import KafkaProducer, get_kafka_producer
from app.kafka.consumer import BaseKafkaConsumer
from app.models import Agent, Project
from app.core.db import engine


logger = logging.getLogger(__name__)

class BaseEventRouter(ABC):
    """Abstract base class for event routers."""

    def __init__(self, producer: KafkaProducer):
        self.producer = producer
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if this router should handle the given event."""
        pass

    @abstractmethod
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route the event to appropriate agent(s).
        """
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
        """Mark message as delivered and broadcast to frontend."""
        message_id = event_dict.get("message_id")
        project_id = event_dict.get("project_id")
        
        if not message_id or not project_id:
            self.logger.debug("No message_id or project_id in event, skipping delivered broadcast")
            return
        
        try:
            # Broadcast to all WebSocket clients in project
            from app.websocket.connection_manager import connection_manager
            
            await connection_manager.broadcast_to_project(
                {
                    "type": "message_delivered",
                    "message_id": str(message_id),
                    "project_id": str(project_id),
                    "status": "delivered",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                UUID(project_id) if isinstance(project_id, str) else project_id
            )
            
            self.logger.info(f"Broadcasted message_delivered for {message_id}")
        except Exception as e:
            self.logger.error(f"Failed to broadcast message_delivered: {e}", exc_info=True)


class UserMessageRouter(BaseEventRouter):
    """
    Router for USER_MESSAGES events.
    """

    MENTION_PATTERN = re.compile(r"@(\w+)")
    
    CONTEXT_TIMEOUT_ONLINE_MINUTES = 7   # User online (WebSocket active)
    CONTEXT_TIMEOUT_OFFLINE_MINUTES = 15  # User offline
    GRACE_PERIOD_SECONDS = 120  # Grace period after disconnect

    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if event is a user message."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "user.message.sent"

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route user message to appropriate agent based on @mentions or conversation context."""
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
        """Get appropriate timeout based on WebSocket connection status.
        
        Returns timeout in minutes:
        - 7 minutes if user is online (WebSocket connected)
        - 15 minutes if user is offline
        - Grace period: Uses online timeout if disconnected < 2 minutes ago
        """
        if project.websocket_connected:
            return self.CONTEXT_TIMEOUT_ONLINE_MINUTES
        
        if project.websocket_last_seen:
            websocket_last_seen = project.websocket_last_seen
            if websocket_last_seen.tzinfo is None:
                websocket_last_seen = websocket_last_seen.replace(tzinfo=timezone.utc)
            
            offline_duration = datetime.now(timezone.utc) - websocket_last_seen
            
            if offline_duration.total_seconds() < self.GRACE_PERIOD_SECONDS:
                return self.CONTEXT_TIMEOUT_ONLINE_MINUTES
        
        return self.CONTEXT_TIMEOUT_OFFLINE_MINUTES

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
                # NOTE: @mention does NOT update conversation context
                # Only Team Leader delegation can assign conversation rights
                
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
        """Infer task type from message content and type."""
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


class AgentMessageRouter(BaseEventRouter):
    """Router that updates conversation context when agent sends messages."""
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        return event_type in ["agent.response", "agent.response.created"]
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Update conversation context when agent responds.
        
        If task_completed=True in details/structured_data, CLEAR ownership instead.
        """
        event_dict = event if isinstance(event, dict) else event.model_dump()
        
        project_id = event_dict.get("project_id")
        agent_name = event_dict.get("agent_name")
        
        if not project_id or not agent_name:
            return
        
        # Check if this is a task completion (should release ownership)
        details = event_dict.get("details", {})
        structured_data = event_dict.get("structured_data", {})
        task_completed = details.get("task_completed") or structured_data.get("task_completed")
        is_greeting = details.get("is_greeting", False)
        
        # Skip ownership update for greeting messages
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
                        # Task completed - CLEAR ownership
                        previous_agent_name = agent.human_name
                        project.active_agent_id = None
                        project.active_agent_updated_at = None
                        session.add(project)
                        session.commit()
                        
                        self.logger.info(
                            f"[CONTEXT_CLEAR] Agent {previous_agent_name} completed task, "
                            f"released ownership for project {project_id}"
                        )
                        
                        # Proactive greeting from Team Leader
                        await self._send_team_leader_greeting(
                            project_id, 
                            previous_agent_name
                        )
                    else:
                        # Normal response - set as active
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
                
                # Save values before session closes
                tl_human_name = team_leader.human_name
                tl_id = team_leader.id
                
                # Generate greeting message
                greeting = (
                    f"Tuyệt vời! {completed_agent_name} đã hoàn thành xong rồi! 🎉 "
                    f"Bạn cần mình hỗ trợ gì tiếp theo không?"
                )
                
                # 1. Save message to DB first
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
            
            # 2. Publish through Kafka (will be picked up by websocket handler)
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


class TaskCompletionRouter(BaseEventRouter):
    """Router that clears conversation context when agent completes task."""
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        
        if event_dict.get("event_type") in ["agent.response", "agent.response.created"]:
            structured_data = event_dict.get("structured_data", {})
            return structured_data.get("task_completed") == True
        
        return False
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Clear conversation context when task completes."""
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


class AgentResponseRouter(BaseEventRouter):
    """Router for AGENT_RESPONSES events. Handles workflow transitions after an agent responds."""

    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "agent.response.created"

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route based on agent response workflow (currently logs only)."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        agent_name = event_dict.get("agent_name", "unknown")
        project_id = event_dict.get("project_id")

        self.logger.info(f"Agent '{agent_name}' responded in project {project_id}.")


class StoryEventRouter(BaseEventRouter):
    """Router for STORY_EVENTS events.

    Handles story status changes (e.g., Todo → In Progress).
    For example: Story moves to In Progress → route to Developer
    """

    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if event is a story event."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        return event_type.startswith("story.")

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route based on story status change.

        Logic: If story moves to In Progress → route to Developer
        """
        event_dict = event if isinstance(event, dict) else event.model_dump()
        story_id = event_dict.get("story_id")
        project_id = event_dict.get("project_id")
        new_status = event_dict.get("new_status")
        old_status = event_dict.get("old_status")

        self.logger.info(
            f"Story {story_id} moved from {old_status} to {new_status} in project {project_id}"
        )

        # If story moves to In Progress, route to Developer agent
        if new_status == "InProgress" and old_status == "Todo":
            await self._route_to_developer(event_dict, project_id)

    async def _route_to_developer(self, event_dict: Dict[str, Any], project_id: UUID) -> None:
        """Route task to Developer agent."""
        with Session(engine) as session:
            from app.services import AgentService
            agent_service = AgentService(session)

            # Find Developer agent in project
            developer = agent_service.get_by_project_and_role(
                project_id=project_id,
                role_type="developer"
            )

            if developer:
                # Create a message for the developer about the status change
                story_title = event_dict.get('story_title', 'Unknown Story')
                content = f"Story '{story_title}' has been moved to In Progress. Please start development."

                await self.publish_task(
                    agent_id=developer.id,
                    task_type=AgentTaskType.IMPLEMENT_STORY,  # or other appropriate task type
                    source_event=event_dict,
                    routing_reason="story_status_changed_to_in_progress",
                    priority="high",
                    additional_context={
                        "story_id": event_dict.get("story_id"),
                        "content": content
                    }
                )

                self.logger.info(
                    f"Routed story status change to Developer: {developer.name} ({developer.id})"
                )
            else:
                self.logger.warning(
                    f"No Developer found in project {project_id} for story status change"
                )


class AgentStatusRouter(BaseEventRouter):
    """Router for AGENT_STATUS events. Tracks agent availability for load balancing."""

    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        return event_type.startswith("agent.")

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Track agent status (currently logs only)."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        agent_name = event_dict.get("agent_name", "unknown")
        status = event_dict.get("status", "unknown")

        self.logger.debug(f"Agent '{agent_name}' status: {status}")


class QuestionAnswerRouter(BaseEventRouter):
    """Router for QUESTION_ANSWERS events. Routes user answers back to the agent that asked the question."""
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "user.question_answer"
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route answer back to agent and resume task."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        
        question_id = event_dict.get("question_id")
        agent_id_raw = event_dict.get("agent_id")
        task_id = event_dict.get("task_id")
        answer = event_dict.get("answer")
        selected_options = event_dict.get("selected_options")
        
        if not question_id or not agent_id_raw:
            self.logger.error(f"Missing required fields: question_id={question_id}, agent_id={agent_id_raw}")
            return
        
        agent_id = UUID(agent_id_raw) if isinstance(agent_id_raw, str) else agent_id_raw
        
        self.logger.info(
            f"[QUESTION_ANSWER_ROUTER] Routing answer for question {question_id} "
            f"back to agent {agent_id}"
        )
        
        from app.models import AgentQuestion, QuestionStatus, QuestionType
        
        with Session(engine) as session:
            question = session.get(AgentQuestion, question_id)
            
            if not question:
                self.logger.error(f"Question {question_id} not found!")
                return
            
            if question.status != QuestionStatus.WAITING_ANSWER:
                self.logger.warning(
                    f"Question {question_id} already answered/expired, ignoring"
                )
                return
            
            question.status = QuestionStatus.ANSWERED
            question.answer = answer
            question.selected_options = selected_options
            
            if question.question_type == QuestionType.APPROVAL:
                question.approved = event_dict.get("approved")
                question.modified_data = event_dict.get("modified_data")
            
            question.answered_at = datetime.now(timezone.utc)
            session.add(question)
            
            from app.models import Message
            message = session.get(Message, question_id)
            if message:
                message.structured_data = {
                    **(message.structured_data or {}),
                    "answered": True,
                    "answered_at": datetime.now(timezone.utc).isoformat(),
                    "user_answer": answer or "",
                    "user_selected_options": selected_options or [],
                    "status": "answered"
                }
                session.add(message)
            
            session.commit()
            original_task_context = question.task_context
            project_id = question.project_id  # Get project_id from question
        
        context_data = {
            "question_id": str(question_id),
            "question_text": question.question_text,
            "question_type": question.question_type.value,
            "answer": answer,
            "selected_options": selected_options,
            "original_context": original_task_context,
        }
        
        if question.question_type == QuestionType.APPROVAL:
            context_data.update({
                "approved": question.approved,
                "modified_data": question.modified_data,
                "proposed_data": question.proposed_data,
                "final_data": question.modified_data if question.modified_data else question.proposed_data,
            })
        
        await self.publish_task(
            agent_id=agent_id,
            task_type=AgentTaskType.RESUME_WITH_ANSWER,
            source_event=event_dict,
            routing_reason=f"question_answer:{question_id}",
            priority="high",
            additional_context=context_data
        )
        
        self.logger.info(
            f"Published RESUME_WITH_ANSWER task to agent {agent_id}"
        )
        
        from app.websocket.connection_manager import connection_manager
        
        # Get agent name from database
        agent_name = "Agent"
        with Session(engine) as session:
            agent = session.get(Agent, agent_id)
            if agent:
                agent_name = agent.human_name or agent.name or "Agent"
        
        await connection_manager.broadcast_to_project(
            {
                "type": "agent.resumed",
                "question_id": str(question_id),
                "agent_id": str(agent_id),
                "agent_name": agent_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            project_id
        )


class BatchAnswersRouter(BaseEventRouter):
    """Router for QUESTION_ANSWERS events (batch mode). Routes multiple answers back to agent at once."""
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "user.question_batch_answer"
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route batch answers back to agent and resume task."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        
        batch_id = event_dict.get("batch_id")
        answers = event_dict.get("answers", [])
        agent_id_raw = event_dict.get("agent_id")
        task_id = event_dict.get("task_id")
        
        if not batch_id or not answers:
            self.logger.error("Batch answer event missing batch_id or answers")
            return
        
        try:
            if isinstance(agent_id_raw, str):
                agent_id = UUID(agent_id_raw)
            else:
                agent_id = agent_id_raw
            
            if isinstance(task_id, str):
                task_id = UUID(task_id)
        except Exception as e:
            self.logger.error(f"Invalid UUID in batch answer event: {e}")
            return
        
        project_id = event_dict.get("project_id")
        if isinstance(project_id, str):
            project_id = UUID(project_id)
        
        from app.models import AgentQuestion, Message, QuestionStatus
        
        with Session(engine) as session:
            first_question = None
            
            for ans_data in answers:
                question_id = UUID(ans_data["question_id"])
                
                question = session.get(AgentQuestion, question_id)
                if question:
                    if not first_question:
                        first_question = question
                    
                    question.status = QuestionStatus.ANSWERED
                    question.answer = ans_data.get("answer", "")
                    question.selected_options = ans_data.get("selected_options")
                    question.answered_at = datetime.now(timezone.utc)
                    session.add(question)
                
                message = session.get(Message, question_id)
                if message:
                    message.structured_data = {
                        **(message.structured_data or {}),
                        "answered": True,
                        "answered_at": datetime.now(timezone.utc).isoformat(),
                        "user_answer": ans_data.get("answer", ""),
                        "user_selected_options": ans_data.get("selected_options", []),
                        "status": "answered"
                    }
                    session.add(message)
            
            session.commit()
            original_task_context = first_question.task_context if first_question else {}
        
        await self.publish_task(
            agent_id=agent_id,
            task_type=AgentTaskType.RESUME_WITH_ANSWER,
            source_event=event_dict,
            routing_reason=f"batch_answers:{batch_id}",
            priority="high",
            additional_context={
                "batch_id": batch_id,
                "batch_answers": answers,
                "answer_count": len(answers),
                "original_context": original_task_context,
                "is_batch": True,
            }
        )
        
        self.logger.info(f"Published RESUME_WITH_ANSWER task to agent {agent_id} with {len(answers)} batch answers")
        
        from app.websocket.connection_manager import connection_manager
        
        # Get agent name from database
        agent_name = "Agent"
        with Session(engine) as session:
            agent = session.get(Agent, agent_id)
            if agent:
                agent_name = agent.human_name or agent.name or "Agent"
        
        await connection_manager.broadcast_to_project(
            {
                "type": "agent.resumed_batch",
                "batch_id": batch_id,
                "agent_id": str(agent_id),
                "agent_name": agent_name,
                "answer_count": len(answers),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            project_id
        )


class DelegationRouter(BaseEventRouter):
    """Router for delegation requests - finds best agent by role."""
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "delegation.request"
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Handle delegation request - find best agent and dispatch."""
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
            # Send error message back to user via delegating agent
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
        """Find best agent for role - prefers idle agents."""
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
        """Update project's active agent context."""
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
        
        self.logger.info(f"[DelegationRouter] Delegation failed (no {target_role} found), sent error task back to {delegating_agent_name}")


class AgentCollaborationRouter(BaseEventRouter):
    """Router for cross-agent collaboration requests.
    
    Handles direct agent-to-agent communication for:
    - Clarification requests (Dev → BA)
    - Review requests (Tester → Dev)
    - Estimation requests (BA → Dev)
    """
    
    MAX_COLLABORATION_DEPTH = 3  # Prevent infinite loops
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        return event_type in [
            "agent.collaboration.request",
            "agent.collaboration.response"
        ]
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route collaboration request/response to appropriate agent."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type")
        
        if event_type == "agent.collaboration.request":
            await self._handle_request(event_dict)
        elif event_type == "agent.collaboration.response":
            await self._handle_response(event_dict)
    
    async def _handle_request(self, event_dict: Dict[str, Any]) -> None:
        """Route collaboration request to target agent by role."""
        request_id = event_dict.get("request_id")
        to_role = event_dict.get("to_agent_role")
        from_role = event_dict.get("from_agent_role")
        project_id = event_dict.get("project_id")
        depth = event_dict.get("depth", 0)
        question = event_dict.get("question", "")
        
        self.logger.info(
            f"[COLLABORATION] Request from {from_role} → {to_role}: "
            f"{question[:50]}..."
        )
        
        # Check depth limit to prevent infinite loops
        if depth >= self.MAX_COLLABORATION_DEPTH:
            self.logger.warning(
                f"[COLLABORATION] Max depth ({self.MAX_COLLABORATION_DEPTH}) exceeded, rejecting"
            )
            await self._send_error_response(
                event_dict,
                f"Max collaboration depth ({self.MAX_COLLABORATION_DEPTH}) exceeded. "
                "Please simplify your request."
            )
            return
        
        if not project_id or not to_role:
            self.logger.error("[COLLABORATION] Missing project_id or to_agent_role")
            return
        
        if isinstance(project_id, str):
            project_id = UUID(project_id)
        
        # Find target agent by role
        agent = await self._find_agent_by_role(project_id, to_role)
        
        if not agent:
            self.logger.warning(f"[COLLABORATION] No {to_role} agent found in project {project_id}")
            await self._send_error_response(
                event_dict,
                f"No {to_role} agent available in this project."
            )
            return
        
        # Dispatch task to target agent
        await self.publish_task(
            agent_id=agent.id,
            task_type=AgentTaskType.COLLABORATION_REQUEST,
            source_event=event_dict,
            routing_reason=f"collaboration_from_{from_role}",
            priority="high",
            additional_context={
                "request_id": str(request_id),
                "question": question,
                "request_type": event_dict.get("request_type", "clarification"),
                "from_agent_id": event_dict.get("from_agent_id"),
                "from_agent_role": from_role,
                "collaboration_context": event_dict.get("context", {}),
                "depth": depth,
            }
        )
        
        self.logger.info(
            f"[COLLABORATION] Dispatched request to {agent.human_name} ({to_role})"
        )
    
    async def _handle_response(self, event_dict: Dict[str, Any]) -> None:
        """Route collaboration response back to requesting agent."""
        request_id = event_dict.get("request_id")
        to_agent_id = event_dict.get("to_agent_id")
        from_agent_id = event_dict.get("from_agent_id")
        success = event_dict.get("success", True)
        
        if not to_agent_id:
            self.logger.error("[COLLABORATION] Response missing to_agent_id")
            return
        
        if isinstance(to_agent_id, str):
            to_agent_id = UUID(to_agent_id)
        
        # Publish task to resume the requesting agent
        await self.publish_task(
            agent_id=to_agent_id,
            task_type=AgentTaskType.COLLABORATION_RESPONSE,
            source_event=event_dict,
            routing_reason=f"collaboration_response:{request_id}",
            priority="high",
            additional_context={
                "request_id": str(request_id),
                "response": event_dict.get("response", ""),
                "success": success,
                "error": event_dict.get("error"),
            }
        )
        
        self.logger.info(
            f"[COLLABORATION] Response for {request_id} dispatched to agent {to_agent_id}"
        )
    
    async def _find_agent_by_role(self, project_id: UUID, role_type: str) -> Optional[Agent]:
        """Find best agent for role - prefers idle agents (same as DelegationRouter)."""
        with Session(engine) as session:
            agents = session.exec(
                select(Agent).where(
                    Agent.project_id == project_id,
                    Agent.role_type == role_type,
                    Agent.status.not_in(["terminated", "stopped", "error"])
                )
            ).all()
            
            if not agents:
                return None
            
            # Prefer idle agents
            idle_agents = [a for a in agents if a.status == "idle"]
            if idle_agents:
                return idle_agents[0]
            
            return agents[0]
    
    async def _send_error_response(self, request: Dict[str, Any], error: str) -> None:
        """Send error response back to requesting agent."""
        from_agent_id = request.get("from_agent_id")
        
        if not from_agent_id:
            self.logger.error("[COLLABORATION] Cannot send error: from_agent_id missing")
            return
        
        from app.kafka.event_schemas import AgentCollaborationResponse
        
        response = AgentCollaborationResponse(
            request_id=UUID(request.get("request_id")) if request.get("request_id") else uuid4(),
            from_agent_id=UUID(request.get("to_agent_id", request.get("project_id"))),
            to_agent_id=UUID(from_agent_id) if isinstance(from_agent_id, str) else from_agent_id,
            response="",
            success=False,
            error=error,
            project_id=request.get("project_id"),
        )
        
        await self.producer.publish(
            KafkaTopics.AGENT_COLLABORATION,
            response
        )
        
        self.logger.info(f"[COLLABORATION] Sent error response: {error}")


# ============================================================================
# ROUTER SERVICE
# ============================================================================


class MessageRouterService(BaseKafkaConsumer):
    """Central routing service that subscribes to events and dispatches to routers."""

    def __init__(self):
        topics = [
            KafkaTopics.USER_MESSAGES.value,
            KafkaTopics.AGENT_EVENTS.value,  # For agent responses to update context
            KafkaTopics.STORY_EVENTS.value,  # Add story events for status change routing
            KafkaTopics.QUESTION_ANSWERS.value,
            KafkaTopics.DELEGATION_REQUESTS.value,
            KafkaTopics.AGENT_COLLABORATION.value,  # Cross-agent collaboration
        ]

        super().__init__(
            topics=topics,
            group_id="message_router_service",
            auto_commit=True,
        )

        self.routers: List[BaseEventRouter] = []
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the router service."""
        self.logger.info("Starting Message Router Service...")

        producer = await get_kafka_producer()

        self.routers = [
            UserMessageRouter(producer),
            AgentMessageRouter(producer),
            TaskCompletionRouter(producer),
            StoryEventRouter(producer),
            QuestionAnswerRouter(producer),
            BatchAnswersRouter(producer),
            DelegationRouter(producer),
            AgentCollaborationRouter(producer),
        ]

        self.logger.info(f"Initialized {len(self.routers)} routers")

        await super().start()

        self.logger.info("Message Router Service started successfully")

    async def stop(self):
        """Stop the router service."""
        self.logger.info("Stopping Message Router Service...")
        await super().stop()
        self.logger.info("Message Router Service stopped")

    async def handle_message(
        self,
        topic: str,
        event: Dict[str, Any],
        raw_data: Dict[str, Any],
        key: Optional[str],
        partition: int,
        offset: int,
    ) -> None:
        """Handle incoming event by dispatching to appropriate router."""
        event_type = raw_data.get("event_type", "unknown")

        self.logger.info(f"[ROUTER] Received event: {event_type} from topic: {topic}")
        
        event_dict = raw_data if isinstance(raw_data, dict) else (event if isinstance(event, dict) else event.model_dump())

        routed = False
        for router in self.routers:
            try:
                if router.should_handle(event_dict):
                    await router.route(event_dict)
                    routed = True
                    break
            except Exception as e:
                self.logger.error(
                    f"Error routing event {event_type} with {router.__class__.__name__}: {e}",
                    exc_info=True
                )

        if not routed:
            self.logger.warning(f"No router handled event type: {event_type}")


# ============================================================================
# GLOBAL SERVICE INSTANCE
# ============================================================================


_router_service: MessageRouterService | None = None


async def get_router_service() -> MessageRouterService:
    """Get the global router service instance."""
    global _router_service

    if _router_service is None:
        _router_service = MessageRouterService()

    return _router_service


async def start_router_service() -> MessageRouterService:
    """Start the global router service."""
    service = await get_router_service()
    if not service.running:
        await service.start()
    return service


async def stop_router_service() -> None:
    """Stop the global router service."""
    global _router_service

    if _router_service is not None:
        await _router_service.stop()
        _router_service = None
