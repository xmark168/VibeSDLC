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
    AgentResponseEvent,
    AgentRoutingEvent,
    AgentStatusEvent,
    AgentStatusType,
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
    UserMessageEvent,
    get_event_schema,
)
from app.kafka.producer import KafkaProducer, get_kafka_producer, shutdown_kafka_producer

__all__ = [
    # Producer
    "KafkaProducer",
    "get_kafka_producer",
    "shutdown_kafka_producer",
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
    "StoryCreatedEvent",
    "StoryUpdatedEvent",
    "StoryStatusChangedEvent",
    "StoryAssignedEvent",
    "StoryEventType",
    "ApprovalRequestEvent",
    "ApprovalResponseEvent",
    "FlowStatusEvent",
    "FlowStatusType",
    "get_event_schema",
]
