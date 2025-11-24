"""
Utility to ensure all Kafka topics are created at startup.

This module provides a robust way to create all required Kafka topics
with appropriate configurations before the application starts consuming/producing.
"""
import logging
from typing import List, Dict, Any

from confluent_kafka.admin import AdminClient, NewTopic

from app.core.config import settings
from app.kafka.event_schemas import KafkaTopics


logger = logging.getLogger(__name__)


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


async def ensure_kafka_topics() -> bool:
    """
    Ensure all required Kafka topics exist.
    
    Creates topics if they don't exist. Safe to call multiple times.
    
    Returns:
        True if all topics exist or were created successfully, False on error
    """
    try:
        logger.info("🔍 Checking Kafka topics...")
        
        # Create admin client
        admin_config = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS
        }
        
        # Add authentication if configured
        if settings.KAFKA_SECURITY_PROTOCOL != "PLAINTEXT":
            admin_config.update({
                "security.protocol": settings.KAFKA_SECURITY_PROTOCOL,
                "sasl.mechanism": settings.KAFKA_SASL_MECHANISM,
                "sasl.username": settings.KAFKA_SASL_USERNAME,
                "sasl.password": settings.KAFKA_SASL_PASSWORD,
            })
        
        admin_client = AdminClient(admin_config)
        
        # Get existing topics
        metadata = admin_client.list_topics(timeout=10)
        existing_topics = set(metadata.topics.keys())
        
        logger.info(f"Found {len(existing_topics)} existing topics")
        
        # Determine which topics need to be created
        topics_to_create = []
        all_topics = list(KafkaTopics)
        
        for topic in all_topics:
            if topic.value not in existing_topics:
                # Determine partition count based on expected traffic
                num_partitions = (
                    TopicConfig.HIGH_TRAFFIC_PARTITIONS
                    if topic in TopicConfig.HIGH_TRAFFIC_TOPICS
                    else TopicConfig.DEFAULT_PARTITIONS
                )
                
                topics_to_create.append(
                    NewTopic(
                        topic=topic.value,
                        num_partitions=num_partitions,
                        replication_factor=TopicConfig.REPLICATION_FACTOR,
                        config={
                            "retention.ms": str(TopicConfig.DEFAULT_RETENTION_MS),
                            "cleanup.policy": "delete",
                            "compression.type": "lz4",  # Better performance
                        }
                    )
                )
                logger.info(
                    f"  ⏳ Will create topic: {topic.value} "
                    f"(partitions={num_partitions}, replication={TopicConfig.REPLICATION_FACTOR})"
                )
            else:
                logger.debug(f"  ✓ Topic exists: {topic.value}")
        
        # Create missing topics
        if topics_to_create:
            logger.info(f"📝 Creating {len(topics_to_create)} missing topics...")
            
            fs = admin_client.create_topics(topics_to_create, operation_timeout=30)
            
            # Wait for operations to complete
            created_count = 0
            failed_count = 0
            
            for topic_name, future in fs.items():
                try:
                    future.result()  # Wait for operation to finish
                    logger.info(f"  ✓ Created topic: {topic_name}")
                    created_count += 1
                except Exception as e:
                    # Topic might already exist (race condition with other instances)
                    if "already exists" in str(e).lower():
                        logger.info(f"  ✓ Topic already exists: {topic_name}")
                        created_count += 1
                    else:
                        logger.error(f"  ✗ Failed to create topic {topic_name}: {e}")
                        failed_count += 1
            
            if failed_count > 0:
                logger.warning(
                    f"⚠️  Topic creation completed with {failed_count} failures "
                    f"({created_count} successful)"
                )
                return False
            else:
                logger.info(f"✅ All {created_count} topics created successfully")
                return True
        
        else:
            logger.info("✅ All Kafka topics already exist")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error ensuring Kafka topics: {e}")
        import traceback
        traceback.print_exc()
        return False


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
