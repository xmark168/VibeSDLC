"""
Kafka event schemas and topic definitions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


def get_project_topic(project_id: UUID) -> str:
    """Get the Kafka topic name for a specific project.

    Each project has its own topic where all agents in that project
    listen for user messages and delegation events.

    Args:
        project_id: UUID of the project

    Returns:
        Topic name in format: project_{project_id}_messages

    Example:
        >>> get_project_topic(UUID("abc-123"))
        'project_abc-123_messages'
    """
    return f"project_{project_id}_messages"


class KafkaTopics(str, Enum):
    """Kafka topic names for different event types."""

    USER_MESSAGES = "user_messages"
    AGENT_RESPONSES = "agent_responses"
    AGENT_ROUTING = "agent_routing"
    STORY_EVENTS = "story_events"
    FLOW_STATUS = "flow_status"
    AGENT_STATUS = "agent_status"
    AGENT_PROGRESS = "agent_progress"
    TOOL_CALLS = "tool_calls"
    APPROVAL_REQUESTS = "approval_requests"
    APPROVAL_RESPONSES = "approval_responses"
    AGENT_TASKS = "agent_tasks"
    

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
    agent_id: Optional[UUID] = None  # ID of mentioned/targeted agent for routing
    agent_name: Optional[str] = None  # Name of mentioned/targeted agent for display


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
    agent_id: Optional[str] = None
    status: AgentStatusType
    current_action: Optional[str] = None
    execution_id: Optional[UUID] = None
    error_message: Optional[str] = None


# AGENT PROGRESS EVENTS
class AgentProgressEvent(BaseKafkaEvent):
    """Event emitted for agent progress tracking during execution."""

    event_type: str = "agent.progress"
    agent_name: str
    agent_id: Optional[str] = None
    execution_id: Optional[UUID] = None
    step_number: int
    total_steps: int
    step_description: str
    status: str  # "in_progress", "completed", "failed"
    step_result: Optional[Dict[str, Any]] = None


# TOOL CALL EVENTS
class ToolCallEvent(BaseKafkaEvent):
    """Event emitted when agent uses a tool."""

    event_type: str = "agent.tool_call"
    agent_name: str
    agent_id: Optional[str] = None
    execution_id: Optional[UUID] = None
    tool_name: str  # "database_query", "file_write", "api_call", "create_story"
    display_name: str  # Human-readable: "Querying stories from database"
    parameters: Optional[Dict[str, Any]] = None
    status: str  # "started", "completed", "failed"
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


# AGENT TASK EVENTS
class AgentTaskType(str, Enum):
    """Types of tasks that can be assigned to agents."""

    CODE_REVIEW = "code_review"
    IMPLEMENT_STORY = "implement_story"
    WRITE_TESTS = "write_tests"
    FIX_BUG = "fix_bug"
    REFACTOR = "refactor"
    ANALYZE_REQUIREMENTS = "analyze_requirements"
    CREATE_STORIES = "create_stories"
    CUSTOM = "custom"


class AgentTaskStatus(str, Enum):
    """Status of agent tasks."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTaskAssignedEvent(BaseKafkaEvent):
    """Event emitted when a task is assigned to an agent."""

    event_type: str = "agent.task.assigned"
    task_id: UUID
    task_type: AgentTaskType
    agent_id: UUID
    agent_name: str
    assigned_by: str  # user_id or agent_name
    title: str
    description: Optional[str] = None
    priority: str = "medium"  # low, medium, high, critical
    story_id: Optional[UUID] = None
    epic_id: Optional[UUID] = None
    estimated_duration: Optional[int] = None  # minutes
    due_date: Optional[datetime] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class AgentTaskStartedEvent(BaseKafkaEvent):
    """Event emitted when agent starts working on a task."""

    event_type: str = "agent.task.started"
    task_id: UUID
    agent_id: UUID
    agent_name: str
    execution_id: UUID
    started_at: datetime = Field(default_factory=datetime.utcnow)


class AgentTaskProgressEvent(BaseKafkaEvent):
    """Event emitted for task progress updates."""

    event_type: str = "agent.task.progress"
    task_id: UUID
    agent_id: UUID
    agent_name: str
    execution_id: UUID
    progress_percentage: int  # 0-100
    current_step: str
    steps_completed: int
    total_steps: int
    estimated_completion: Optional[datetime] = None


class AgentTaskCompletedEvent(BaseKafkaEvent):
    """Event emitted when task is completed successfully."""

    event_type: str = "agent.task.completed"
    task_id: UUID
    agent_id: UUID
    agent_name: str
    execution_id: UUID
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: int
    result: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None  # Files created, PRs, etc.


class AgentTaskFailedEvent(BaseKafkaEvent):
    """Event emitted when task fails."""

    event_type: str = "agent.task.failed"
    task_id: UUID
    agent_id: UUID
    agent_name: str
    execution_id: UUID
    failed_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str
    error_type: Optional[str] = None
    retry_count: int = 0
    can_retry: bool = True


class AgentTaskCancelledEvent(BaseKafkaEvent):
    """Event emitted when task is cancelled."""

    event_type: str = "agent.task.cancelled"
    task_id: UUID
    agent_id: UUID
    agent_name: str
    cancelled_by: str  # user_id or agent_name
    cancelled_at: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None


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
    "agent.progress": AgentProgressEvent,
    "agent.tool_call": ToolCallEvent,
    "agent.task.assigned": AgentTaskAssignedEvent,
    "agent.task.started": AgentTaskStartedEvent,
    "agent.task.progress": AgentTaskProgressEvent,
    "agent.task.completed": AgentTaskCompletedEvent,
    "agent.task.failed": AgentTaskFailedEvent,
    "agent.task.cancelled": AgentTaskCancelledEvent,
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
