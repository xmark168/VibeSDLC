"""Central Message Router for dispatching tasks to agents.

This module contains the routing logic and service for the VibeSDLC system.
The Router subscribes to various Kafka events and decides which agent should
handle each event, then publishes RouterTaskEvent to AGENT_TASKS topic.

Architecture:
    Events (USER_MESSAGES, AGENT_RESPONSES, etc.)
        ↓
    Router (rule-based routing logic)
        ↓
    AGENT_TASKS topic (RouterTaskEvent)
        ↓
    Agents (consume tasks based on agent_id)
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
    ApprovalResponseEvent,
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
    """Abstract base class for event routers.
    """

    def __init__(self, producer: KafkaProducer):
        """Initialize the router with a Kafka producer.

        Args:
            producer: Kafka producer for publishing router tasks
        """
        self.producer = producer
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if this router should handle the given event.

        Args:
            event: Event to check

        Returns:
            True if this router should handle the event
        """
        pass

    @abstractmethod
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route the event to appropriate agent(s).

        This method contains the core routing logic. It should:
        1. Analyze the event
        2. Determine target agent(s)
        3. Publish RouterTaskEvent(s) to AGENT_TASKS topic

        Args:
            event: Event to route
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
        """Publish a RouterTaskEvent to AGENT_TASKS topic.

        Args:
            agent_id: Target agent UUID
            task_type: Type of task (AgentTaskType enum)
            source_event: Original event that triggered routing
            routing_reason: Explanation of why this agent was chosen
            priority: Task priority (low, medium, high, critical)
            additional_context: Extra context to include in task
        """
        event_dict = source_event if isinstance(source_event, dict) else source_event.model_dump()

        # Build context
        context = {
            **event_dict,
            **(additional_context or {}),
        }

        # Create router task
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

        # Publish to AGENT_TASKS topic
        await self.producer.publish(
            topic=KafkaTopics.AGENT_TASKS,
            event=task,
        )

        self.logger.info(
            f"Published task {task.task_id} to agent {agent_id} "
            f"(reason: {routing_reason})"
        )

        # Broadcast message_delivered to frontend via WebSocket
        await self._mark_message_delivered(event_dict)

    async def _mark_message_delivered(self, event_dict: Dict[str, Any]) -> None:
        """Mark message as delivered and broadcast to frontend.
        
        Called after successfully routing message to agent.
        
        Args:
            event_dict: Source event dictionary containing message_id and project_id
        """
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
    """Router for USER_MESSAGES events.

    Routing logic:
    1. Parse message content for @mentions
    2. If @mention found → route to mentioned agent
    3. If no @mention → check conversation context → route to active agent or Team Leader
    """

    MENTION_PATTERN = re.compile(r"@(\w+)")
    
    # Smart session-aware timeouts
    CONTEXT_TIMEOUT_ONLINE_MINUTES = 7   # User online (WebSocket active)
    CONTEXT_TIMEOUT_OFFLINE_MINUTES = 15  # User offline
    GRACE_PERIOD_SECONDS = 120  # 2 min grace after disconnect

    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if event is a user message."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "user.message.sent"

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route user message to appropriate agent.

        Logic:
        - Extract @mentions from message content
        - Look up mentioned agent in database
        - If found, route to that agent
        - If not found or no mention, route to Team Leader
        """
        event_dict = event if isinstance(event, dict) else event.model_dump()

        project_id = event_dict.get("project_id")
        content = event_dict.get("content", "")
        message_id = event_dict.get("message_id")

        self.logger.info(f"[USER_MESSAGE_ROUTER] Routing user message {message_id} in project {project_id}")

        # Parse @mentions
        mentions = self.MENTION_PATTERN.findall(content)

        if mentions:
            # User mentioned agent(s)
            await self._route_with_mention(event_dict, mentions[0], project_id)
        else:
            # No mention → check conversation context
            await self._route_with_context(event_dict, project_id)

    async def _route_with_context(
        self,
        event_dict: Dict[str, Any],
        project_id: UUID
    ) -> None:
        """Route based on active conversation context."""
        with Session(engine) as session:
            # Get project with active agent
            project = session.get(Project, project_id)
            
            if not project:
                self.logger.error(f"Project {project_id} not found!")
                return
            
            # Check if there's an active agent
            active_agent_id = project.active_agent_id
            active_updated_at = project.active_agent_updated_at
            
            # Check if context is still valid (not expired)
            if active_agent_id and active_updated_at:
                # Ensure active_updated_at is timezone-aware
                if active_updated_at.tzinfo is None:
                    active_updated_at = active_updated_at.replace(tzinfo=timezone.utc)
                
                time_since_update = datetime.now(timezone.utc) - active_updated_at
                
                # Get smart timeout based on WebSocket connection
                timeout_minutes = self._get_timeout_for_project(project)
                timeout_seconds = timeout_minutes * 60
                
                if time_since_update.total_seconds() < timeout_seconds:
                    # Context still valid → route to active agent
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
                    # Context expired → clear it
                    connection_status = "online" if project.websocket_connected else "offline"
                    self.logger.info(
                        f"[CONTEXT_ROUTING] Context expired after {timeout_minutes}min "
                        f"(user {connection_status}), clearing context"
                    )
                    await self._clear_conversation_context(session, project_id)
            
            # No active context or expired → default to Team Leader
            await self._route_to_team_leader(event_dict, project_id)

    def _get_timeout_for_project(self, project: Project) -> int:
        """Get appropriate timeout based on WebSocket connection status.
        
        Returns timeout in minutes:
        - 7 minutes if user is online (WebSocket connected)
        - 15 minutes if user is offline
        - Grace period: Uses online timeout if disconnected < 2 minutes ago
        """
        # Check if user is currently online
        if project.websocket_connected:
            return self.CONTEXT_TIMEOUT_ONLINE_MINUTES
        
        # Check when WebSocket last seen (grace period for brief disconnects)
        if project.websocket_last_seen:
            # Ensure websocket_last_seen is timezone-aware
            websocket_last_seen = project.websocket_last_seen
            if websocket_last_seen.tzinfo is None:
                websocket_last_seen = websocket_last_seen.replace(tzinfo=timezone.utc)
            
            offline_duration = datetime.now(timezone.utc) - websocket_last_seen
            
            # If recently disconnected (< 2 min), use online timeout
            if offline_duration.total_seconds() < self.GRACE_PERIOD_SECONDS:
                return self.CONTEXT_TIMEOUT_ONLINE_MINUTES
        
        # User offline → longer timeout
        return self.CONTEXT_TIMEOUT_OFFLINE_MINUTES

    async def _route_with_mention(
        self, event_dict: Dict[str, Any], mentioned_name: str, project_id: UUID
    ) -> None:
        """Route message to mentioned agent (one-off request, doesn't switch context)."""
        with Session(engine) as session:
            # Look up agent by name in project using AgentService
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
                # This allows users to ask one-off questions without switching context
                
                # Found mentioned agent - infer task type
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
                # Mentioned agent not found → fallback to Team Leader
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
                
                self.logger.info(
                    f"[CONTEXT_UPDATE] Set active agent for project {project_id}: {agent_id}"
                )
        except Exception as e:
            self.logger.error(f"Failed to update conversation context: {e}", exc_info=True)
            session.rollback()

    async def _clear_conversation_context(
        self,
        session: Session,
        project_id: UUID
    ) -> None:
        """Clear conversation context (set to NULL)."""
        try:
            project = session.get(Project, project_id)
            if project:
                project.active_agent_id = None
                project.active_agent_updated_at = None
                session.add(project)
                session.commit()
                
                self.logger.info(
                    f"[CONTEXT_CLEAR] Cleared conversation context for project {project_id}"
                )
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
            # Find Team Leader in project using AgentService
            from app.services import AgentService
            agent_service = AgentService(session)
            team_leader = agent_service.get_by_project_and_role(
                project_id=project_id,
                role_type="team_leader"
            )

            if team_leader:
                # Team Leader gets MESSAGE task type
                await self.publish_task(
                    agent_id=team_leader.id,
                    task_type=AgentTaskType.MESSAGE,
                    source_event=event_dict,
                    routing_reason="no_mention_default_team_leader",
                    priority="medium",
                )
                self.logger.info(
                    f"Routed message to Team Leader: {team_leader.name} ({team_leader.id})"
                )
            else:
                self.logger.error(
                    f"No Team Leader found in project {project_id}, cannot route message!"
                )

    def _infer_task_type(self, event_dict: Dict[str, Any], agent_role: str = None) -> AgentTaskType:
        """Infer task type from message content and type.

        Args:
            event_dict: Event dictionary with message data
            agent_role: Role of target agent (optional, for role-specific inference)

        Returns:
            AgentTaskType enum value
        """
        message_type = event_dict.get("message_type", "text")
        content = event_dict.get("content", "").lower()

        # Infer from message_type
        if message_type == "product_brief" or message_type == "product_vision":
            return AgentTaskType.ANALYZE_REQUIREMENTS
        elif message_type == "prd":
            return AgentTaskType.CREATE_STORIES
        elif message_type == "code_review":
            return AgentTaskType.CODE_REVIEW

        # Infer from content keywords
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

        # Default based on agent role
        if agent_role:
            role_defaults = {
                "business_analyst": AgentTaskType.ANALYZE_REQUIREMENTS,
                "developer": AgentTaskType.IMPLEMENT_STORY,
                "tester": AgentTaskType.WRITE_TESTS,
                "team_leader": AgentTaskType.MESSAGE,
            }
            return role_defaults.get(agent_role, AgentTaskType.MESSAGE)

        # Final fallback
        return AgentTaskType.MESSAGE


class AgentMessageRouter(BaseEventRouter):
    """Router that updates conversation context when agent sends messages."""
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if event is agent message/response."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        
        # Handle agent response events
        return event_type in ["agent.response", "agent.response.created"]
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Update conversation context when agent responds."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        
        project_id = event_dict.get("project_id")
        agent_name = event_dict.get("agent_name")
        
        if not project_id or not agent_name:
            return
        
        with Session(engine) as session:
            # Look up agent
            from app.services import AgentService
            agent_service = AgentService(session)
            
            agent = agent_service.get_by_project_and_name(
                project_id=UUID(project_id) if isinstance(project_id, str) else project_id,
                name=agent_name,
                case_sensitive=False
            )
            
            if agent:
                # Update active agent context
                project = session.get(Project, agent.project_id)
                if project:
                    previous_agent_id = project.active_agent_id
                    project.active_agent_id = agent.id
                    project.active_agent_updated_at = datetime.now(timezone.utc)
                    session.add(project)
                    session.commit()
                    
                    self.logger.info(
                        f"[CONTEXT_UPDATE] Agent {agent.human_name} responded, "
                        f"set as active for project {project_id}"
                    )
                    
                    # Broadcast ownership change (MetaGPT-style)
                    # TODO: Fix inheritance issue with _broadcast_ownership_change
                    # await self._broadcast_ownership_change(
                    #     project_id=agent.project_id,
                    #     new_agent=agent,
                    #     previous_agent_id=previous_agent_id,
                    #     reason="task_started"
                    # )


class TaskCompletionRouter(BaseEventRouter):
    """Router that clears conversation context when agent completes task."""
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if event signals task completion."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        
        # Check for task completion signal in agent response events
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
                # Get agent before clearing
                agent = session.get(Agent, project.active_agent_id)
                
                # Clear context after task completion
                project.active_agent_id = None
                project.active_agent_updated_at = None
                session.add(project)
                session.commit()
                
                self.logger.info(
                    f"[TASK_COMPLETION] Cleared conversation context for project {project_id} "
                    f"after {agent_name} completed task"
                )
                
                # Broadcast ownership released (MetaGPT-style)
                if agent:
                    await self._broadcast_ownership_released(
                        project_id=UUID(project_id) if isinstance(project_id, str) else project_id,
                        agent=agent,
                        reason="task_completed"
                    )


class AgentResponseRouter(BaseEventRouter):
    """Router for AGENT_RESPONSES events.

    Handles workflow transitions after an agent responds.
    For example: BA finishes analysis → route to Developer
    """

    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if event is an agent response."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "agent.response.created"

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route based on agent response workflow.

        Currently: Log the response, no automatic routing.
        Future: Implement workflow state machine transitions.
        """
        event_dict = event if isinstance(event, dict) else event.model_dump()
        agent_name = event_dict.get("agent_name", "unknown")
        project_id = event_dict.get("project_id")

        self.logger.info(
            f"Agent '{agent_name}' responded in project {project_id}. "
            f"No automatic workflow transition configured yet."
        )

        # TODO: Implement workflow transitions
        # Example: If BA finished requirements → route task to Developer
        # This requires workflow state tracking


class ApprovalResponseRouter(BaseEventRouter):
    """Router for APPROVAL_RESPONSES events.

    Handles routing after user approves/rejects agent proposals.
    """

    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if event is an approval response."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "approval.response.submitted"

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route based on approval decision.

        If approved: Continue workflow
        If rejected: Route back to originating agent with feedback
        """
        event_dict = event if isinstance(event, dict) else event.model_dump()
        approved = event_dict.get("approved", False)
        approval_request_id = event_dict.get("approval_request_id")
        feedback = event_dict.get("feedback")

        self.logger.info(
            f"Approval request {approval_request_id}: "
            f"{'APPROVED' if approved else 'REJECTED'}"
        )

        if not approved and feedback:
            # TODO: Route back to agent with feedback
            self.logger.info(f"Rejection feedback: {feedback}")
            # Need to look up which agent created the approval request
            # Then route task back to them with feedback

        # TODO: Implement approval workflow routing


class AgentStatusRouter(BaseEventRouter):
    """Router for AGENT_STATUS events.

    Tracks agent availability for load balancing.
    Currently passive (just logs), but can be extended for smart routing.
    """

    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        """Check if event is an agent status update."""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        event_type = event_dict.get("event_type", "")
        return event_type.startswith("agent.")

    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Track agent status for future load balancing.

        Currently: Just log status changes
        Future: Use status for routing decisions (don't route to offline agents)
        """
        event_dict = event if isinstance(event, dict) else event.model_dump()
        agent_name = event_dict.get("agent_name", "unknown")
        status = event_dict.get("status", "unknown")

        self.logger.debug(f"Agent '{agent_name}' status: {status}")

        # TODO: Maintain agent availability state for smart routing
        # Can use Redis/in-memory dict to track which agents are available


class QuestionAnswerRouter(BaseEventRouter):
    """Router for QUESTION_ANSWERS events.
    
    Routes user answers back to the agent that asked the question,
    resuming the paused task with the answer.
    """
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "user.question_answer"
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route answer back to agent and resume task"""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        
        question_id = event_dict.get("question_id")
        agent_id_raw = event_dict.get("agent_id")
        task_id = event_dict.get("task_id")
        answer = event_dict.get("answer")
        selected_options = event_dict.get("selected_options")
        
        # Validate required fields
        if not question_id or not agent_id_raw:
            self.logger.error(f"Missing required fields: question_id={question_id}, agent_id={agent_id_raw}")
            return
        
        # Convert agent_id to UUID
        agent_id = UUID(agent_id_raw) if isinstance(agent_id_raw, str) else agent_id_raw
        
        self.logger.info(
            f"[QUESTION_ANSWER_ROUTER] Routing answer for question {question_id} "
            f"back to agent {agent_id}"
        )
        
        # Load question from DB to get full context
        from app.models import AgentQuestion, QuestionStatus
        
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
            
            # Update question status
            question.status = QuestionStatus.ANSWERED
            question.answer = answer
            question.selected_options = selected_options
            question.answered_at = datetime.now(timezone.utc)
            session.add(question)
            
            # ALSO update messages table for chat history persistence
            from app.models import Message
            message = session.get(Message, question_id)
            if message:
                # Update structured_data to mark as answered
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
            
            # Load original task context
            original_task_context = question.task_context
        
        # Publish RESUME task to agent
        await self.publish_task(
            agent_id=agent_id,
            task_type=AgentTaskType.RESUME_WITH_ANSWER,
            source_event=event_dict,
            routing_reason=f"question_answer:{question_id}",
            priority="high",
            additional_context={
                "question_id": str(question_id),
                "question_text": question.question_text,
                "answer": answer,
                "selected_options": selected_options,
                "original_context": original_task_context,
            }
        )
        
        self.logger.info(
            f"Published RESUME_WITH_ANSWER task to agent {agent_id}"
        )
        
        # Broadcast agent resumed event to WebSocket
        from app.websocket.connection_manager import connection_manager
        await connection_manager.broadcast_to_project(
            {
                "type": "agent.resumed",
                "question_id": str(question_id),
                "agent_id": str(agent_id),
                "agent_name": question.agent.human_name if question.agent else "Agent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            project_id
        )


class BatchAnswersRouter(BaseEventRouter):
    """Router for QUESTION_ANSWERS events (batch mode).
    
    Routes user answers for multiple questions back to the agent that asked them,
    resuming the paused task with all answers at once.
    """
    
    def should_handle(self, event: BaseKafkaEvent | Dict[str, Any]) -> bool:
        event_dict = event if isinstance(event, dict) else event.model_dump()
        return event_dict.get("event_type") == "user.question_batch_answer"
    
    async def route(self, event: BaseKafkaEvent | Dict[str, Any]) -> None:
        """Route batch answers back to agent and resume task"""
        event_dict = event if isinstance(event, dict) else event.model_dump()
        
        batch_id = event_dict.get("batch_id")
        answers = event_dict.get("answers", [])  # List of { question_id, answer, selected_options }
        agent_id_raw = event_dict.get("agent_id")
        task_id = event_dict.get("task_id")
        
        if not batch_id or not answers:
            self.logger.error("Batch answer event missing batch_id or answers")
            return
        
        # Convert IDs to UUID
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
        
        # Update all questions in database
        from app.models import AgentQuestion, Message, QuestionStatus
        
        with Session(engine) as session:
            first_question = None
            
            for ans_data in answers:
                question_id = UUID(ans_data["question_id"])
                
                # Update agent_questions table
                question = session.get(AgentQuestion, question_id)
                if question:
                    if not first_question:
                        first_question = question
                    
                    question.status = QuestionStatus.ANSWERED
                    question.answer = ans_data.get("answer", "")
                    question.selected_options = ans_data.get("selected_options")
                    question.answered_at = datetime.now(timezone.utc)
                    session.add(question)
                
                # Update messages table (for chat history)
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
            
            # Get original task context from first question
            original_task_context = first_question.task_context if first_question else {}
        
        # Resume agent with all answers at once
        await self.publish_task(
            agent_id=agent_id,
            task_type=AgentTaskType.RESUME_WITH_ANSWER,
            source_event=event_dict,
            routing_reason=f"batch_answers:{batch_id}",
            priority="high",
            additional_context={
                "batch_id": batch_id,
                "batch_answers": answers,  # All answers at once
                "answer_count": len(answers),
                "original_context": original_task_context,
                "is_batch": True,
            }
        )
        
        self.logger.info(
            f"Published RESUME_WITH_ANSWER task to agent {agent_id} with {len(answers)} batch answers"
        )
        
        # Broadcast agent resumed event to WebSocket
        from app.websocket.connection_manager import connection_manager
        await connection_manager.broadcast_to_project(
            {
                "type": "agent.resumed_batch",
                "batch_id": batch_id,
                "agent_id": str(agent_id),
                "agent_name": first_question.agent.human_name if first_question and first_question.agent else "Agent",
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
        
        # Convert project_id to UUID if needed
        if isinstance(project_id, str):
            project_id = UUID(project_id)
        
        # Find best agent for role
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
        
        # Create task for selected agent
        producer = await get_kafka_producer()
        
        # Extract context and ensure content is included
        delegation_context = event_dict.get("context", {})
        delegation_content = event_dict.get("content", "")
        
        # Add content to context if not already there
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
        
        # Update conversation context
        await self._update_active_agent(project_id, agent.id)
        
        self.logger.info(
            f"[DelegationRouter] Delegated to {agent.human_name} "
            f"(role={target_role}) for project {project_id}"
        )
    
    async def _find_best_agent(self, project_id: UUID, role_type: str) -> Optional[Agent]:
        """Find best agent for role - prefers idle agents."""
        with Session(engine) as session:
            # Get all agents with target role in project (exclude terminated/stopped)
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
            
            # Strategy: Prefer idle > busy > any
            idle_agents = [a for a in agents if a.status == "idle"]
            if idle_agents:
                selected = idle_agents[0]
                self.logger.info(f"[DelegationRouter] Selected idle agent: {selected.human_name} (id={selected.id})")
                return selected
            
            # Return first agent (simple strategy)
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
        """Handle delegation failure - send error back to delegating agent.
        
        The delegating agent will receive a DELEGATION_FAILED task and can:
        1. Notify user about the error
        2. Handle the task itself as fallback
        3. Try delegating to another role
        """
        delegating_agent_id = event_dict.get("delegating_agent_id")
        delegating_agent_name = event_dict.get("delegating_agent_name")
        
        if not delegating_agent_id:
            self.logger.error("Cannot handle delegation failure: delegating_agent_id missing")
            return
        
        # Convert to UUID if needed
        if isinstance(delegating_agent_id, str):
            delegating_agent_id = UUID(delegating_agent_id)
        
        # Create error message for user
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
        
        # Send task back to delegating agent to handle the error
        producer = await get_kafka_producer()
        
        # Create a DELEGATION_FAILED task for the delegating agent
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
                # Preserve original content so agent can handle it
                "original_content": event_dict.get("content"),
            }
        )
        
        await producer.publish(
            topic=KafkaTopics.AGENT_TASKS,
            event=error_task
        )
        
        self.logger.info(
            f"[DelegationRouter] Delegation failed (no {target_role} found), "
            f"sent error task back to {delegating_agent_name}"
        )


# ============================================================================
# ROUTER SERVICE
# ============================================================================


class MessageRouterService(BaseKafkaConsumer):
    """Central routing service that subscribes to events and dispatches to routers.

    This service:
    1. Subscribes to multiple Kafka topics
    2. Receives events
    3. Dispatches to appropriate router based on event type
    4. Routers publish RouterTaskEvent to AGENT_TASKS topic
    """

    def __init__(self):
        """Initialize the router service."""
        # Subscribe to topics that need routing
        topics = [
            KafkaTopics.USER_MESSAGES.value,
            KafkaTopics.AGENT_EVENTS.value,  # For agent responses to update context
            KafkaTopics.APPROVAL_RESPONSES.value,
            KafkaTopics.QUESTION_ANSWERS.value,
            KafkaTopics.DELEGATION_REQUESTS.value,  # For delegation by role
        ]

        # Use a dedicated consumer group for the router
        super().__init__(
            topics=topics,
            group_id="message_router_service",
            auto_commit=True,
        )

        self.routers: List[BaseEventRouter] = []
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the router service.

        Initializes routers and starts consuming events.
        """
        self.logger.info("Starting Message Router Service...")

        # Initialize routers with Kafka producer
        producer = await get_kafka_producer()

        self.routers = [
            UserMessageRouter(producer),
            AgentMessageRouter(producer),
            TaskCompletionRouter(producer),
            ApprovalResponseRouter(producer),
            QuestionAnswerRouter(producer),
            BatchAnswersRouter(producer),
            DelegationRouter(producer),
        ]

        self.logger.info(f"Initialized {len(self.routers)} routers")

        # Start consuming
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
        """Handle incoming event by dispatching to appropriate router.

        This method is called by BaseKafkaConsumer for each message.

        Args:
            topic: Kafka topic name
            event: Validated event object or raw dict
            raw_data: Raw event data dict
            key: Message key
            partition: Partition number
            offset: Message offset
        """
        event_type = raw_data.get("event_type", "unknown")

        self.logger.info(f"[ROUTER] Received event: {event_type} from topic: {topic}")
        
        # Use raw_data for routing (event might be validated object)
        event_dict = raw_data if isinstance(raw_data, dict) else (event if isinstance(event, dict) else event.model_dump())

        # Dispatch to routers
        routed = False
        for router in self.routers:
            try:
                if router.should_handle(event_dict):
                    await router.route(event_dict)
                    routed = True
                    break  # Only first matching router handles the event
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
    """Get the global router service instance.

    Returns:
        MessageRouterService instance
    """
    global _router_service

    if _router_service is None:
        _router_service = MessageRouterService()

    return _router_service


async def start_router_service() -> MessageRouterService:
    """Start the global router service.

    Returns:
        Started MessageRouterService instance
    """
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
