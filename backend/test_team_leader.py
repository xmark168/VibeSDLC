"""
Test script for Team Leader Agent

Publishes test messages to USER_MESSAGES topic to verify:
1. Team Leader consumes messages
2. Team Leader analyzes intent using CrewAI (delegation, insights, or hybrid)
3. Team Leader provides project insights when requested
4. Team Leader delegates to appropriate specialist agents (BA, Dev, Tester)
5. Specialist agents receive and print task details (debug mode)
6. Parallel delegation to multiple agents works correctly
7. Hybrid requests (insights + delegation) are handled correctly
"""

import asyncio
import uuid
from datetime import datetime

from app.crews.events.kafka_producer import get_kafka_producer
from app.crews.events.event_schemas import (
    KafkaTopics,
    UserMessageEvent,
)


async def send_test_message():
    """Send a test message to USER_MESSAGES topic"""
    try:
        print("\n" + "=" * 80)
        print("🚀 Team Leader Agent Test Script")
        print("=" * 80)

        # Get Kafka producer
        producer = await get_kafka_producer()
        print("✓ Kafka producer initialized")

        # Create test message
        message_id = uuid.uuid4()
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Test message content
        test_content = "Hello Team Leader! Please delegate this task to the test agent for verification."

        user_message = UserMessageEvent(
            message_id=message_id,
            project_id=project_id,
            user_id=user_id,
            content=test_content,
            metadata={
                "source": "test_script",
                "test_run": True
            },
            timestamp=datetime.utcnow()
        )

        print(f"\n📝 Sending test message:")
        print(f"   Message ID:  {message_id}")
        print(f"   Project ID:  {project_id}")
        print(f"   User ID:     {user_id}")
        print(f"   Content:     {test_content}")
        print("-" * 80)

        # Publish to USER_MESSAGES topic
        success = await producer.publish_event(
            topic=KafkaTopics.USER_MESSAGES,
            event=user_message.model_dump(),
            key=str(project_id)
        )

        if success:
            print("✅ Message published successfully!")
            print("\n📊 Expected flow:")
            print("   1. Team Leader Agent consumes from USER_MESSAGES")
            print("   2. Team Leader analyzes intent using CrewAI")
            print("   3. Based on analysis, Team Leader:")
            print("      - Provides insights (project metrics, analytics, status)")
            print("      - Delegates to BA Agent (user stories, requirements, criteria)")
            print("      - Delegates to Dev Agent (implementation, bug fixes, code)")
            print("      - Delegates to Tester Agent (test cases, QA, testing)")
            print("      - Or combination (hybrid: insights + delegation)")
            print("   4. Selected agent(s) receive tasks and print details")
            print("\n⏳ Check the application logs/console to see the agent output...")
            print("=" * 80 + "\n")
        else:
            print("❌ Failed to publish message")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def send_multiple_test_messages():
    """Send multiple test messages with different intents"""
    try:
        print("\n" + "=" * 80)
        print("🚀 Team Leader Agent - Multiple Test Messages")
        print("=" * 80)

        producer = await get_kafka_producer()
        print("✓ Kafka producer initialized\n")

        # Different test messages to test agent routing
        test_messages = [
            "Create a user story for the login feature",  # Should go to BA
            "Fix the bug in the authentication module",   # Should go to Dev
            "Run tests for the payment gateway",          # Should go to Tester
            "Test agent, please verify the delegation system",  # Should go to Test Agent
            "Show me the project metrics and analytics",  # Might go to Test/BA
            "Write code to implement the user registration API",  # Should go to Dev
            "Design test cases for the checkout flow",    # Should go to Tester
            "Define acceptance criteria for the shopping cart feature",  # Should go to BA
        ]

        project_id = uuid.uuid4()
        user_id = uuid.uuid4()

        for idx, content in enumerate(test_messages, 1):
            message_id = uuid.uuid4()

            user_message = UserMessageEvent(
                message_id=message_id,
                project_id=project_id,
                user_id=user_id,
                content=content,
                metadata={
                    "source": "test_script",
                    "test_run": True,
                    "test_number": idx
                },
                timestamp=datetime.utcnow()
            )

            print(f"📨 Message {idx}: {content}")

            success = await producer.publish_event(
                topic=KafkaTopics.USER_MESSAGES,
                event=user_message.model_dump(),
                key=str(project_id)
            )

            if success:
                print(f"   ✅ Published successfully")
            else:
                print(f"   ❌ Failed to publish")

            # Small delay between messages
            await asyncio.sleep(1)

        print("\n" + "=" * 80)
        print("✅ All test messages sent!")
        print("⏳ Check the application logs to see Team Leader analysis and agent output")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def send_parallel_delegation_tests():
    """Send messages specifically designed to test parallel delegation"""
    try:
        print("\n" + "=" * 80)
        print("🚀 Team Leader Agent - Parallel Delegation Tests")
        print("=" * 80)

        producer = await get_kafka_producer()
        print("✓ Kafka producer initialized\n")

        # Messages that should trigger parallel delegation (multiple agents needed)
        parallel_test_messages = [
            "Implement a new user authentication feature - create user stories, write the code, and test it thoroughly",
            "We have a critical bug in the payment system - need requirements analysis, code fix, and comprehensive testing",
            "Build a notification system from scratch with full BA analysis, development, and QA coverage",
            "Refactor the entire user profile module - needs stories, implementation, and test coverage",
        ]

        project_id = uuid.uuid4()
        user_id = uuid.uuid4()

        print("📋 These messages are designed to trigger PARALLEL DELEGATION")
        print("   (Team Leader should delegate to BA + Dev + Tester simultaneously)\n")

        for idx, content in enumerate(parallel_test_messages, 1):
            message_id = uuid.uuid4()

            user_message = UserMessageEvent(
                message_id=message_id,
                project_id=project_id,
                user_id=user_id,
                content=content,
                metadata={
                    "source": "parallel_delegation_test",
                    "test_run": True,
                    "test_number": idx,
                    "expect_parallel": True
                },
                timestamp=datetime.utcnow()
            )

            print(f"📨 Parallel Test {idx}:")
            print(f"   {content}")

            success = await producer.publish_event(
                topic=KafkaTopics.USER_MESSAGES,
                event=user_message.model_dump(),
                key=str(project_id)
            )

            if success:
                print(f"   ✅ Published successfully")
                print(f"   ⏳ Watch for PARALLEL DELEGATION log in Team Leader")
            else:
                print(f"   ❌ Failed to publish")

            print()

            # Longer delay to see parallel delegation in action
            await asyncio.sleep(3)

        print("=" * 80)
        print("✅ All parallel delegation tests sent!")
        print("📊 Check logs to verify:")
        print("   - Team Leader logs show 'PARALLEL DELEGATION' message")
        print("   - Multiple agents (BA, Dev, Tester) receive tasks simultaneously")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test function"""
    print("\n🔧 Team Leader Agent Test Options:")
    print("1. Send single test message")
    print("2. Send multiple test messages with different intents")
    print("3. Send parallel delegation test messages")
    print("4. All tests (1 + 2 + 3)\n")

    choice = input("Select option (1/2/3/4): ").strip()

    if choice == "1":
        await send_test_message()
    elif choice == "2":
        await send_multiple_test_messages()
    elif choice == "3":
        await send_parallel_delegation_tests()
    elif choice == "4":
        await send_test_message()
        await asyncio.sleep(3)
        await send_multiple_test_messages()
        await asyncio.sleep(3)
        await send_parallel_delegation_tests()
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    asyncio.run(main())
