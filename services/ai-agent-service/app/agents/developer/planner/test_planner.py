"""
Test Planner Agent

Simple test để verify planner agent hoạt động correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from app.agents.developer.planner.agent import PlannerAgent


def test_planner_basic():
    """Test basic planner functionality."""
    print("🧪 Testing Planner Agent - Basic Functionality")
    print("=" * 60)

    # Create planner agent
    planner = PlannerAgent(
        model="gpt-4o", session_id="test_session_001", user_id="test_user"
    )

    # Test task description
    task_description = """
    Implement user authentication system with email verification.

    Requirements:
    - Users can register with email and password
    - Email verification required before account activation
    - Login with email/password after verification
    - Password reset functionality

    Acceptance Criteria:
    - Registration endpoint accepts email, password, confirm_password
    - Verification email sent automatically after registration
    - Users cannot login until email is verified
    - Password reset sends secure reset link to email
    - All endpoints return appropriate error messages

    Technical Specs:
    - Use FastAPI for API endpoints
    - PostgreSQL database with SQLModel
    - JWT tokens for authentication
    - Email service integration (SMTP or SendGrid)
    """

    try:
        print(f"📝 Task: {task_description[:100]}...")
        print("\n🚀 Starting planner workflow...")

        # Run planner with optional codebase_path
        # If you want to use a specific codebase path, pass it here:
        # codebase_path = r"D:\path\to\your\codebase"
        result = planner.run(
            task_description=task_description,
            codebase_path=r"D:\\capstone project\\VibeSDLC\\services\ai-agent-service\app\agents\\demo",  # Empty = use default path
            thread_id="test_thread_001",
        )

        # Display results
        print("\n" + "=" * 60)
        print("📊 PLANNER RESULTS")
        print("=" * 60)

        if result["success"]:
            print("✅ Planning completed successfully!")
            print(f"📋 Task ID: {result['task_id']}")
            print(f"📊 Complexity: {result['complexity_score']}/10")
            print(f"⭐ Story Points: {result['story_points']} SP")
            print(f"✅ Ready for Implementation: {result['ready_for_implementation']}")
            print(f"📈 Validation Score: {result['validation_score']:.1%}")
            print(f"🔄 Iterations: {result['iterations']}")

            # Show final plan summary
            final_plan = result.get("final_plan", {})
            if final_plan:
                print(
                    f"\n📋 Implementation Steps: {len(final_plan.get('implementation', {}).get('steps', []))}"
                )
                print(
                    f"📁 Files to Create: {len(final_plan.get('file_changes', {}).get('files_to_create', []))}"
                )
                print(
                    f"✏️  Files to Modify: {len(final_plan.get('file_changes', {}).get('files_to_modify', []))}"
                )

                # Show first few steps
                steps = final_plan.get("implementation", {}).get("steps", [])
                if steps:
                    print("\n🔧 First 3 Implementation Steps:")
                    for i, step in enumerate(steps[:3], 1):
                        print(f"  {i}. {step.get('title', 'Unknown step')}")

                # Show complete final plan JSON
                print("\n" + "=" * 80)
                print("📋 COMPLETE FINAL PLAN JSON")
                print("=" * 80)
                import json

                print(json.dumps(final_plan, indent=2, ensure_ascii=False))
                print("=" * 80)
        else:
            print("❌ Planning failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


def main():
    """Run all tests."""
    print("🚀 PLANNER AGENT TESTING SUITE")
    print("=" * 80)

    # Test 1: Basic functionality
    result1 = test_planner_basic()

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    tests_passed = 0
    total_tests = 1

    if result1.get("success"):
        print("✅ Test 1 (Basic): PASSED")
        tests_passed += 1
    else:
        print("❌ Test 1 (Basic): FAILED")

    print(f"\n📊 Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("🎉 All tests passed! Planner Agent is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the implementation.")

    return tests_passed == total_tests


if __name__ == "__main__":
    # Run tests
    success = main()
    exit(0 if success else 1)
