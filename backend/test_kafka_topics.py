"""Test script to manually create Kafka topics"""

import logging
from app.kafka.producer import kafka_producer

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

print("=" * 60)
print("Testing Kafka Producer Initialization and Topic Creation")
print("=" * 60)

try:
    print("\n1. Initializing Kafka producer...")
    kafka_producer.initialize()
    print("   ✓ Producer initialized")

    print("\n2. Checking if topics were created...")
    metadata = kafka_producer.admin_client.list_topics(timeout=10)
    existing_topics = list(metadata.topics.keys())

    print(f"\n   Existing topics: {existing_topics}")

    required_topics = ['agent_tasks', 'agent_responses']
    for topic in required_topics:
        if topic in existing_topics:
            print(f"   ✓ {topic} exists")
        else:
            print(f"   ✗ {topic} MISSING")

    print("\n3. Producer status:")
    print(f"   - Initialized: {kafka_producer._initialized}")
    print(f"   - Producer: {kafka_producer.producer is not None}")
    print(f"   - Admin Client: {kafka_producer.admin_client is not None}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
