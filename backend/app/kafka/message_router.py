"""Central Message Router for dispatching tasks to agents.

This module contains the routing logic abstraction for the VibeSDLC system.
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

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.kafka.event_schemas import (
    AgentResponseEvent,
    AgentStatusEvent,
    ApprovalResponseEvent,
    BaseKafkaEvent,
    RouterTaskEvent,
    UserMessageEvent,
)
from app.kafka.producer import KafkaProducer
from app.kafka.event_schemas import KafkaTopics
from app.models import Agent, Project
from app.core.db import engine


logger = logging.getLogger(__name__)


class BaseEventRouter(ABC):
    """Abstract base class for event routers.

    Each router handles a specific event type and implements routing logic
    to determine which agent should handle the event.
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
        source_event: BaseKafkaEvent | Dict[str, Any],
        routing_reason: str,
        priority: str = "medium",
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publish a RouterTaskEvent to AGENT_TASKS topic.

        Args:
            agent_id: Target agent UUID
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


class UserMessageRouter(BaseEventRouter):
    """Router for USER_MESSAGES events.

    Routing logic:
    1. Parse message content for @mentions
    2. If @mention found → route to mentioned agent
    3. If no @mention → route to Team Leader (default)
    """

    MENTION_PATTERN = re.compile(r"@(\w+)")

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

        self.logger.debug(f"Routing user message {message_id} in project {project_id}")

        # Parse @mentions
        mentions = self.MENTION_PATTERN.findall(content)

        if mentions:
            # User mentioned agent(s)
            await self._route_with_mention(event_dict, mentions[0], project_id)
        else:
            # No mention → default to Team Leader
            await self._route_to_team_leader(event_dict, project_id)

    async def _route_with_mention(
        self, event_dict: Dict[str, Any], mentioned_name: str, project_id: UUID
    ) -> None:
        """Route message to mentioned agent."""
        with Session(engine) as session:
            # Look up agent by name in project
            # Try case-insensitive match
            statement = (
                select(Agent)
                .where(Agent.project_id == project_id)
                .where(Agent.name.ilike(f"%{mentioned_name}%"))
            )
            agent = session.exec(statement).first()

            if agent:
                # Found mentioned agent
                await self.publish_task(
                    agent_id=agent.id,
                    source_event=event_dict,
                    routing_reason=f"@mention:{mentioned_name}",
                    priority="high",  # Mentions are high priority
                )
                self.logger.info(
                    f"Routed message to mentioned agent: {agent.name} ({agent.id})"
                )
            else:
                # Mentioned agent not found → fallback to Team Leader
                self.logger.warning(
                    f"Mentioned agent '@{mentioned_name}' not found in project {project_id}, "
                    f"routing to Team Leader"
                )
                await self._route_to_team_leader(event_dict, project_id)

    async def _route_to_team_leader(
        self, event_dict: Dict[str, Any], project_id: UUID
    ) -> None:
        """Route message to Team Leader (default behavior)."""
        with Session(engine) as session:
            # Find Team Leader in project
            statement = (
                select(Agent)
                .where(Agent.project_id == project_id)
                .where(Agent.role_type == "team_leader")
            )
            team_leader = session.exec(statement).first()

            if team_leader:
                await self.publish_task(
                    agent_id=team_leader.id,
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
