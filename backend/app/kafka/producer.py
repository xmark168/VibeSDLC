"""Kafka Producer service for VibeSDLC"""

import json
import logging
from typing import Any, Dict, Optional
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from app.kafka.config import kafka_settings
from app.kafka.topics import KafkaTopics, TOPIC_CONFIGS
from app.kafka.schemas import AgentTask, AgentResponse, StoryEvent, AgentStatusMessage

logger = logging.getLogger(__name__)


class KafkaProducerService:
    """Kafka Producer Service for publishing messages"""

    def __init__(self):
        self.producer: Optional[Producer] = None
        self.admin_client: Optional[AdminClient] = None
        self._initialized = False

    def initialize(self):
        """Initialize Kafka producer and create topics"""
        if not kafka_settings.KAFKA_ENABLED:
            logger.info("Kafka is disabled. Skipping producer initialization.")
            return

        try:
            logger.info(f"Connecting to Kafka at {kafka_settings.KAFKA_BOOTSTRAP_SERVERS}")

            # Producer configuration
            producer_config = {
                'bootstrap.servers': kafka_settings.KAFKA_BOOTSTRAP_SERVERS,
                'client.id': kafka_settings.KAFKA_CLIENT_ID,
                'acks': kafka_settings.KAFKA_PRODUCER_ACKS,
                'retries': kafka_settings.KAFKA_PRODUCER_RETRIES,
                'compression.type': kafka_settings.KAFKA_PRODUCER_COMPRESSION_TYPE,
            }

            logger.info("Creating Kafka producer...")
            self.producer = Producer(producer_config)
            logger.info("✓ Producer created")

            # Admin client for topic management
            admin_config = {
                'bootstrap.servers': kafka_settings.KAFKA_BOOTSTRAP_SERVERS,
            }
            logger.info("Creating Kafka admin client...")
            self.admin_client = AdminClient(admin_config)
            logger.info(f"✓ Admin client created: {self.admin_client is not None}")

            # Create topics
            logger.info("Creating topics...")
            self._create_topics()

            self._initialized = True
            logger.info("Kafka producer initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def _create_topics(self):
        """Create Kafka topics if they don't exist"""
        if not self.admin_client:
            logger.warning("Admin client not initialized, skipping topic creation")
            return

        try:
            # Get existing topics
            logger.info("Listing existing Kafka topics...")
            metadata = self.admin_client.list_topics(timeout=10)
            existing_topics = set(metadata.topics.keys())
            logger.info(f"Existing topics: {existing_topics}")

            # Create new topics
            new_topics = []
            for topic, config in TOPIC_CONFIGS.items():
                if topic.value not in existing_topics:
                    logger.info(f"Preparing to create topic: {topic.value}")
                    new_topic = NewTopic(
                        topic.value,
                        num_partitions=config["num_partitions"],
                        replication_factor=config["replication_factor"]
                    )
                    new_topics.append(new_topic)

            if new_topics:
                logger.info(f"Creating {len(new_topics)} new topics...")
                fs = self.admin_client.create_topics(new_topics, request_timeout=30.0)
                for topic, f in fs.items():
                    try:
                        f.result(timeout=30)  # Wait for creation with timeout
                        logger.info(f"✓ Topic '{topic}' created successfully")
                    except Exception as e:
                        logger.error(f"✗ Failed to create topic '{topic}': {e}")
            else:
                logger.info("All topics already exist")

        except Exception as e:
            logger.error(f"Error in topic creation process: {e}")

    def _delivery_callback(self, err, msg):
        """Callback for message delivery reports"""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def send_message(self, topic: KafkaTopics, message: Dict[str, Any], key: Optional[str] = None):
        """Send a message to Kafka topic"""
        if not self._initialized or not self.producer:
            logger.warning("Kafka producer not initialized. Message not sent.")
            return

        try:
            # Serialize message to JSON
            value = json.dumps(message, default=str).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None

            # Produce message
            self.producer.produce(
                topic.value,
                value=value,
                key=key_bytes,
                callback=self._delivery_callback
            )

            # Trigger delivery reports
            self.producer.poll(0)

        except Exception as e:
            logger.error(f"Failed to send message to {topic.value}: {e}")
            raise

    def send_agent_task(self, task: AgentTask):
        """Send agent task message"""
        message = task.model_dump(mode='json')
        self.send_message(KafkaTopics.AGENT_TASKS, message, key=task.task_id)

    def send_agent_response(self, response: AgentResponse):
        """Send agent response message"""
        message = response.model_dump(mode='json')
        self.send_message(KafkaTopics.AGENT_RESPONSES, message, key=response.task_id)

    def send_story_event(self, event: StoryEvent):
        """Send story event message"""
        message = event.model_dump(mode='json')
        topic_map = {
            "created": KafkaTopics.STORY_CREATED,
            "updated": KafkaTopics.STORY_UPDATED,
            "status_changed": KafkaTopics.STORY_STATUS_CHANGED,
            "assigned": KafkaTopics.STORY_ASSIGNED,
        }
        topic = topic_map.get(event.event_type, KafkaTopics.STORY_UPDATED)
        self.send_message(topic, message, key=str(event.story_id))

    def send_agent_status(self, status: AgentStatusMessage):
        """Send agent status message"""
        message = status.model_dump(mode='json')
        self.send_message(KafkaTopics.AGENT_STATUS, message, key=status.agent_id)

    def flush(self, timeout: float = 10.0):
        """Wait for all messages to be delivered"""
        if self.producer:
            self.producer.flush(timeout)

    def close(self):
        """Close the producer"""
        if self.producer:
            self.flush()
            logger.info("Kafka producer closed")


# Global producer instance
kafka_producer = KafkaProducerService()
