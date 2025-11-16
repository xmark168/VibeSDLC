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
            "title": "User Authentication System",
            "description": "Implement comprehensive user authentication system with registration, login, and security features",
            "task_type": None,
            "business_value": "Enable secure user access and account management for the application",
            "labels": ["backend", "frontend", "security"],
            "rank": 1,
            "status": "To Do",
            "story_point": 21,
            "estimate_value": 21,
        },
        {
            "id": "TASK-001",
            "type": "Task",
            "parent_id": "EPIC-001",
            "title": "Implement user registration functionality",
            "description": "Create user registration API endpoint with validation, password hashing, and email verification",
            "task_type": "Development",
            "labels": ["backend", "frontend"],
            "rank": 2,
            "status": "To Do",
            "story_point": 8,
            "estimate_value": 8,
            "acceptance_criteria": [
                "POST /api/auth/register endpoint accepts email, password, and confirm_password",
                "Password validation includes minimum 8 characters, uppercase, lowercase, number, special character",
                "Email validation ensures proper format and uniqueness",
                "Password is hashed using bcrypt before storing in database",
                "User data is stored in database with created_at timestamp",
                "Returns JWT token upon successful registration",
                "Returns appropriate error messages for validation failures",
                "Includes comprehensive unit tests for all scenarios",
                "API documentation is updated with endpoint details",
            ],
            "dependencies": [],
        },
        {
            "id": "TASK-002",
            "type": "Task",
            "parent_id": "EPIC-001",
            "title": "Implement user login functionality",
            "description": "Create user login API endpoint with authentication, session management, and security features",
            "task_type": "Development",
            "labels": ["backend"],
            "rank": 3,
            "status": "To Do",
            "story_point": 5,
            "estimate_value": 5,
            "acceptance_criteria": [
                "POST /api/auth/login endpoint accepts email and password",
                "Validates user credentials against database",
                "Compares hashed password using bcrypt",
                "Returns JWT token with user information upon successful login",
                "Implements rate limiting to prevent brute force attacks",
                "Logs failed login attempts for security monitoring",
                "Returns appropriate error messages for invalid credentials",
                "Token includes user ID, email, and expiration time",
                "Includes comprehensive unit tests for authentication scenarios",
                "API documentation is updated with endpoint details",
            ],
            "dependencies": ["TASK-001"],
        },
        {
            "id": "TASK-003",
            "type": "Task",
            "parent_id": "EPIC-001",
            "title": "Implement password reset functionality",
            "description": "Create password reset flow with email verification, secure token generation, and password update capabilities",
            "task_type": "Development",
            "labels": ["backend", "frontend"],
            "rank": 4,
            "status": "To Do",
            "story_point": 5,
            "estimate_value": 5,
            "acceptance_criteria": [
                "POST /api/auth/forgot-password endpoint accepts email address",
                "Generates secure random reset token with 1-hour expiration",
                "Stores reset token hash in database with user association",
                "Sends password reset email with secure reset link",
                "POST /api/auth/reset-password endpoint validates reset token",
                "Verifies token has not expired before allowing password reset",
                "New password meets same validation requirements as registration",
                "Invalidates reset token after successful password change",
                "Includes comprehensive unit tests for all reset scenarios",
                "API documentation is updated with password reset flow details",
            ],
            "dependencies": ["TASK-001"],
        },
        {
            "id": "TASK-004",
            "type": "Task",
            "parent_id": "EPIC-001",
            "title": "Implement JWT token refresh mechanism",
            "description": "Create token refresh endpoint to allow users to obtain new access tokens without re-authentication",
            "task_type": "Development",
            "labels": ["frontend"],
            "rank": 5,
            "status": "To Do",
            "story_point": 3,
            "estimate_value": 3,
            "acceptance_criteria": [
                "POST /api/auth/refresh endpoint accepts refresh token",
                "Validates refresh token signature and expiration",
                "Verifies refresh token exists in database and is not revoked",
                "Issues new access token with updated expiration time",
                "Issues new refresh token and invalidates old one (token rotation)",
                "Access token expires in 15 minutes, refresh token in 7 days",
                "Returns appropriate error for invalid or expired refresh tokens",
                "Implements token blacklist for revoked refresh tokens",
                "Includes comprehensive unit tests for token refresh scenarios",
                "API documentation is updated with token refresh flow details",
            ],
            "dependencies": ["TASK-002"],
        },
        {
            "id": "US-001",
            "type": "User Story",
            "parent_id": "EPIC-001",
            "title": "As a user, I want to test the system",
            "description": "User story for testing purposes",
            "task_type": None,  # Should be skipped
            "labels": ["testing"],
            "rank": 6,
            "status": "To Do",
        },
    ]

    # Test sprint data
    sprint_data = [
        {
            "sprint_id": "test-sprint-1",
            "sprint_number": 1,
            "sprint_goal": "Implement core user authentication features (registration, login, password reset, and token refresh)",
            "start_date": "2025-01-01",
            "end_date": "2025-01-15",
            "assigned_items": [
                "EPIC-001",  # Should be skipped (no task_type)
                "TASK-001",  # Should be processed (Development)
                "TASK-002",  # Should be processed (Development)
                "TASK-003",  # Should be processed (Development)
                "TASK-004",  # Should be processed (Development)
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
                github_repo_url="",
            )

            print(f"✅ Agent execution result: {result['success']}")

            if result["success"]:
                summary = result["execution_summary"]
                print(f"📊 Total assigned items: {summary['total_assigned_items']}")
                print(f"📊 Eligible tasks: {summary['eligible_tasks_count']}")
                print(f"📊 Processed tasks: {summary['processed_tasks_count']}")
                print(f"📊 Success rate: {summary['success_rate']:.1f}%")

                # Verify expected results
                assert summary["total_assigned_items"] == 7, (
                    "Should have 7 assigned items"
                )
                assert summary["eligible_tasks_count"] == 4, (
                    "Should have 4 eligible tasks (TASK-001, TASK-002, TASK-003, TASK-004)"
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
