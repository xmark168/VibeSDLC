"""
Reset Kafka consumer group offset to latest

This script resets the websocket_bridge_group consumer offset to latest,
so it only consumes new messages instead of old backlog.
"""

from confluent_kafka.admin import AdminClient, ConsumerGroupTopicPartitions, TopicPartition
import sys


def reset_consumer_group():
    """Reset consumer group offset to latest"""
    
    # Kafka config
    admin_config = {
        'bootstrap.servers': 'localhost:9092',
    }
    
    admin_client = AdminClient(admin_config)
    
    # Consumer group to reset
    group_id = "websocket_bridge_group"
    
    # Topics to reset
    topics = [
        "agent_events",
        "domain_events",
        "story_events",
        "flow_status",
        "agent_tasks",
    ]
    
    print(f"Resetting consumer group '{group_id}' offset to latest...")
    print(f"Topics: {topics}")
    
    # Get topic metadata to find partitions
    metadata = admin_client.list_topics(timeout=10)
    
    # Build list of TopicPartitions with offset -1 (latest)
    topic_partitions = []
    for topic in topics:
        if topic in metadata.topics:
            partitions = metadata.topics[topic].partitions
            for partition_id in partitions.keys():
                # offset = -1 means "latest"
                tp = TopicPartition(topic, partition_id, offset=-1)
                topic_partitions.append(tp)
                print(f"  {topic} partition {partition_id} -> LATEST")
        else:
            print(f"  WARNING: Topic {topic} not found")
    
    if not topic_partitions:
        print("No partitions found. Exiting.")
        return
    
    # Alter consumer group offsets
    try:
        # Note: ConsumerGroupTopicPartitions requires group_id and topic_partitions
        from confluent_kafka.admin import ConsumerGroupTopicPartitions
        
        cg_tp = ConsumerGroupTopicPartitions(group_id, topic_partitions)
        
        # Alter offsets (requires kafka >= 2.4.0)
        fs = admin_client.alter_consumer_group_offsets([cg_tp])
        
        # Wait for result
        for group, future in fs.items():
            try:
                result = future.result()
                print(f"\n✅ Successfully reset consumer group '{group}'")
            except Exception as e:
                print(f"\n❌ Failed to reset consumer group '{group}': {e}")
                print("\nAlternative: Delete consumer group manually:")
                print(f"  kafka-consumer-groups --bootstrap-server localhost:9092 --group {group_id} --delete")
                return
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nYou can also reset manually using kafka-consumer-groups CLI:")
        print(f"  kafka-consumer-groups --bootstrap-server localhost:9092 --group {group_id} --reset-offsets --to-latest --all-topics --execute")
        return
    
    print("\n✅ Consumer group offset reset complete!")
    print("Restart the backend to apply changes.")


if __name__ == "__main__":
    reset_consumer_group()
