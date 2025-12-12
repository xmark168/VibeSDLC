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
    AgentEvent,
    AgentTaskEvent,
    AgentTaskStatus,
    AgentTaskType,
    BaseKafkaEvent,
    BatchAnswersEvent,
    BatchQuestionsAskedEvent,
    ConversationOwnershipChangedEvent,
    ConversationOwnershipReleasedEvent,
    DelegationRequestEvent,
    FlowStatusEvent,
    FlowStatusType,
    KafkaTopics,
    QuestionAskedEvent,
    QuestionAnswerEvent,
    RouterTaskEvent,
    StoryEvent,
    StoryEventType,
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
    "AgentEvent",
    "DelegationRequestEvent",
    "StoryEvent",
    "StoryEventType",
    "FlowStatusEvent",
    "FlowStatusType",
    "QuestionAskedEvent",
    "QuestionAnswerEvent",
    "BatchQuestionsAskedEvent",
    "BatchAnswersEvent",
    "ConversationOwnershipChangedEvent",
    "ConversationOwnershipReleasedEvent",
    "RouterTaskEvent",
    # Agent Task Events (Unified)
    "AgentTaskType",
    "AgentTaskStatus",
    "AgentTaskEvent",
    # Utils
    "get_event_schema",
]
