"""Kafka topics definitions for VibeSDLC"""

from enum import Enum


class KafkaTopics(str, Enum):
    """Kafka topic names"""

    # Agent communication topics
    AGENT_TASKS = "agent_tasks"
    AGENT_RESPONSES = "agent_responses"

    # Story events topics
    STORY_CREATED = "story_created"
    STORY_UPDATED = "story_updated"
    STORY_STATUS_CHANGED = "story_status_changed"
    STORY_ASSIGNED = "story_assigned"

    # Agent coordination
    AGENT_STATUS = "agent_status"
    AGENT_HEARTBEAT = "agent_heartbeat"


# Topic configurations
TOPIC_CONFIGS = {
    KafkaTopics.AGENT_TASKS: {
        "num_partitions": 3,
        "replication_factor": 1,
    },
    KafkaTopics.AGENT_RESPONSES: {
        "num_partitions": 3,
        "replication_factor": 1,
    },
    KafkaTopics.STORY_CREATED: {
        "num_partitions": 2,
        "replication_factor": 1,
    },
    KafkaTopics.STORY_UPDATED: {
        "num_partitions": 2,
        "replication_factor": 1,
    },
    KafkaTopics.STORY_STATUS_CHANGED: {
        "num_partitions": 2,
        "replication_factor": 1,
    },
    KafkaTopics.STORY_ASSIGNED: {
        "num_partitions": 2,
        "replication_factor": 1,
    },
    KafkaTopics.AGENT_STATUS: {
        "num_partitions": 1,
        "replication_factor": 1,
    },
    KafkaTopics.AGENT_HEARTBEAT: {
        "num_partitions": 1,
        "replication_factor": 1,
    },
}
