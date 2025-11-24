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
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.kafka.event_schemas import (
    AgentResponseEvent,
    AgentStatusEvent,
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


# ============================================================================
# ROUTING LOGIC
# ============================================================================


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

        self.logger.info(f"[USER_MESSAGE_ROUTER] Routing user message {message_id} in project {project_id}")

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
            KafkaTopics.APPROVAL_RESPONSES.value,
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
            ApprovalResponseRouter(producer),
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
