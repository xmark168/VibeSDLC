"""
Kafka producer singleton for publishing events.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from uuid import UUID

from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from pydantic import BaseModel

from app.core.config import settings, kafka_settings
from app.kafka.event_schemas import BaseKafkaEvent, KafkaTopics

logger = logging.getLogger(__name__)


class UUIDEncoder(json.JSONEncoder):
    """JSON encoder that handles UUID serialization."""
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


class KafkaProducer:
    """Singleton Kafka producer with automatic topic creation and event validation."""

    _instance: Optional["KafkaProducer"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """Initialize Kafka producer with configuration from settings."""
        if KafkaProducer._instance is not None:
            raise RuntimeError("Use get_kafka_producer() to get singleton instance")

        self.config = {
            "bootstrap.servers": kafka_settings.BOOTSTRAP_SERVERS,
            "client.id": f"vibeSDLC-producer-{settings.ENVIRONMENT}",
            "acks": "all",  # Wait for all in-sync replicas
            "retries": 3,
            "retry.backoff.ms": 1000,
            "compression.type": "snappy",
            "enable.idempotence": True,  # Exactly-once semantics
        }

        # Add SASL authentication if configured
        if kafka_settings.SASL_MECHANISM:
            self.config.update({
                "security.protocol": kafka_settings.SECURITY_PROTOCOL,
                "sasl.mechanism": kafka_settings.SASL_MECHANISM,
                "sasl.username": kafka_settings.SASL_USERNAME,
                "sasl.password": kafka_settings.SASL_PASSWORD,
            })

        self.producer: Optional[Producer] = None
        self.admin_client: Optional[AdminClient] = None
        self._delivery_reports: Dict[str, Any] = {}

    async def initialize(self):
        """Initialize Kafka producer and create topics if needed."""
        try:
            self.producer = Producer(self.config)
            self.admin_client = AdminClient({
                "bootstrap.servers": kafka_settings.BOOTSTRAP_SERVERS
            })

            # Topics are now created by ensure_kafka_topics() in main.py startup
            # But keep this as backup for lazy initialization
            await self._create_topics()
            logger.info("Kafka producer initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    async def _create_topics(self):
        """Create Kafka topics if they don't exist."""
        try:
            # Get existing topics
            metadata = self.admin_client.list_topics(timeout=10)
            existing_topics = set(metadata.topics.keys())

            # Define topics to create with optimized partition counts
            # High-traffic topics get 6 partitions for better load distribution
            high_traffic_topics = {
                KafkaTopics.AGENT_EVENTS,      # Unified agent events stream
                KafkaTopics.AGENT_TASKS,
                KafkaTopics.USER_MESSAGES,
            }

            topics_to_create = []
            for topic in KafkaTopics:
                if topic.value not in existing_topics:
                    # High-traffic topics get 6 partitions, others get 3
                    num_partitions = 6 if topic in high_traffic_topics else 3

                    topics_to_create.append(
                        NewTopic(
                            topic=topic.value,
                            num_partitions=num_partitions,
                            replication_factor=1,  # Adjust for production
                            config={
                                "retention.ms": str(7 * 24 * 60 * 60 * 1000),  # 7 days
                                "cleanup.policy": "delete",
                            }
                        )
                    )

            if topics_to_create:
                fs = self.admin_client.create_topics(topics_to_create)
                for topic, f in fs.items():
                    try:
                        f.result()  # Wait for operation to finish
                        logger.info(f"Topic {topic} created successfully")
                    except Exception as e:
                        logger.warning(f"Failed to create topic {topic}: {e}")
            else:
                logger.info("All Kafka topics already exist")

        except Exception as e:
            logger.error(f"Error creating Kafka topics: {e}")
            # Don't raise - topics might exist already

    def _delivery_report(self, err, msg):
        """Callback for delivery reports from Kafka."""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
            self._delivery_reports[msg.key()] = {"status": "failed", "error": str(err)}
        else:
            self._delivery_reports[msg.key()] = {
                "status": "success",
                "partition": msg.partition(),
                "offset": msg.offset(),
            }

    async def publish(
        self,
        topic: KafkaTopics | str,
        event: BaseKafkaEvent | Dict[str, Any],
        key: Optional[str] = None,
    ) -> bool:
        """Publish an event to Kafka topic.

        PARTITION KEY STRATEGY:
        - Primary: project_id (ensures all events for a project go to same partition)
        - Fallback: event_id (if no project_id available)
        - Override: Explicitly provided key parameter

        Args:
            topic: Kafka topic (enum or string)
            event: Event to publish (Pydantic model or dict)
            key: Optional partition key (overrides auto-detection)

        Returns:
            bool: True if published successfully, False otherwise
        """
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return False

        try:
            # Convert topic enum to string
            topic_str = topic.value if isinstance(topic, KafkaTopics) else topic

            # Serialize event
            if isinstance(event, BaseModel):
                event_data = event.model_dump(mode="json")
            else:
                event_data = event

            # HYBRID PARTITION KEY STRATEGY
            # AGENT_TASKS: partition by agent_id (one partition per agent)
            # OTHER TOPICS: partition by project_id (ordering within project)
            # Priority: explicit key > agent_id (for AGENT_TASKS) > project_id > event_id
            if not key:
                # Special handling for AGENT_TASKS topic
                if topic_str == "agent_tasks":
                    # Use agent_id for task partitioning
                    agent_id = event_data.get("agent_id")
                    if agent_id:
                        key = str(agent_id) if isinstance(agent_id, UUID) else agent_id

                # For all other topics or if agent_id not available, use project_id
                if not key:
                    project_id = event_data.get("project_id")
                    if project_id:
                        key = str(project_id) if isinstance(project_id, UUID) else project_id
                    else:
                        # Final fallback to event_id
                        event_id = event_data.get("event_id")
                        if event_id:
                            key = str(event_id) if isinstance(event_id, UUID) else event_id

            # Serialize to JSON with UUID handling
            message_value = json.dumps(event_data, cls=UUIDEncoder).encode("utf-8")
            message_key = key.encode("utf-8") if key else None

            # Ensure topic exists before publishing
            try:
                metadata = self.admin_client.list_topics(timeout=5)
                if topic_str not in metadata.topics:
                    # Create topic on-the-fly if it doesn't exist
                    logger.warning(f"Topic {topic_str} not found, creating it...")

                    # Determine partitions based on topic type
                    high_traffic = topic_str in [
                        "agent_responses", "agent_status", "agent_progress",
                        "agent_tasks", "user_messages"
                    ]
                    num_partitions = 6 if high_traffic else 3

                    new_topic = NewTopic(
                        topic=topic_str,
                        num_partitions=num_partitions,
                        replication_factor=1,
                        config={
                            "retention.ms": str(7 * 24 * 60 * 60 * 1000),
                            "cleanup.policy": "delete",
                        }
                    )
                    fs = self.admin_client.create_topics([new_topic])
                    for t, f in fs.items():
                        f.result()  # Wait for creation
                        logger.info(f"Created topic {t} on-the-fly with {num_partitions} partitions")
            except Exception as e:
                logger.warning(f"Could not verify/create topic {topic_str}: {e}")

            # Publish to Kafka
            self.producer.produce(
                topic=topic_str,
                value=message_value,
                key=message_key,
                callback=self._delivery_report,
            )

            # Poll to handle delivery reports
            self.producer.poll(0)

            logger.info(f"Published event to {topic_str}: {event_data.get('event_type')}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event to {topic}: {e}", exc_info=True)
            return False

    async def flush(self, timeout: float = 10.0):
        """Flush pending messages.

        Args:
            timeout: Maximum time to wait for pending messages (seconds)
        """
        if self.producer:
            remaining = self.producer.flush(timeout)
            if remaining > 0:
                logger.warning(f"{remaining} messages were not delivered")
            else:
                logger.info("All messages flushed successfully")

    async def close(self):
        """Close Kafka producer and flush pending messages."""
        if self.producer:
            await self.flush()
            self.producer = None
            logger.info("Kafka producer closed")

    @classmethod
    async def get_instance(cls) -> "KafkaProducer":
        """Get singleton instance of KafkaProducer.

        Returns:
            Initialized KafkaProducer instance
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = KafkaProducer()
                    await cls._instance.initialize()
        return cls._instance


# GLOBAL PRODUCER INSTANCE
_producer_instance: Optional[KafkaProducer] = None


async def get_kafka_producer() -> KafkaProducer:
    """Get the global Kafka producer instance.

    Returns:
        Initialized KafkaProducer singleton
    """
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = await KafkaProducer.get_instance()
    return _producer_instance


async def shutdown_kafka_producer():
    """Shutdown the global Kafka producer instance."""
    global _producer_instance
    if _producer_instance:
        await _producer_instance.close()
        _producer_instance = None
