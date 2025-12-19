"""
Kafka event schemas and topic definitions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class KafkaTopics(str, Enum):
    """Kafka topic names."""

    USER_MESSAGES = "user_messages"
    AGENT_EVENTS = "agent_events"
    AGENT_TASKS = "agent_tasks"
    DOMAIN_EVENTS = "domain_events"
    STORY_EVENTS = "story_events"
    FLOW_STATUS = "flow_status"
    QUESTION_ANSWERS = "question_answers"
    DELEGATION_REQUESTS = "delegation_requests"
    AGENT_COLLABORATION = "agent_collaboration"  # Cross-agent collaboration
    

class BaseKafkaEvent(BaseModel):
    """Base schema for all Kafka events."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('event_id', 'project_id', 'user_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Auto-convert UUID to string."""
        if isinstance(v, UUID):
            return str(v)
        return v


class UserMessageEvent(BaseKafkaEvent):
    """User message to agents."""

    event_type: str = "user.message.sent"
    message_id: UUID
    content: str
    author_type: str = "USER"
    message_type: str = "text"
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None  # File attachments with extracted text


class AgentTaskType(str, Enum):
    """Types of tasks that can be assigned to agents."""

    # Specific task types
    CODE_REVIEW = "code_review"
    IMPLEMENT_STORY = "implement_story"
    REVIEW_PR = "review_pr"  # Review PR for conflicts/errors before merge
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
    # Task control events
    CANCEL = "story.cancel"
    PAUSE = "story.pause"
    RESUME = "story.resume"
    REVIEW_ACTION = "story.review_action"


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


class StoryAgentStateEvent(BaseKafkaEvent):
    """Agent execution state changed on a story."""
    
    event_type: str = "story.agent_state.changed"
    story_id: UUID
    agent_state: str  # "pending" | "processing" | "canceled" | "finished"
    old_state: Optional[str] = None
    agent_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    progress_message: Optional[str] = None  # Optional status message


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
    proposed_data: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    task_id: str
    execution_id: Optional[str] = None


class QuestionAnswerEvent(BaseKafkaEvent):
    """User answer to question."""
    
    event_type: str = "user.question_answer"
    question_id: UUID
    answer: str
    selected_options: Optional[List[str]] = None
    approved: Optional[bool] = None
    modified_data: Optional[Dict[str, Any]] = None
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
    """Unified task lifecycle event (assigned/started/progress/completed/failed/cancelled).
    
    Slimmed down from 30 fields to 15 core fields.
    Status-specific data moved to 'details' dict for flexibility.
    """
    
    event_type: str
    task_id: UUID
    agent_id: UUID
    agent_name: str
    task_type: AgentTaskType
    status: AgentTaskStatus
    story_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
    priority: str = "medium"
    context: Dict[str, Any] = Field(default_factory=dict)
    # All status-specific fields moved here:
    # - assigned: assigned_by, title, description
    # - progress: progress_percentage, current_step, steps_completed, total_steps
    # - completed: completed_at, duration_seconds, result, artifacts
    # - failed: failed_at, error_message, error_type, retry_count, can_retry
    # - cancelled: cancelled_by, cancelled_at, reason
    details: Dict[str, Any] = Field(default_factory=dict)


class TaskRejectionEvent(BaseKafkaEvent):
    """Event published when agent rejects a task due to queue overflow."""
    
    event_type: str = "agent.task.rejected"
    task_id: UUID
    agent_id: UUID
    agent_name: str
    reason: str  # "queue_full", "resource_unavailable", etc.
    queue_size: int
    max_queue_size: int
    details: Dict[str, Any] = Field(default_factory=dict)


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


class AgentEvent(BaseKafkaEvent):
    """Unified agent event (status/progress/tool_call/response/delegation)."""
    
    event_type: str
    agent_name: str
    agent_id: str
    execution_id: Optional[str] = None
    task_id: Optional[str] = None
    content: str
    details: Dict[str, Any] = Field(default_factory=dict)
    execution_context: Optional[Dict[str, Any]] = Field(default_factory=dict)  # NEW: mode, task_type, display_mode


# EVENT REGISTRY
EVENT_TYPE_TO_SCHEMA = {
    # User events
    "user.message.sent": UserMessageEvent,
    
    # Agent events (unified)
    "agent.response": AgentEvent,
    "agent.response.created": AgentEvent,  # Legacy alias
    "agent.routing.delegated": DelegationRequestEvent,  # Legacy alias
    "agent.idle": AgentEvent,
    "agent.thinking": AgentEvent,
    "agent.acting": AgentEvent,
    "agent.waiting": AgentEvent,
    "agent.error": AgentEvent,
    "agent.progress": AgentEvent,
    "agent.tool_call": AgentEvent,
    "agent.delegation": AgentEvent,
    "agent.question": AgentEvent,
    "agent.completed": AgentEvent,
    
    # Delegation events
    "delegation.request": DelegationRequestEvent,
    
    # Story events
    StoryEventType.CREATED.value: StoryEvent,
    StoryEventType.UPDATED.value: StoryEvent,
    StoryEventType.STATUS_CHANGED.value: StoryEvent,
    StoryEventType.ASSIGNED.value: StoryEvent,
    StoryEventType.DELETED.value: StoryEvent,
    StoryEventType.CANCEL.value: StoryEvent,
    StoryEventType.PAUSE.value: StoryEvent,
    StoryEventType.RESUME.value: StoryEvent,
    StoryEventType.REVIEW_ACTION.value: StoryEvent,
    "story.agent_state.changed": StoryAgentStateEvent,
    "story.review_action": StoryEvent,  # Use unified StoryEvent
    
    # Question events
    "agent.question_asked": QuestionAskedEvent,
    "user.question_answer": QuestionAnswerEvent,
    "agent.question_batch_asked": BatchQuestionsAskedEvent,
    "user.question_batch_answer": BatchAnswersEvent,
    
    # Conversation events
    "conversation.ownership_changed": ConversationOwnershipChangedEvent,
    "conversation.ownership_released": ConversationOwnershipReleasedEvent,
    
    # Flow events
    FlowStatusType.STARTED.value: FlowStatusEvent,
    FlowStatusType.IN_PROGRESS.value: FlowStatusEvent,
    FlowStatusType.COMPLETED.value: FlowStatusEvent,
    FlowStatusType.FAILED.value: FlowStatusEvent,
    FlowStatusType.CANCELLED.value: FlowStatusEvent,
    
    # Task events
    "agent.task.assigned": AgentTaskEvent,
    "agent.task.started": AgentTaskEvent,
    "agent.task.progress": AgentTaskEvent,
    "agent.task.completed": AgentTaskEvent,
    "agent.task.failed": AgentTaskEvent,
    "agent.task.cancelled": AgentTaskEvent,
    "router.task.dispatched": RouterTaskEvent,
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
