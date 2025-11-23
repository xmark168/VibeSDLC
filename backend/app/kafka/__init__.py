"""Kafka package initialization.

Provides easy imports for Kafka components.
"""

from app.kafka.consumer import BaseKafkaConsumer, EventHandlerConsumer
from app.kafka.consumer_registry import (
    get_consumer_registry,
    setup_consumers,
    shutdown_all_consumers,
    start_all_consumers,
)
from app.kafka.event_schemas import (
    AgentProgressEvent,
    AgentResponseEvent,
    AgentRoutingEvent,
    AgentStatusEvent,
    AgentStatusType,
    AgentTaskAssignedEvent,
    AgentTaskCancelledEvent,
    AgentTaskCompletedEvent,
    AgentTaskFailedEvent,
    AgentTaskProgressEvent,
    AgentTaskStartedEvent,
    AgentTaskStatus,
    AgentTaskType,
    ApprovalRequestEvent,
    ApprovalResponseEvent,
    BaseKafkaEvent,
    FlowStatusEvent,
    FlowStatusType,
    KafkaTopics,
    StoryAssignedEvent,
    StoryCreatedEvent,
    StoryEventType,
    StoryStatusChangedEvent,
    StoryUpdatedEvent,
    ToolCallEvent,
    UserMessageEvent,
    get_event_schema,
)
from app.kafka.producer import KafkaProducer, get_kafka_producer, shutdown_kafka_producer
from app.kafka.ensure_topics import ensure_kafka_topics

__all__ = [
    # Producer
    "KafkaProducer",
    "get_kafka_producer",
    "shutdown_kafka_producer",
    # Topics
    "ensure_kafka_topics",
    # Consumer
    "BaseKafkaConsumer",
    "EventHandlerConsumer",
    "get_consumer_registry",
    "setup_consumers",
    "start_all_consumers",
    "shutdown_all_consumers",
    # Event Schemas
    "BaseKafkaEvent",
    "KafkaTopics",
    "UserMessageEvent",
    "AgentResponseEvent",
    "AgentRoutingEvent",
    "AgentStatusEvent",
    "AgentStatusType",
    "AgentProgressEvent",
    "StoryCreatedEvent",
    "StoryUpdatedEvent",
    "StoryStatusChangedEvent",
    "StoryAssignedEvent",
    "StoryEventType",
    "ApprovalRequestEvent",
    "ApprovalResponseEvent",
    "FlowStatusEvent",
    "FlowStatusType",
    "ToolCallEvent",
    # Agent Task Events
    "AgentTaskType",
    "AgentTaskStatus",
    "AgentTaskAssignedEvent",
    "AgentTaskStartedEvent",
    "AgentTaskProgressEvent",
    "AgentTaskCompletedEvent",
    "AgentTaskFailedEvent",
    "AgentTaskCancelledEvent",
    # Utils
    "get_event_schema",
]
