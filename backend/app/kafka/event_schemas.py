"""
Kafka event schemas and topic definitions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class KafkaTopics(str, Enum):
    """Kafka topic names."""

    USER_MESSAGES = "user_messages"
    AGENT_EVENTS = "agent_events"
    AGENT_TASKS = "agent_tasks"
    DOMAIN_EVENTS = "domain_events"
    STORY_EVENTS = "story_events"
    FLOW_STATUS = "flow_status"
    APPROVAL_RESPONSES = "approval_responses"
    QUESTION_ANSWERS = "question_answers"
    DELEGATION_REQUESTS = "delegation_requests"
    

class BaseKafkaEvent(BaseModel):
    """Base schema for all Kafka events."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserMessageEvent(BaseKafkaEvent):
    """User message to agents."""

    event_type: str = "user.message.sent"
    message_id: UUID
    content: str
    author_type: str = "USER"
    message_type: str = "text"
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None


class AgentResponseEvent(BaseKafkaEvent):
    """Agent response."""

    event_type: str = "agent.response.created"
    message_id: UUID
    task_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
    agent_name: str
    agent_type: str
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    approval_request_id: Optional[UUID] = None


class AgentRoutingEvent(BaseKafkaEvent):
    """TeamLeader delegation."""

    event_type: str = "agent.routing.delegated"
    from_agent: str
    to_agent: str
    delegation_reason: str
    context: Dict[str, Any] = Field(default_factory=dict)


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


class DelegationRequestEvent(BaseKafkaEvent):
    """Request to delegate task to agent by role (Router selects specific agent)."""
    
    event_type: str = "delegation.request"
    original_task_id: str
    delegating_agent_id: str
    delegating_agent_name: str
    target_role: str
    priority: str = "high"
    task_type: AgentTaskType
    content: str
    context: Dict[str, Any] = Field(default_factory=dict)
    delegation_message: Optional[str] = None
    source_event_type: str
    source_event_id: str


# STORY EVENTS
class StoryEventType(str, Enum):
    """Story event types."""

    CREATED = "story.created"
    UPDATED = "story.updated"
    STATUS_CHANGED = "story.status.changed"
    ASSIGNED = "story.assigned"
    DELETED = "story.deleted"


class StoryEvent(BaseKafkaEvent):
    """Unified story lifecycle event (created/updated/status.changed/assigned/deleted)."""
    
    event_type: str
    story_id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    story_type: Optional[str] = None
    status: Optional[str] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    transition_reason: Optional[str] = None
    updated_fields: Optional[Dict[str, Any]] = None
    assignee_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    epic_id: Optional[UUID] = None
    created_by_agent: Optional[str] = None
    updated_by: Optional[str] = None
    changed_by: Optional[str] = None
    assigned_by: Optional[str] = None


class ApprovalRequestEvent(BaseKafkaEvent):
    """Approval request."""

    event_type: str = "approval.request.created"
    approval_request_id: UUID
    request_type: str
    agent_name: str
    proposed_data: Dict[str, Any]
    explanation: Optional[str] = None


class ApprovalResponseEvent(BaseKafkaEvent):
    """Approval response."""

    event_type: str = "approval.response.submitted"
    approval_request_id: UUID
    approved: bool
    feedback: Optional[str] = None
    modified_data: Optional[Dict[str, Any]] = None


class QuestionAskedEvent(BaseKafkaEvent):
    """Agent clarification question."""
    
    event_type: str = "agent.question_asked"
    question_id: str
    agent_id: str
    agent_name: str
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    allow_multiple: bool = False
    task_id: str
    execution_id: Optional[str] = None


class QuestionAnswerEvent(BaseKafkaEvent):
    """User answer to question."""
    
    event_type: str = "user.question_answer"
    question_id: UUID
    answer: str
    selected_options: Optional[List[str]] = None
    agent_id: UUID
    task_id: UUID


class BatchQuestionsAskedEvent(BaseKafkaEvent):
    """Agent asks multiple questions at once (batch mode)."""
    
    event_type: str = "agent.question_batch_asked"
    batch_id: str
    question_ids: List[str]
    questions: List[dict]  # List of question dicts with question_text, question_type, options, etc.
    agent_id: str
    agent_name: str
    task_id: str
    execution_id: Optional[str] = None


class BatchAnswersEvent(BaseKafkaEvent):
    """User answers multiple questions at once (batch mode)."""
    
    event_type: str = "user.question_batch_answer"
    batch_id: str
    answers: List[dict]  # List of { question_id, answer, selected_options }
    agent_id: UUID
    task_id: UUID


class ConversationOwnershipChangedEvent(BaseKafkaEvent):
    """Conversation ownership transferred to new agent (MetaGPT-style)."""
    
    event_type: str = "conversation.ownership_changed"
    project_id: str
    previous_agent_id: Optional[UUID] = None
    previous_agent_name: Optional[str] = None
    new_agent_id: UUID
    new_agent_name: str
    reason: str  # "task_started", "delegated", "completed_handoff"


class ConversationOwnershipReleasedEvent(BaseKafkaEvent):
    """Agent releases conversation ownership."""
    
    event_type: str = "conversation.ownership_released"
    project_id: str
    agent_id: UUID
    agent_name: str
    reason: str  # "task_completed", "error", "timeout"


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


class AgentTaskStatus(str, Enum):
    """Status of agent tasks."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTaskEvent(BaseKafkaEvent):
    """Unified task lifecycle event (assigned/started/progress/completed/failed/cancelled)."""
    
    event_type: str
    task_id: UUID
    agent_id: UUID
    agent_name: str
    task_type: AgentTaskType
    status: AgentTaskStatus
    context: Dict[str, Any] = Field(default_factory=dict)
    assigned_by: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    story_id: Optional[UUID] = None
    epic_id: Optional[UUID] = None
    estimated_duration: Optional[int] = None
    due_date: Optional[datetime] = None
    execution_id: Optional[UUID] = None
    started_at: Optional[datetime] = None
    progress_percentage: Optional[int] = None
    current_step: Optional[str] = None
    steps_completed: Optional[int] = None
    total_steps: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    retry_count: Optional[int] = None
    can_retry: Optional[bool] = None
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    reason: Optional[str] = None


class RouterTaskEvent(BaseKafkaEvent):
    """Router task dispatch to agents."""

    event_type: str = "router.task.dispatched"
    task_id: UUID = Field(default_factory=uuid4)
    task_type: AgentTaskType
    agent_id: UUID
    agent_role: Optional[str] = None
    source_event_type: str
    source_event_id: str
    routing_reason: str
    priority: str = "medium"
    context: Dict[str, Any] = Field(default_factory=dict)


class AgentEventType:
    """Agent event types."""
    
    THINKING = "thinking"
    IDLE = "idle"
    WAITING = "waiting"
    ERROR = "error"
    TOOL_CALL = "tool_call"
    PROGRESS = "progress"
    RESPONSE = "response"
    DELEGATION = "delegation"
    QUESTION = "question"
    APPROVAL_REQUEST = "approval_request"


class AgentEvent(BaseKafkaEvent):
    """Unified agent event (status/progress/tool_call/response/delegation)."""
    
    event_type: str
    agent_name: str
    agent_id: str
    execution_id: Optional[str] = None
    task_id: Optional[str] = None
    content: str
    details: Dict[str, Any] = Field(default_factory=dict)


# EVENT REGISTRY
EVENT_TYPE_TO_SCHEMA = {
    "user.message.sent": UserMessageEvent,
    "agent.response.created": AgentResponseEvent,
    "agent.routing.delegated": AgentRoutingEvent,
    "delegation.request": DelegationRequestEvent,
    StoryEventType.CREATED.value: StoryEvent,
    StoryEventType.UPDATED.value: StoryEvent,
    StoryEventType.STATUS_CHANGED.value: StoryEvent,
    StoryEventType.ASSIGNED.value: StoryEvent,
    StoryEventType.DELETED.value: StoryEvent,
    "approval.request.created": ApprovalRequestEvent,
    "approval.response.submitted": ApprovalResponseEvent,
    "agent.question_asked": QuestionAskedEvent,
    "user.question_answer": QuestionAnswerEvent,
    "agent.question_batch_asked": BatchQuestionsAskedEvent,
    "user.question_batch_answer": BatchAnswersEvent,
    "conversation.ownership_changed": ConversationOwnershipChangedEvent,
    "conversation.ownership_released": ConversationOwnershipReleasedEvent,
    FlowStatusType.STARTED.value: FlowStatusEvent,
    FlowStatusType.IN_PROGRESS.value: FlowStatusEvent,
    FlowStatusType.COMPLETED.value: FlowStatusEvent,
    FlowStatusType.FAILED.value: FlowStatusEvent,
    FlowStatusType.CANCELLED.value: FlowStatusEvent,
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
