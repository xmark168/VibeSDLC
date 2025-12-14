"""
Utility to ensure all Kafka topics are created at startup.

This module provides a robust way to create all required Kafka topics
with appropriate configurations before the application starts consuming/producing.

Optimized for fast startup:
- Short timeouts (2s for check, 5s for creation)
- Background topic creation (non-blocking)
- Graceful fallback when Kafka unavailable
"""
import asyncio
import logging
from typing import List, Dict, Any, Set

from confluent_kafka.admin import AdminClient, NewTopic

from app.core.config import settings
from app.kafka.event_schemas import KafkaTopics


logger = logging.getLogger(__name__)

# Timeouts optimized for fast startup
LIST_TOPICS_TIMEOUT = 2.0  # seconds
CREATE_TOPICS_TIMEOUT = 5  # seconds
FUTURE_RESULT_TIMEOUT = 5  # seconds


class TopicConfig:
    """Configuration for Kafka topics."""
    
    # High-traffic topics that need more partitions for better load distribution
    HIGH_TRAFFIC_TOPICS = {
        KafkaTopics.AGENT_EVENTS,      # Unified agent events stream
        KafkaTopics.AGENT_TASKS,
        KafkaTopics.USER_MESSAGES,
    }
    
    # Default partition counts
    HIGH_TRAFFIC_PARTITIONS = 6
    DEFAULT_PARTITIONS = 3
    
    # Default replication factor (set to 1 for development, increase for production)
    REPLICATION_FACTOR = 1
    
    # Default retention (7 days in milliseconds)
    DEFAULT_RETENTION_MS = 7 * 24 * 60 * 60 * 1000


def _get_admin_config() -> dict:
    """Build Kafka admin client configuration."""
    admin_config = {
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS
    }
    
    if settings.KAFKA_SECURITY_PROTOCOL != "PLAINTEXT":
        admin_config.update({
            "security.protocol": settings.KAFKA_SECURITY_PROTOCOL,
            "sasl.mechanism": settings.KAFKA_SASL_MECHANISM,
            "sasl.username": settings.KAFKA_SASL_USERNAME,
            "sasl.password": settings.KAFKA_SASL_PASSWORD,
        })
    
    return admin_config


def _build_new_topic(topic_name: str) -> NewTopic:
    """Build NewTopic object with appropriate configuration."""
    topic_enum = next((t for t in KafkaTopics if t.value == topic_name), None)
    
    num_partitions = (
        TopicConfig.HIGH_TRAFFIC_PARTITIONS
        if topic_enum and topic_enum in TopicConfig.HIGH_TRAFFIC_TOPICS
        else TopicConfig.DEFAULT_PARTITIONS
    )
    
    return NewTopic(
        topic=topic_name,
        num_partitions=num_partitions,
        replication_factor=TopicConfig.REPLICATION_FACTOR,
        config={
            "retention.ms": str(TopicConfig.DEFAULT_RETENTION_MS),
            "cleanup.policy": "delete",
            "compression.type": "lz4",
        }
    )


async def _create_topics_background(admin_config: dict, missing_topics: Set[str]) -> None:
    """
    Create missing topics in background with retry.
    
    Non-blocking - runs as background task to not delay startup.
    """
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            admin_client = AdminClient(admin_config)
            topics_to_create = [_build_new_topic(t) for t in missing_topics]
            
            fs = admin_client.create_topics(topics_to_create, operation_timeout=CREATE_TOPICS_TIMEOUT)
            
            created = 0
            failed = 0
            
            for topic_name, future in fs.items():
                try:
                    future.result(timeout=FUTURE_RESULT_TIMEOUT)
                    logger.info(f"  ✓ Created topic: {topic_name}")
                    created += 1
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.debug(f"  ✓ Topic already exists: {topic_name}")
                        created += 1
                    else:
                        logger.warning(f"  ✗ Failed to create {topic_name}: {e}")
                        failed += 1
            
            if failed == 0:
                logger.info(f"Background topic creation complete ({created} topics)")
                return
            else:
                logger.warning(f"⚠️ {failed} topics failed, {created} created")
                
        except Exception as e:
            logger.warning(f"Background topic creation attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
    
    logger.error("Background topic creation failed after all retries")


async def ensure_kafka_topics() -> bool:
    """
    Ensure all required Kafka topics exist.
    
    Optimized for fast startup:
    - Quick check with short timeout (2s)
    - Background topic creation (non-blocking)
    - Graceful fallback when Kafka unavailable
    
    Returns:
        True always (doesn't block startup on failure)
    """
    try:
        logger.info("🔍 Checking Kafka topics...")
        
        admin_config = _get_admin_config()
        admin_client = AdminClient(admin_config)
        
        # Quick check with short timeout
        metadata = admin_client.list_topics(timeout=LIST_TOPICS_TIMEOUT)
        existing_topics = set(metadata.topics.keys())
        
        logger.info(f"Found {len(existing_topics)} existing topics")
        
        # Determine missing topics
        required_topics = {t.value for t in KafkaTopics}
        missing_topics = required_topics - existing_topics
        
        if not missing_topics:
            logger.info("All Kafka topics already exist")
            return True
        
        # Create missing topics in background (non-blocking)
        logger.info(f"⏳ Creating {len(missing_topics)} topics in background...")
        asyncio.create_task(_create_topics_background(admin_config, missing_topics))
        
        return True
            
    except Exception as e:
        # Graceful fallback - don't block startup
        logger.warning(f"⚠️ Kafka not ready: {e}")
        logger.warning("Topics will be created on demand by producer")
        return True


def list_all_required_topics() -> List[str]:
    """
    Get list of all required Kafka topics.
    
    Returns:
        List of topic names as strings
    """
    return [topic.value for topic in KafkaTopics]


def get_topic_info() -> Dict[str, Any]:
    """
    Get information about all required topics.
    
    Returns:
        Dictionary with topic configurations
    """
    info = {
        "topics": [],
        "total_count": len(KafkaTopics),
        "high_traffic_count": len(TopicConfig.HIGH_TRAFFIC_TOPICS),
    }
    
    for topic in KafkaTopics:
        is_high_traffic = topic in TopicConfig.HIGH_TRAFFIC_TOPICS
        
        info["topics"].append({
            "name": topic.value,
            "partitions": (
                TopicConfig.HIGH_TRAFFIC_PARTITIONS
                if is_high_traffic
                else TopicConfig.DEFAULT_PARTITIONS
            ),
            "replication_factor": TopicConfig.REPLICATION_FACTOR,
            "high_traffic": is_high_traffic,
        })
    
    return info
