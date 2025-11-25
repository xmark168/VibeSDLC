"""
Kafka event schemas and topic definitions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class KafkaTopics(str, Enum):
    """Kafka topic names for different event types."""

    # Input: User → System
    USER_MESSAGES = "user_messages"
    
    # Processing: Unified agent events
    AGENT_EVENTS = "agent_events"
    
    # Task Management: Router → Agents
    AGENT_TASKS = "agent_tasks"
    
    # Domain Events: System state changes
    DOMAIN_EVENTS = "domain_events"
    STORY_EVENTS = "story_events"
    FLOW_STATUS = "flow_status"
    
    # Other
    APPROVAL_RESPONSES = "approval_responses"
    QUESTION_ANSWERS = "question_answers"
    

# BASE EVENT SCHEMA
class BaseKafkaEvent(BaseModel):
    """Base schema for all Kafka events."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))  # FIX: Call uuid4() to generate UUID instance
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    task_id: Optional[UUID] = None  # Task ID that was completed
    execution_id: Optional[UUID] = None  # Execution ID for linking to activity timeline
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


class StoryEvent(BaseKafkaEvent):
    """Unified event for all story lifecycle events.
    
    Replaces: StoryCreatedEvent, StoryUpdatedEvent, StoryStatusChangedEvent, StoryAssignedEvent
    
    Event types:
    - story.created
    - story.updated
    - story.status.changed
    - story.assigned
    - story.deleted
    """
    
    event_type: str  # story.{created|updated|status.changed|assigned|deleted}
    story_id: UUID
    
    # Core fields (for created/updated events)
    title: Optional[str] = None
    description: Optional[str] = None
    story_type: Optional[str] = None  # UserStory, EnablerStory
    status: Optional[str] = None  # Todo, InProgress, Review, Done
    
    # Status change fields (for status.changed events)
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    transition_reason: Optional[str] = None
    
    # Update fields (for updated events)
    updated_fields: Optional[Dict[str, Any]] = None
    
    # Assignment fields (for assigned events)
    assignee_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    
    # Metadata
    epic_id: Optional[UUID] = None
    created_by_agent: Optional[str] = None
    updated_by: Optional[str] = None  # user_id or agent_name
    changed_by: Optional[str] = None  # user_id or agent_name
    assigned_by: Optional[str] = None  # agent_name or user_id


# APPROVAL EVENTS
class ApprovalRequestEvent(BaseKafkaEvent):
    """Event emitted when agent requests human approval."""

    event_type: str = "approval.request.created"
    approval_request_id: UUID
    request_type: str  # story_creation, story_update, epic_creation
    agent_name: str
    proposed_data: Dict[str, Any]
    explanation: Optional[str] = None


class ApprovalResponseEvent(BaseKafkaEvent):
    """Event emitted when user responds to approval request."""

    event_type: str = "approval.response.submitted"
    approval_request_id: UUID
    approved: bool
    feedback: Optional[str] = None
    modified_data: Optional[Dict[str, Any]] = None


# CLARIFICATION QUESTION EVENTS
class QuestionAskedEvent(BaseKafkaEvent):
    """Event when agent asks a clarification question"""
    event_type: str = "agent.question_asked"
    
    question_id: UUID
    agent_id: UUID
    agent_name: str
    
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    allow_multiple: bool = False
    
    task_id: UUID
    execution_id: Optional[UUID] = None


class QuestionAnswerEvent(BaseKafkaEvent):
    """Event when user answers a question"""
    event_type: str = "user.question_answer"
    
    question_id: UUID
    answer: str
    selected_options: Optional[List[str]] = None
    
    agent_id: UUID
    task_id: UUID


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


# AGENT STATUS/PROGRESS/TOOL EVENTS - Now using unified AgentEvent (see below)


# AGENT TASK EVENTS
class AgentTaskType(str, Enum):
    """Types of tasks that can be assigned to agents."""

    # Specific task types
    CODE_REVIEW = "code_review"
    IMPLEMENT_STORY = "implement_story"
    WRITE_TESTS = "write_tests"
    FIX_BUG = "fix_bug"
    REFACTOR = "refactor"
    ANALYZE_REQUIREMENTS = "analyze_requirements"
    CREATE_STORIES = "create_stories"

    # Abstraction task types (high-level)
    USER_STORY = "user_story"  # BA: Analyze requirements → create user stories
    MESSAGE = "message"  # Any agent: Handle/respond to user message
    
    # Clarification questions
    RESUME_WITH_ANSWER = "resume_with_answer"  # Resume task with clarification answer

    # Generic
    CUSTOM = "custom"


class AgentTaskStatus(str, Enum):
    """Status of agent tasks."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTaskEvent(BaseKafkaEvent):
    """Unified event for all agent task lifecycle events.
    
    Replaces: AgentTaskAssignedEvent, AgentTaskStartedEvent, AgentTaskProgressEvent,
              AgentTaskCompletedEvent, AgentTaskFailedEvent, AgentTaskCancelledEvent
    
    Event types:
    - agent.task.assigned
    - agent.task.started
    - agent.task.progress
    - agent.task.completed
    - agent.task.failed
    - agent.task.cancelled
    """
    
    event_type: str  # agent.task.{assigned|started|progress|completed|failed|cancelled}
    task_id: UUID
    agent_id: UUID
    agent_name: str
    task_type: AgentTaskType
    status: AgentTaskStatus
    
    # Context (always present)
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Assignment fields (for assigned events)
    assigned_by: Optional[str] = None  # user_id or agent_name
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None  # low, medium, high, critical
    story_id: Optional[UUID] = None
    epic_id: Optional[UUID] = None
    estimated_duration: Optional[int] = None  # minutes
    due_date: Optional[datetime] = None
    
    # Execution tracking (for started/progress events)
    execution_id: Optional[UUID] = None
    started_at: Optional[datetime] = None
    
    # Progress tracking (for progress events)
    progress_percentage: Optional[int] = None  # 0-100
    current_step: Optional[str] = None
    steps_completed: Optional[int] = None
    total_steps: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    
    # Completion fields (for completed events)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None  # Files created, PRs, etc.
    
    # Failure fields (for failed events)
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    retry_count: Optional[int] = None
    can_retry: Optional[bool] = None
    
    # Cancellation fields (for cancelled events)
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    reason: Optional[str] = None


# ROUTER TASK EVENT (for Central Message Router)
class RouterTaskEvent(BaseKafkaEvent):
    """Event emitted by Central Message Router to dispatch tasks to agents.

    This is the primary event type used by the routing system to assign work to agents.
    The Router subscribes to various source events (USER_MESSAGES, AGENT_RESPONSES, etc.)
    and publishes RouterTaskEvent to AGENT_TASKS topic for agents to consume.
    """

    event_type: str = "router.task.dispatched"
    task_id: UUID = Field(default_factory=uuid4)
    task_type: AgentTaskType  # NEW: Type of task for agent to perform
    agent_id: UUID  # Target agent to handle this task
    agent_role: Optional[str] = None  # team_leader, business_analyst, developer, tester
    source_event_type: str  # Original event type: user.message.sent, agent.response.created, etc.
    source_event_id: str  # Original event ID for tracing
    routing_reason: str  # How routing decision was made
    priority: str = "medium"  # low, medium, high, critical
    context: Dict[str, Any] = Field(default_factory=dict)  # Contains source event data + additional context


# ===== UNIFIED AGENT EVENT SCHEMA (NEW) =====

class AgentEventType:
    """Standard agent event types (extensible)"""
    
    # Status events
    THINKING = "thinking"
    IDLE = "idle"
    WAITING = "waiting"
    ERROR = "error"
    
    # Activity events
    TOOL_CALL = "tool_call"
    PROGRESS = "progress"
    
    # Communication events
    RESPONSE = "response"
    DELEGATION = "delegation"
    QUESTION = "question"
    
    # Approval events
    APPROVAL_REQUEST = "approval_request"


class AgentEvent(BaseKafkaEvent):
    """
    Unified event schema for all agent communications.
    
    Replaces:
    - AgentProgressEvent
    - AgentResponseEvent
    - AgentStatusEvent
    - ToolCallEvent
    - AgentRoutingEvent
    - ApprovalRequestEvent
    
    This single schema handles all agent events with a flexible structure.
    """
    
    event_type: str  # "agent.thinking", "agent.tool_call", "agent.response", etc.
    
    # Agent identification
    agent_name: str
    agent_id: str
    
    # Execution context
    execution_id: Optional[UUID] = None  # Links events in same execution
    task_id: Optional[UUID] = None
    
    # Event payload
    content: str  # Human-readable message
    details: Dict[str, Any] = Field(default_factory=dict)  # Structured data


# EVENT REGISTRY
EVENT_TYPE_TO_SCHEMA = {
    "user.message.sent": UserMessageEvent,
    "agent.response.created": AgentResponseEvent,
    "agent.routing.delegated": AgentRoutingEvent,
    StoryEventType.CREATED.value: StoryEvent,
    StoryEventType.UPDATED.value: StoryEvent,
    StoryEventType.STATUS_CHANGED.value: StoryEvent,
    StoryEventType.ASSIGNED.value: StoryEvent,
    StoryEventType.DELETED.value: StoryEvent,
    "approval.request.created": ApprovalRequestEvent,
    "approval.response.submitted": ApprovalResponseEvent,
    "agent.question_asked": QuestionAskedEvent,
    "user.question_answer": QuestionAnswerEvent,
    FlowStatusType.STARTED.value: FlowStatusEvent,
    FlowStatusType.IN_PROGRESS.value: FlowStatusEvent,
    FlowStatusType.COMPLETED.value: FlowStatusEvent,
    FlowStatusType.FAILED.value: FlowStatusEvent,
    FlowStatusType.CANCELLED.value: FlowStatusEvent,
    # Agent events now use unified AgentEvent
    "agent.idle": AgentEvent,
    "agent.thinking": AgentEvent,
    "agent.acting": AgentEvent,
    "agent.waiting": AgentEvent,
    "agent.error": AgentEvent,
    "agent.progress": AgentEvent,
    "agent.tool_call": AgentEvent,
    "agent.task.assigned": AgentTaskEvent,
    "agent.task.started": AgentTaskEvent,
    "agent.task.progress": AgentTaskEvent,
    "agent.task.completed": AgentTaskEvent,
    "agent.task.failed": AgentTaskEvent,
    "agent.task.cancelled": AgentTaskEvent,
    "router.task.dispatched": RouterTaskEvent,
    # Unified agent events
    "agent.thinking": AgentEvent,
    "agent.idle": AgentEvent,
    "agent.waiting": AgentEvent,
    "agent.error": AgentEvent,
    "agent.tool_call": AgentEvent,
    "agent.progress": AgentEvent,
    "agent.response": AgentEvent,
    "agent.delegation": AgentEvent,
    "agent.question": AgentEvent,
    "agent.approval_request": AgentEvent,
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
