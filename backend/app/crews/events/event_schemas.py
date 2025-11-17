"""
Event system configuration for CrewAI agents

Defines Kafka topics, Redis keys, and event schemas
"""

from pydantic import BaseModel
from typing import Literal, Any, Optional
from datetime import datetime
from uuid import UUID

# Kafka Topics
class KafkaTopics:
    """Kafka topic names"""
    CREW_EVENTS = "crew.events"      # General crew lifecycle events
    TASK_QUEUE = "crew.tasks"        # Task assignment queue
    TASK_RESULTS = "crew.results"    # Task completion results
    FLOW_STATUS = "crew.flow.status" # Flow execution status updates
    AGENT_STATUS = "crew.agent.status"  # Agent health/status updates

    # New topics for agent routing
    USER_MESSAGES = "user.messages"  # User input messages
    AGENT_TASKS_BA = "agent.tasks.ba"  # Tasks for Business Analyst
    AGENT_TASKS_DEV = "agent.tasks.dev"  # Tasks for Developer
    AGENT_TASKS_TESTER = "agent.tasks.tester"  # Tasks for Tester
    AGENT_TASKS_LEADER = "agent.tasks.leader"  # Tasks for Team Leader
    AGENT_RESPONSES = "agent.responses"  # Agent responses
    AGENT_ROUTING = "agent.routing"  # Routing decisions
    STORY_EVENTS = "story.events"  # Story lifecycle events

# Redis Keys
class RedisKeys:
    """Redis key patterns"""
    TASK_QUEUE_PREFIX = "tasks:"      # tasks:{agent_id} - task queue for each agent
    FLOW_STATE_PREFIX = "flow:state:" # flow:state:{flow_id} - flow execution state
    AGENT_STATUS_PREFIX = "agent:status:"  # agent:status:{agent_id} - agent status
    TASK_RESULT_PREFIX = "task:result:"    # task:result:{task_id} - task results

# Event Schemas
class EventType:
    """Event type constants"""
    # Task events
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Flow events
    FLOW_STARTED = "flow.started"
    FLOW_STEP_COMPLETED = "flow.step.completed"
    FLOW_COMPLETED = "flow.completed"
    FLOW_FAILED = "flow.failed"

    # Agent events
    AGENT_ONLINE = "agent.online"
    AGENT_OFFLINE = "agent.offline"
    AGENT_BUSY = "agent.busy"
    AGENT_IDLE = "agent.idle"

class BaseEvent(BaseModel):
    """Base event schema"""
    event_id: str
    event_type: str
    timestamp: datetime
    source: str  # agent_id or flow_id
    data: dict[str, Any]

class TaskCreatedEvent(BaseModel):
    """Event emitted when a new task is created"""
    event_type: Literal["task.created"] = "task.created"
    task_id: str
    task_type: str  # "analyze_requirements", "implement_feature", "run_tests", etc.
    project_id: UUID
    priority: int = 5  # 1-10, higher is more important
    assigned_to: Optional[str] = None  # agent_id
    created_by: str  # user_id or agent_id
    input_data: dict[str, Any]
    timestamp: datetime = datetime.utcnow()

class TaskAssignedEvent(BaseModel):
    """Event emitted when a task is assigned to an agent"""
    event_type: Literal["task.assigned"] = "task.assigned"
    task_id: str
    assigned_to: str  # agent_id
    assigned_by: str  # flow_id or user_id
    timestamp: datetime = datetime.utcnow()

class TaskCompletedEvent(BaseModel):
    """Event emitted when a task is completed"""
    event_type: Literal["task.completed"] = "task.completed"
    task_id: str
    agent_id: str
    result: dict[str, Any]
    execution_time_ms: int
    timestamp: datetime = datetime.utcnow()

class TaskFailedEvent(BaseModel):
    """Event emitted when a task fails"""
    event_type: Literal["task.failed"] = "task.failed"
    task_id: str
    agent_id: str
    error_message: str
    error_type: str
    retry_count: int = 0
    timestamp: datetime = datetime.utcnow()

class FlowStartedEvent(BaseModel):
    """Event emitted when a flow starts execution"""
    event_type: Literal["flow.started"] = "flow.started"
    flow_id: str
    flow_type: str  # "development_flow", etc.
    project_id: UUID
    triggered_by: str  # user_id
    input_state: dict[str, Any]
    timestamp: datetime = datetime.utcnow()

class FlowStepCompletedEvent(BaseModel):
    """Event emitted when a flow step completes"""
    event_type: Literal["flow.step.completed"] = "flow.step.completed"
    flow_id: str
    step_name: str
    output: dict[str, Any]
    next_step: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

class FlowCompletedEvent(BaseModel):
    """Event emitted when a flow completes successfully"""
    event_type: Literal["flow.completed"] = "flow.completed"
    flow_id: str
    final_state: dict[str, Any]
    total_execution_time_ms: int
    timestamp: datetime = datetime.utcnow()

class AgentStatusEvent(BaseModel):
    """Event emitted when agent status changes"""
    event_type: str  # agent.online, agent.offline, agent.busy, agent.idle
    agent_id: str
    agent_type: str  # "team_leader", "business_analyst", "developer", "tester"
    status: Literal["online", "offline", "busy", "idle"]
    current_task_id: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

# New event schemas for agent routing
class UserMessageEvent(BaseModel):
    """Event emitted when user sends a message"""
    event_type: Literal["user.message"] = "user.message"
    message_id: UUID
    project_id: UUID
    user_id: UUID
    content: str
    metadata: Optional[dict[str, Any]] = None
    timestamp: datetime = datetime.utcnow()

class AgentTaskEvent(BaseModel):
    """Event emitted when a task is assigned to an agent"""
    event_type: Literal["agent.task"] = "agent.task"
    task_id: UUID
    agent_type: Literal["ba", "dev", "tester", "leader"]  # Target agent
    project_id: UUID
    user_message_id: UUID
    task_description: str
    context: dict[str, Any]
    timestamp: datetime = datetime.utcnow()

class AgentResponseEvent(BaseModel):
    """Event emitted when agent sends a response"""
    event_type: Literal["agent.response"] = "agent.response"
    response_id: UUID
    task_id: UUID
    agent_type: str
    project_id: UUID
    content: str
    structured_data: Optional[dict[str, Any]] = None  # For story previews, etc.
    metadata: Optional[dict[str, Any]] = None
    timestamp: datetime = datetime.utcnow()

class AgentRoutingEvent(BaseModel):
    """Event emitted when router decides where to route a message"""
    event_type: Literal["agent.routing"] = "agent.routing"
    message_id: UUID
    project_id: UUID
    routed_to: str  # Agent type: "ba", "dev", "tester", "leader"
    routing_reason: str  # Why this agent was chosen
    confidence: float  # 0.0-1.0
    timestamp: datetime = datetime.utcnow()

class StoryCreatedEvent(BaseModel):
    """Event emitted when a story is created"""
    event_type: Literal["story.created"] = "story.created"
    story_id: UUID
    project_id: UUID
    title: str
    status: str
    created_by: UUID
    timestamp: datetime = datetime.utcnow()

class StoryUpdatedEvent(BaseModel):
    """Event emitted when a story is updated"""
    event_type: Literal["story.updated"] = "story.updated"
    story_id: UUID
    project_id: UUID
    changes: dict[str, Any]  # What fields changed
    updated_by: UUID
    timestamp: datetime = datetime.utcnow()

class StoryStatusChangedEvent(BaseModel):
    """Event emitted when a story status changes"""
    event_type: Literal["story.status.changed"] = "story.status.changed"
    story_id: UUID
    project_id: UUID
    old_status: str
    new_status: str
    changed_by: UUID
    timestamp: datetime = datetime.utcnow()
