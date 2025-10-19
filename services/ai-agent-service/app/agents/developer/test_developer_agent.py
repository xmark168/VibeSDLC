"""
Test Developer Agent Implementation

Test script to verify Developer Agent orchestrator functionality.
"""

import json
import tempfile
from pathlib import Path

from app.agents.developer.agent import DeveloperAgent


def create_test_data():
    """Create test backlog and sprint data."""

    # Test backlog data
    backlog_data = [
        {
            "id": "EPIC-001",
            "type": "Epic",
            "parent_id": None,
            "title": "Test Epic for Development",
            "description": "Test epic to validate Developer Agent functionality",
            "task_type": None,
            "business_value": "Validate agent orchestration",
        },
        {
            "id": "TASK-001",
            "type": "Task",
            "parent_id": "EPIC-001",
            "title": "Implement test feature",
            "description": "Create a simple test feature to validate implementation workflow",
            "task_type": "Development",
            "acceptance_criteria": [
                "Feature is implemented correctly",
                "Code follows best practices",
                "Tests are included",
            ],
        },
        {
            "id": "TASK-002",
            "type": "Task",
            "parent_id": "EPIC-001",
            "title": "Setup test infrastructure",
            "description": "Setup basic infrastructure for testing",
            "task_type": "Infrastructure",
        },
        {
            "id": "US-001",
            "type": "User Story",
            "parent_id": "EPIC-001",
            "title": "As a user, I want to test the system",
            "description": "User story for testing purposes",
            "task_type": None,  # Should be skipped
        },
    ]

    # Test sprint data
    sprint_data = [
        {
            "sprint_id": "test-sprint-1",
            "sprint_number": 1,
            "sprint_goal": "Test Developer Agent functionality",
            "start_date": "2025-01-01",
            "end_date": "2025-01-15",
            "assigned_items": [
                "EPIC-001",  # Should be skipped (no task_type)
                "TASK-001",  # Should be processed (Development)
                "TASK-002",  # Should be processed (Infrastructure)
                "US-001",  # Should be skipped (no task_type)
                "MISSING-TASK",  # Should be skipped (not found)
            ],
            "status": "Planned",
        }
    ]

    return backlog_data, sprint_data


def test_developer_agent_basic():
    """Test basic Developer Agent functionality."""
    print("🧪 Testing Developer Agent basic functionality...")

    # Create test data
    backlog_data, sprint_data = create_test_data()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Write test files
        backlog_file = temp_path / "backlog.json"
        sprint_file = temp_path / "sprint.json"

        with open(backlog_file, "w") as f:
            json.dump(backlog_data, f, indent=2)

        with open(sprint_file, "w") as f:
            json.dump(sprint_data, f, indent=2)

        print(f"📁 Test backlog: {backlog_file}")
        print(f"📁 Test sprint: {sprint_file}")

        # Test with DeveloperAgent class
        print("\n🧪 Testing DeveloperAgent class...")

        try:
            agent = DeveloperAgent(
                model="gpt-4o-mini",  # Use cheaper model for testing
                session_id="test_session",
                user_id="test_user",
                enable_langfuse=False,  # Disable for testing
            )

            result = agent.run(
                sprint_id="test-sprint-1",
                backlog_path=str(backlog_file),
                sprint_path=str(sprint_file),
                working_directory=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
                continue_on_error=True,
            )

            print(f"✅ Agent execution result: {result['success']}")

            if result["success"]:
                summary = result["execution_summary"]
                print(f"📊 Total assigned items: {summary['total_assigned_items']}")
                print(f"📊 Eligible tasks: {summary['eligible_tasks_count']}")
                print(f"📊 Processed tasks: {summary['processed_tasks_count']}")
                print(f"📊 Success rate: {summary['success_rate']:.1f}%")

                # Verify expected results
                assert summary["total_assigned_items"] == 5, (
                    "Should have 5 assigned items"
                )
                assert summary["eligible_tasks_count"] == 2, (
                    "Should have 2 eligible tasks (TASK-001, TASK-002)"
                )

                print("✅ Basic functionality test passed!")
            else:
                print(
                    f"❌ Agent execution failed: {result.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            return False

    return True


def main():
    """Run all tests."""
    print("🚀 Testing Developer Agent Implementation...\n")

    tests = [
        ("Basic Functionality", test_developer_agent_basic),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"🧪 {test_name}")
        print(f"{'=' * 60}")

        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")

    print(f"\n{'=' * 60}")
    print("🎯 TEST SUMMARY")
    print(f"{'=' * 60}")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed / total * 100:.1f}%")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
