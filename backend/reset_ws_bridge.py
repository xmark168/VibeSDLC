"""
Simple script to reset WebSocket Bridge consumer lag

Run this when you experience lag in real-time WebSocket updates.
"""

import asyncio
from confluent_kafka import Consumer, TopicPartition, KafkaException


async def reset_websocket_bridge():
    """Reset websocket_bridge_group to latest offset"""
    
    config = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'websocket_bridge_group',
        'auto.offset.reset': 'latest',
        'enable.auto.commit': False,
    }
    
    consumer = Consumer(config)
    
    topics = [
        'agent_events',
        'domain_events',
        'story_events',
        'flow_status',
        'agent_tasks',
    ]
    
    print("🔄 Resetting WebSocket Bridge consumer to latest offset...")
    print(f"   Consumer Group: websocket_bridge_group")
    print(f"   Topics: {', '.join(topics)}")
    print()
    
    try:
        # Subscribe to topics
        consumer.subscribe(topics)
        
        # Poll once to get partition assignment
        consumer.poll(timeout=5.0)
        
        # Get assigned partitions
        partitions = consumer.assignment()
        
        if not partitions:
            print("⚠️  No partitions assigned. Topics may be empty or consumer group doesn't exist yet.")
            print("   Try restarting the backend first, then run this script.")
            consumer.close()
            return
        
        print(f"📊 Found {len(partitions)} partition(s)")
        print()
        
        # Seek each partition to end (latest)
        for partition in partitions:
            # Get high watermark (latest offset)
            low, high = consumer.get_watermark_offsets(partition, timeout=10.0)
            
            # Seek to high watermark
            partition.offset = high
            consumer.seek(partition)
            
            print(f"   ✓ {partition.topic} [partition {partition.partition}]")
            print(f"     Offset: {low} → {high} (skipped {high - low} messages)")
        
        print()
        print("💾 Committing new offsets...")
        
        # Commit the new offsets
        consumer.commit()
        
        print()
        print("✅ WebSocket Bridge reset complete!")
        print("   The consumer will now only process new messages.")
        print("   Restart the backend to apply changes.")
        
    except KafkaException as e:
        print(f"❌ Kafka error: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Make sure Kafka is running (docker-compose up -d)")
        print("   2. Check if backend is stopped (consumer group must be inactive)")
        print("   3. Verify Kafka connection: localhost:9092")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        
    finally:
        consumer.close()


def main():
    """Entry point"""
    print()
    print("=" * 70)
    print("  WebSocket Bridge Consumer Reset Tool")
    print("=" * 70)
    print()
    
    try:
        asyncio.run(reset_websocket_bridge())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    
    print()


if __name__ == "__main__":
    main()
