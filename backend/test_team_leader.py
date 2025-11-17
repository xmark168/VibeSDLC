"""
Team Leader Agent Test Suite

Comprehensive test script for Team Leader Agent that:
- Tests intent analysis (delegation, insights, hybrid)
- Tests routing to specialist agents (BA, Dev, Tester)
- Tests parallel delegation capabilities
- Tests insights/analytics requests
- Validates end-to-end message flow
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any
from enum import Enum

from app.crews.events.kafka_producer import get_kafka_producer, shutdown_kafka_producer
from app.crews.events.event_schemas import KafkaTopics, UserMessageEvent


class TestCategory(Enum):
    """Test message categories"""
    DELEGATION_BA = "delegation_ba"
    DELEGATION_DEV = "delegation_dev"
    DELEGATION_TESTER = "delegation_tester"
    INSIGHTS = "insights"
    PARALLEL = "parallel"
    HYBRID = "hybrid"


class TestMessage:
    """Test message with expected behavior"""
    def __init__(
        self,
        content: str,
        category: TestCategory,
        expected_agents: list[str],
        description: str = ""
    ):
        self.content = content
        self.category = category
        self.expected_agents = expected_agents
        self.description = description


# Test message catalog
TEST_MESSAGES = {
    # BA Agent Tests
    "ba_user_story": TestMessage(
        content="Create a user story for user login with social media authentication",
        category=TestCategory.DELEGATION_BA,
        expected_agents=["ba"],
        description="User story creation"
    ),
    "ba_requirements": TestMessage(
        content="Define acceptance criteria for the shopping cart checkout flow",
        category=TestCategory.DELEGATION_BA,
        expected_agents=["ba"],
        description="Requirements analysis"
    ),
    "ba_specification": TestMessage(
        content="Write technical specifications for the payment gateway integration",
        category=TestCategory.DELEGATION_BA,
        expected_agents=["ba"],
        description="Technical specs"
    ),

    # Developer Agent Tests
    "dev_implementation": TestMessage(
        content="Implement the user registration API with email verification",
        category=TestCategory.DELEGATION_DEV,
        expected_agents=["dev"],
        description="Feature implementation"
    ),
    "dev_bugfix": TestMessage(
        content="Fix the authentication token expiration bug in the login module",
        category=TestCategory.DELEGATION_DEV,
        expected_agents=["dev"],
        description="Bug fix"
    ),
    "dev_refactor": TestMessage(
        content="Refactor the database connection pooling code for better performance",
        category=TestCategory.DELEGATION_DEV,
        expected_agents=["dev"],
        description="Code refactoring"
    ),

    # Tester Agent Tests
    "tester_test_cases": TestMessage(
        content="Design test cases for the checkout flow including edge cases",
        category=TestCategory.DELEGATION_TESTER,
        expected_agents=["tester"],
        description="Test case design"
    ),
    "tester_qa": TestMessage(
        content="Run comprehensive QA tests on the payment gateway integration",
        category=TestCategory.DELEGATION_TESTER,
        expected_agents=["tester"],
        description="QA testing"
    ),
    "tester_automation": TestMessage(
        content="Create automated test suite for the user authentication flow",
        category=TestCategory.DELEGATION_TESTER,
        expected_agents=["tester"],
        description="Test automation"
    ),

    # Insights Tests
    "insights_metrics": TestMessage(
        content="Show me the current project metrics and team performance analytics",
        category=TestCategory.INSIGHTS,
        expected_agents=[],
        description="Project metrics request"
    ),
    "insights_status": TestMessage(
        content="What's the status of all user stories? Any blockers?",
        category=TestCategory.INSIGHTS,
        expected_agents=[],
        description="Status and blockers"
    ),
    "insights_velocity": TestMessage(
        content="Analyze our team velocity and cycle time trends",
        category=TestCategory.INSIGHTS,
        expected_agents=[],
        description="Velocity analysis"
    ),

    # Parallel Delegation Tests
    "parallel_full_feature": TestMessage(
        content="Implement a new notification system - create user stories, write the code, and test it thoroughly",
        category=TestCategory.PARALLEL,
        expected_agents=["ba", "dev", "tester"],
        description="Full feature development"
    ),
    "parallel_bug_workflow": TestMessage(
        content="There's a critical payment bug - analyze requirements, fix the code, and run comprehensive tests",
        category=TestCategory.PARALLEL,
        expected_agents=["ba", "dev", "tester"],
        description="Critical bug workflow"
    ),
    "parallel_refactor": TestMessage(
        content="Refactor the user profile module - update specs, implement changes, and verify with tests",
        category=TestCategory.PARALLEL,
        expected_agents=["ba", "dev", "tester"],
        description="Refactoring workflow"
    ),

    # Hybrid Tests (Insights + Delegation)
    "hybrid_status_fix": TestMessage(
        content="Show me blocked stories and help fix the authentication blocker",
        category=TestCategory.HYBRID,
        expected_agents=["dev"],
        description="Insights + bug fix"
    ),
    "hybrid_metrics_plan": TestMessage(
        content="Analyze sprint progress and create user stories for remaining features",
        category=TestCategory.HYBRID,
        expected_agents=["ba"],
        description="Insights + planning"
    ),
}


async def send_single_message(
    content: str,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    metadata: Dict[str, Any] = None
) -> bool:
    """Send a single test message to USER_MESSAGES topic"""
    producer = await get_kafka_producer()

    message_id = uuid.uuid4()
    user_message = UserMessageEvent(
        message_id=message_id,
        project_id=project_id,
        user_id=user_id,
        content=content,
        metadata=metadata or {"source": "test_script", "test_run": True},
        timestamp=datetime.utcnow()
    )

    success = await producer.publish_event(
        topic=KafkaTopics.USER_MESSAGES,
        event=user_message.model_dump(),
        key=str(project_id)
    )

    return success


async def test_single_message():
    """Test 1: Send a single custom message"""
    print("\n" + "=" * 80)
    print("🧪 TEST 1: Single Custom Message")
    print("=" * 80)

    try:
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()

        print("\nEnter your test message (or press Enter for default):")
        custom_content = input("> ").strip()

        if not custom_content:
            custom_content = "Create a user story for implementing dark mode feature"

        print(f"\n📝 Sending message:")
        print(f"   Project ID: {project_id}")
        print(f"   User ID:    {user_id}")
        print(f"   Content:    {custom_content}")
        print("-" * 80)

        success = await send_single_message(custom_content, project_id, user_id)

        if success:
            print("✅ Message published successfully!")
            print("\n📊 Expected flow:")
            print("   1. Team Leader consumes message from USER_MESSAGES")
            print("   2. Team Leader analyzes intent using CrewAI")
            print("   3. Team Leader routes to appropriate agent(s) or provides insights")
            print("   4. Check application logs for detailed output")
        else:
            print("❌ Failed to publish message")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await shutdown_kafka_producer()
        print("\n" + "=" * 80 + "\n")


async def test_category(category: TestCategory, delay: float = 1.0):
    """Test specific category of messages"""
    category_name = category.value.replace("_", " ").title()
    print("\n" + "=" * 80)
    print(f"🧪 TEST: {category_name}")
    print("=" * 80)

    try:
        # Filter messages by category
        messages = [
            (key, msg) for key, msg in TEST_MESSAGES.items()
            if msg.category == category
        ]

        if not messages:
            print(f"⚠️  No test messages found for category: {category_name}")
            return

        project_id = uuid.uuid4()
        user_id = uuid.uuid4()

        print(f"\n📋 Running {len(messages)} test(s) for: {category_name}")
        print(f"   Project ID: {project_id}")
        print("-" * 80)

        for idx, (key, msg) in enumerate(messages, 1):
            print(f"\n📨 Test {idx}/{len(messages)}: {msg.description}")
            print(f"   Message:  {msg.content}")
            print(f"   Expected: {', '.join(msg.expected_agents) if msg.expected_agents else 'Insights response'}")

            metadata = {
                "source": "test_script",
                "test_run": True,
                "test_key": key,
                "category": category.value,
                "expected_agents": msg.expected_agents,
            }

            success = await send_single_message(msg.content, project_id, user_id, metadata)

            if success:
                print(f"   ✅ Published successfully")
            else:
                print(f"   ❌ Failed to publish")

            # Delay between messages
            if idx < len(messages):
                await asyncio.sleep(delay)

        print("\n" + "-" * 80)
        print(f"✅ All {len(messages)} test(s) sent for {category_name}")
        print("⏳ Check application logs for Team Leader analysis and routing")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await shutdown_kafka_producer()
        print("\n" + "=" * 80 + "\n")


async def test_all_categories():
    """Test all message categories sequentially"""
    print("\n" + "=" * 80)
    print("🧪 COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print("\nThis will test all categories:")
    print("  1. BA Agent delegation")
    print("  2. Developer Agent delegation")
    print("  3. Tester Agent delegation")
    print("  4. Insights requests")
    print("  5. Parallel delegation")
    print("  6. Hybrid requests")
    print("\n" + "=" * 80)

    categories = [
        TestCategory.DELEGATION_BA,
        TestCategory.DELEGATION_DEV,
        TestCategory.DELEGATION_TESTER,
        TestCategory.INSIGHTS,
        TestCategory.PARALLEL,
        TestCategory.HYBRID,
    ]

    for idx, category in enumerate(categories, 1):
        print(f"\n🔄 Running category {idx}/{len(categories)}...")
        await test_category(category, delay=1.5)

        # Delay between categories
        if idx < len(categories):
            print(f"\n⏸️  Waiting 3 seconds before next category...")
            await asyncio.sleep(3)

    print("\n" + "=" * 80)
    print("✅ COMPREHENSIVE TEST SUITE COMPLETED")
    print("=" * 80)
    print("\n📊 Summary:")
    print(f"   Total categories tested: {len(categories)}")
    print(f"   Total messages sent:     {len(TEST_MESSAGES)}")
    print("\n📋 Check application logs to verify:")
    print("   - CrewAI intent analysis for each message")
    print("   - Correct routing to expected agents")
    print("   - Parallel delegation when multiple agents needed")
    print("   - Insights responses for analytics requests")
    print("=" * 80 + "\n")


async def test_parallel_stress():
    """Stress test parallel delegation with rapid messages"""
    print("\n" + "=" * 80)
    print("🧪 PARALLEL DELEGATION STRESS TEST")
    print("=" * 80)

    try:
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Get parallel messages
        parallel_messages = [
            msg for msg in TEST_MESSAGES.values()
            if msg.category == TestCategory.PARALLEL
        ]

        print(f"\n📋 Sending {len(parallel_messages)} parallel delegation messages")
        print(f"   Project ID: {project_id}")
        print(f"   Delay:      0.5s (rapid fire)")
        print("-" * 80)

        for idx, msg in enumerate(parallel_messages, 1):
            print(f"\n⚡ Rapid Test {idx}/{len(parallel_messages)}")
            print(f"   {msg.content[:60]}...")

            metadata = {
                "source": "stress_test",
                "test_run": True,
                "expect_parallel": True,
                "expected_agents": msg.expected_agents,
            }

            success = await send_single_message(msg.content, project_id, user_id, metadata)

            if success:
                print(f"   ✅ Sent")
            else:
                print(f"   ❌ Failed")

            await asyncio.sleep(0.5)  # Rapid fire

        print("\n" + "-" * 80)
        print("✅ Stress test completed!")
        print("📊 Watch logs for parallel delegation handling")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await shutdown_kafka_producer()
        print("\n" + "=" * 80 + "\n")


async def main():
    """Main test menu"""
    while True:
        print("\n" + "=" * 80)
        print("🧪 TEAM LEADER AGENT TEST SUITE")
        print("=" * 80)
        print("\nTest Options:")
        print("  1. Single custom message")
        print("  2. BA Agent delegation tests")
        print("  3. Developer Agent delegation tests")
        print("  4. Tester Agent delegation tests")
        print("  5. Insights/Analytics tests")
        print("  6. Parallel delegation tests")
        print("  7. Hybrid (insights + delegation) tests")
        print("  8. All categories (comprehensive)")
        print("  9. Parallel delegation stress test")
        print("  0. Exit")
        print("\n" + "=" * 80)

        choice = input("\nSelect option (0-9): ").strip()

        if choice == "0":
            print("\n👋 Goodbye!\n")
            break
        elif choice == "1":
            await test_single_message()
        elif choice == "2":
            await test_category(TestCategory.DELEGATION_BA)
        elif choice == "3":
            await test_category(TestCategory.DELEGATION_DEV)
        elif choice == "4":
            await test_category(TestCategory.DELEGATION_TESTER)
        elif choice == "5":
            await test_category(TestCategory.INSIGHTS)
        elif choice == "6":
            await test_category(TestCategory.PARALLEL)
        elif choice == "7":
            await test_category(TestCategory.HYBRID)
        elif choice == "8":
            await test_all_categories()
        elif choice == "9":
            await test_parallel_stress()
        else:
            print("\n❌ Invalid choice! Please select 0-9\n")
            continue

        # Ask if user wants to continue
        print("\n" + "-" * 80)
        continue_choice = input("Run another test? (y/n): ").strip().lower()
        if continue_choice != "y":
            print("\n👋 Goodbye!\n")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user\n")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
