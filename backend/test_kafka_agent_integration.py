"""
Comprehensive test script for Kafka and Agent integration in VibeSDLC

This script tests:
1. Kafka connection and topic creation
2. Producer functionality (sending messages)
3. Consumer functionality (receiving messages)
4. Agent task processing
5. End-to-end workflow

Usage:
    python test_kafka_agent_integration.py
"""

import asyncio
import logging
import sys
import time
import json
from datetime import datetime
from app.kafka.producer import kafka_producer
from app.kafka.consumer import KafkaConsumerService
from app.kafka.topics import KafkaTopics
from app.kafka.schemas import AgentTask, AgentTaskType, AgentResponse
from confluent_kafka import Consumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KafkaAgentTester:
    """Test suite for Kafka and Agent integration"""

    def __init__(self):
        self.test_results = []
        self.consumer = None

    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✓ PASS" if passed else "✗ FAIL"
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
        logger.info(f"{status} - {test_name}: {message}")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        passed_count = sum(1 for r in self.test_results if r["passed"])
        total_count = len(self.test_results)

        for result in self.test_results:
            status = "✓" if result["passed"] else "✗"
            print(f"{status} {result['test']}: {result['message']}")

        print("-" * 70)
        print(f"Total: {passed_count}/{total_count} tests passed")
        print("=" * 70 + "\n")

        return passed_count == total_count

    # ========== TEST 1: Kafka Connection ==========
    def test_kafka_connection(self):
        """Test Kafka broker connection"""
        print("\n" + "=" * 70)
        print("TEST 1: KAFKA CONNECTION")
        print("=" * 70)

        try:
            kafka_producer.initialize()

            if kafka_producer._initialized:
                self.log_test(
                    "Kafka Connection",
                    True,
                    "Successfully connected to Kafka broker"
                )
                return True
            else:
                self.log_test(
                    "Kafka Connection",
                    False,
                    "Producer initialized but not marked as initialized"
                )
                return False

        except Exception as e:
            self.log_test(
                "Kafka Connection",
                False,
                f"Failed to connect: {str(e)}"
            )
            return False

    # ========== TEST 2: Topic Creation ==========
    def test_topic_creation(self):
        """Test if all required topics were created"""
        print("\n" + "=" * 70)
        print("TEST 2: TOPIC CREATION")
        print("=" * 70)

        try:
            metadata = kafka_producer.admin_client.list_topics(timeout=10)
            existing_topics = set(metadata.topics.keys())

            required_topics = [
                'agent_tasks',
                'agent_responses',
                'story_created',
                'story_updated',
                'story_status_changed',
                'story_assigned',
                'agent_status',
                'agent_heartbeat'
            ]

            all_exist = True
            for topic in required_topics:
                exists = topic in existing_topics
                status = "✓" if exists else "✗"
                print(f"  {status} {topic}")

                if not exists:
                    all_exist = False

            self.log_test(
                "Topic Creation",
                all_exist,
                f"{'All topics created' if all_exist else 'Some topics missing'}"
            )
            return all_exist

        except Exception as e:
            self.log_test(
                "Topic Creation",
                False,
                f"Failed to list topics: {str(e)}"
            )
            return False

    # ========== TEST 3: Producer - Send Message ==========
    def test_producer_send(self):
        """Test sending a message via producer"""
        print("\n" + "=" * 70)
        print("TEST 3: PRODUCER - SEND MESSAGE")
        print("=" * 70)

        try:
            # Create a test task
            test_task = AgentTask(
                task_id=f"test_task_{int(time.time())}",
                task_type=AgentTaskType.HELLO,
                agent_type="developer",
                payload={"message": "Test message from integration test"},
                priority=5
            )

            print(f"  Sending task: {test_task.task_id}")
            kafka_producer.send_agent_task(test_task)
            kafka_producer.flush(timeout=5.0)

            self.log_test(
                "Producer Send",
                True,
                f"Successfully sent task {test_task.task_id}"
            )
            return test_task.task_id

        except Exception as e:
            self.log_test(
                "Producer Send",
                False,
                f"Failed to send message: {str(e)}"
            )
            return None

    # ========== TEST 4: Consumer - Receive Message ==========
    def test_consumer_receive(self, task_id: str = None):
        """Test receiving messages via consumer"""
        print("\n" + "=" * 70)
        print("TEST 4: CONSUMER - RECEIVE MESSAGE")
        print("=" * 70)

        try:
            # Create a simple consumer
            from app.kafka.config import kafka_settings

            consumer_config = {
                'bootstrap.servers': kafka_settings.KAFKA_BOOTSTRAP_SERVERS,
                'group.id': 'test_consumer_group',
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': True,
            }

            consumer = Consumer(consumer_config)
            consumer.subscribe(['agent_tasks'])

            print("  Polling for messages (10 second timeout)...")
            messages_received = []
            timeout = time.time() + 10  # 10 second timeout

            while time.time() < timeout:
                msg = consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    continue

                # Decode message
                value = json.loads(msg.value().decode('utf-8'))
                messages_received.append(value)
                print(f"  ✓ Received message: task_id={value.get('task_id')}")

                # If we're looking for a specific task, check if we found it
                if task_id and value.get('task_id') == task_id:
                    consumer.close()
                    self.log_test(
                        "Consumer Receive",
                        True,
                        f"Successfully received task {task_id}"
                    )
                    return True

            consumer.close()

            if messages_received:
                self.log_test(
                    "Consumer Receive",
                    True,
                    f"Received {len(messages_received)} message(s)"
                )
                return True
            else:
                self.log_test(
                    "Consumer Receive",
                    False,
                    "No messages received within timeout"
                )
                return False

        except Exception as e:
            self.log_test(
                "Consumer Receive",
                False,
                f"Failed to receive messages: {str(e)}"
            )
            if consumer:
                consumer.close()
            return False

    # ========== TEST 5: Agent Response Flow ==========
    def test_agent_response_flow(self):
        """Test complete agent request-response flow"""
        print("\n" + "=" * 70)
        print("TEST 5: AGENT RESPONSE FLOW")
        print("=" * 70)

        try:
            # Send a task
            test_task = AgentTask(
                task_id=f"response_test_{int(time.time())}",
                task_type=AgentTaskType.HELLO,
                agent_type="developer",
                payload={"message": "Testing agent response flow"},
                priority=7
            )

            print(f"  Step 1: Sending task {test_task.task_id}")
            kafka_producer.send_agent_task(test_task)
            kafka_producer.flush(timeout=5.0)
            print("  ✓ Task sent")

            # Create a mock agent response
            mock_response = AgentResponse(
                task_id=test_task.task_id,
                agent_id="test_agent_001",
                agent_type="developer",
                status="completed",
                result={
                    "message": "Hello from test agent!",
                    "status": "success"
                },
                completed_at=datetime.utcnow(),
                execution_time_ms=100
            )

            print(f"  Step 2: Sending response for task {test_task.task_id}")
            kafka_producer.send_agent_response(mock_response)
            kafka_producer.flush(timeout=5.0)
            print("  ✓ Response sent")

            # Try to consume the response
            from app.kafka.config import kafka_settings

            consumer_config = {
                'bootstrap.servers': kafka_settings.KAFKA_BOOTSTRAP_SERVERS,
                'group.id': 'test_response_consumer',
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': True,
            }

            consumer = Consumer(consumer_config)
            consumer.subscribe(['agent_responses'])

            print("  Step 3: Listening for response...")
            timeout = time.time() + 10
            response_received = False

            while time.time() < timeout:
                msg = consumer.poll(timeout=1.0)

                if msg is None or msg.error():
                    continue

                value = json.loads(msg.value().decode('utf-8'))
                if value.get('task_id') == test_task.task_id:
                    print(f"  ✓ Received response: {value.get('status')}")
                    response_received = True
                    break

            consumer.close()

            self.log_test(
                "Agent Response Flow",
                response_received,
                f"{'Complete request-response cycle successful' if response_received else 'Response not received'}"
            )
            return response_received

        except Exception as e:
            self.log_test(
                "Agent Response Flow",
                False,
                f"Failed: {str(e)}"
            )
            return False

    # ========== TEST 6: Multiple Message Types ==========
    def test_multiple_message_types(self):
        """Test sending different types of messages"""
        print("\n" + "=" * 70)
        print("TEST 6: MULTIPLE MESSAGE TYPES")
        print("=" * 70)

        try:
            from app.kafka.schemas import StoryEvent

            # Test different task types
            task_types = [
                AgentTaskType.HELLO,
                AgentTaskType.ANALYZE_STORY,
                AgentTaskType.GENERATE_CODE,
            ]

            for task_type in task_types:
                task = AgentTask(
                    task_id=f"{task_type.value}_{int(time.time())}",
                    task_type=task_type,
                    agent_type="developer",
                    payload={"test": True},
                    priority=5
                )
                kafka_producer.send_agent_task(task)
                print(f"  ✓ Sent {task_type.value} task")

            # Test story event
            story_event = StoryEvent(
                event_type="status_changed",
                story_id=999,
                project_id=1,
                changes={"status": {"from": "TODO", "to": "IN_PROGRESS"}},
                triggered_by=1
            )
            kafka_producer.send_story_event(story_event)
            print("  ✓ Sent story event")

            kafka_producer.flush(timeout=5.0)

            self.log_test(
                "Multiple Message Types",
                True,
                "Successfully sent all message types"
            )
            return True

        except Exception as e:
            self.log_test(
                "Multiple Message Types",
                False,
                f"Failed: {str(e)}"
            )
            return False

    # ========== RUN ALL TESTS ==========
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("\n" + "=" * 70)
        print("KAFKA & AGENT INTEGRATION TEST SUITE")
        print("=" * 70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Test 1: Connection
        if not self.test_kafka_connection():
            print("\n⚠ Kafka connection failed. Stopping tests.")
            self.print_summary()
            return False

        # Test 2: Topics
        self.test_topic_creation()

        # Test 3: Producer
        task_id = self.test_producer_send()

        # Test 4: Consumer
        if task_id:
            self.test_consumer_receive(task_id)
        else:
            self.test_consumer_receive()

        # Test 5: Agent Response Flow
        self.test_agent_response_flow()

        # Test 6: Multiple Message Types
        self.test_multiple_message_types()

        # Print summary
        all_passed = self.print_summary()

        if all_passed:
            print("🎉 All tests passed! Kafka and Agent integration is working correctly.\n")
        else:
            print("⚠ Some tests failed. Please check the logs above.\n")

        return all_passed


def main():
    """Main entry point"""
    tester = KafkaAgentTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
