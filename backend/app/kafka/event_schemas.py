"""
Kafka event schemas and topic definitions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class KafkaTopics(str, Enum):
    """Kafka topic names for different event types."""

    USER_MESSAGES = "user_messages"
    AGENT_RESPONSES = "agent_responses"
    AGENT_ROUTING = "agent_routing"
    STORY_EVENTS = "story_events"
    FLOW_STATUS = "flow_status"
    AGENT_STATUS = "agent_status"
    APPROVAL_REQUESTS = "approval_requests"
    APPROVAL_RESPONSES = "approval_responses"
    

# BASE EVENT SCHEMA
class BaseKafkaEvent(BaseModel):
    """Base schema for all Kafka events."""

    event_id: str = Field(default_factory=lambda: str(UUID))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    project_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# USER MESSAGE EVENTS
class UserMessageEvent(BaseKafkaEvent):
    """Event emitted when user sends a message to agents."""

    event_type: str = "user.message.sent"
    message_id: UUID
    content: str
    author_type: str = "USER"
    message_type: str = "text"  # text, prd, product_vision, etc.


# AGENT RESPONSE EVENTS
class AgentResponseEvent(BaseKafkaEvent):
    """Event emitted when agent produces a response."""

    event_type: str = "agent.response.created"
    message_id: UUID
    agent_name: str
    agent_type: str
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    approval_request_id: Optional[UUID] = None


# AGENT ROUTING EVENTS
class AgentRoutingEvent(BaseKafkaEvent):
    """Event emitted when TeamLeader delegates to specialist agents."""

    event_type: str = "agent.routing.delegated"
    from_agent: str
    to_agent: str
    delegation_reason: str
    context: Dict[str, Any] = Field(default_factory=dict)


# STORY EVENTS
class StoryEventType(str, Enum):
    """Story event types."""

    CREATED = "story.created"
    UPDATED = "story.updated"
    STATUS_CHANGED = "story.status.changed"
    ASSIGNED = "story.assigned"
    DELETED = "story.deleted"


class StoryCreatedEvent(BaseKafkaEvent):
    """Event emitted when a story is created."""

    event_type: str = StoryEventType.CREATED.value
    story_id: UUID
    title: str
    description: Optional[str] = None
    story_type: str  # UserStory, EnablerStory
    status: str  # Todo, InProgress, Review, Done
    epic_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    created_by_agent: Optional[str] = None


class StoryUpdatedEvent(BaseKafkaEvent):
    """Event emitted when a story is updated."""

    event_type: str = StoryEventType.UPDATED.value
    story_id: UUID
    updated_fields: Dict[str, Any]
    updated_by: Optional[str] = None  # user_id or agent_name


class StoryStatusChangedEvent(BaseKafkaEvent):
    """Event emitted when story status transitions."""

    event_type: str = StoryEventType.STATUS_CHANGED.value
    story_id: UUID
    old_status: str
    new_status: str
    changed_by: str  # user_id or agent_name
    transition_reason: Optional[str] = None


class StoryAssignedEvent(BaseKafkaEvent):
    """Event emitted when story is assigned."""

    event_type: str = StoryEventType.ASSIGNED.value
    story_id: UUID
    assignee_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    assigned_by: str  # agent_name or user_id


# APPROVAL EVENTS
class ApprovalRequestEvent(BaseKafkaEvent):
    """Event emitted when agent requests human approval."""

    event_type: str = "approval.request.created"
    approval_request_id: UUID
    request_type: str  # story_creation, story_update, epic_creation
    agent_name: str
    proposed_data: Dict[str, Any]
    preview_data: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None


class ApprovalResponseEvent(BaseKafkaEvent):
    """Event emitted when user responds to approval request."""

    event_type: str = "approval.response.submitted"
    approval_request_id: UUID
    approved: bool
    feedback: Optional[str] = None
    modified_data: Optional[Dict[str, Any]] = None


# FLOW STATUS EVENTS
class FlowStatusType(str, Enum):
    """Flow execution status types."""

    STARTED = "flow.started"
    IN_PROGRESS = "flow.in_progress"
    COMPLETED = "flow.completed"
    FAILED = "flow.failed"
    CANCELLED = "flow.cancelled"


class FlowStatusEvent(BaseKafkaEvent):
    """Event emitted for workflow execution status updates."""

    event_type: str
    flow_id: UUID
    flow_type: str  # story_generation, code_review
    status: FlowStatusType
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    completed_steps: Optional[int] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


# AGENT STATUS EVENTS
class AgentStatusType(str, Enum):
    """Agent execution status types."""

    IDLE = "agent.idle"
    THINKING = "agent.thinking"
    ACTING = "agent.acting"
    WAITING = "agent.waiting"
    ERROR = "agent.error"


class AgentStatusEvent(BaseKafkaEvent):
    """Event emitted for agent status updates."""

    event_type: str
    agent_name: str
    status: AgentStatusType
    current_action: Optional[str] = None
    execution_id: Optional[UUID] = None
    error_message: Optional[str] = None


# EVENT REGISTRY
EVENT_TYPE_TO_SCHEMA = {
    "user.message.sent": UserMessageEvent,
    "agent.response.created": AgentResponseEvent,
    "agent.routing.delegated": AgentRoutingEvent,
    StoryEventType.CREATED.value: StoryCreatedEvent,
    StoryEventType.UPDATED.value: StoryUpdatedEvent,
    StoryEventType.STATUS_CHANGED.value: StoryStatusChangedEvent,
    StoryEventType.ASSIGNED.value: StoryAssignedEvent,
    "approval.request.created": ApprovalRequestEvent,
    "approval.response.submitted": ApprovalResponseEvent,
    FlowStatusType.STARTED.value: FlowStatusEvent,
    FlowStatusType.IN_PROGRESS.value: FlowStatusEvent,
    FlowStatusType.COMPLETED.value: FlowStatusEvent,
    FlowStatusType.FAILED.value: FlowStatusEvent,
    FlowStatusType.CANCELLED.value: FlowStatusEvent,
    "agent.idle": AgentStatusEvent,
    "agent.thinking": AgentStatusEvent,
    "agent.acting": AgentStatusEvent,
    "agent.waiting": AgentStatusEvent,
    "agent.error": AgentStatusEvent,
}


def get_event_schema(event_type: str) -> type[BaseKafkaEvent]:
    """Get Pydantic schema class for an event type.

    Args:
        event_type: Event type string

    Returns:
        Pydantic model class for the event

    Raises:
        ValueError: If event type is not registered
    """
    schema = EVENT_TYPE_TO_SCHEMA.get(event_type)
    if not schema:
        raise ValueError(f"Unknown event type: {event_type}")
    return schema
