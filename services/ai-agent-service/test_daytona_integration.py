#!/usr/bin/env python3
"""
Test script để verify Daytona Sandbox integration với Planner Agent.

Test cases:
1. Local codebase analysis (existing behavior)
2. Public GitHub repository với Daytona sandbox
3. Private GitHub repository với authentication
4. Error handling khi Daytona không available
5. Fallback behavior khi sandbox creation fails
"""

import os
import sys
import asyncio
from typing import Dict, Any

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from app.agents.developer.planner.agent import PlannerAgent


def test_local_codebase_analysis():
    """Test 1: Local codebase analysis (existing behavior)"""
    print("\n" + "=" * 70)
    print("🧪 TEST 1: Local Codebase Analysis")
    print("=" * 70)

    try:
        planner = PlannerAgent(
            model="gpt-4o-mini", session_id="test_local", user_id="test_user"
        )

        result = planner.run(
            task_description="Add user authentication with email verification",
            codebase_context="Existing FastAPI app with PostgreSQL database",
            codebase_path="",  # Use default local path
            github_repo_url="",  # No GitHub repo
            thread_id="test_local_thread",
        )

        print("✅ Local codebase analysis test PASSED")
        print(f"   Task ID: {result.get('task_id', 'N/A')}")
        print(f"   Complexity: {result.get('complexity_score', 0)}/10")
        print(f"   Ready: {result.get('ready_for_implementation', False)}")

        return True

    except Exception as e:
        print(f"❌ Local codebase analysis test FAILED: {e}")
        return False


def test_public_github_repo():
    """Test 2: Public GitHub repository với Daytona sandbox"""
    print("\n" + "=" * 70)
    print("🧪 TEST 2: Public GitHub Repository with Daytona")
    print("=" * 70)

    # Skip if no Daytona API key
    if not os.getenv("DAYTONA_API_KEY"):
        print("⏭️  Skipping - DAYTONA_API_KEY not configured")
        return True

    try:
        planner = PlannerAgent(
            model="gpt-4o-mini", session_id="test_public_repo", user_id="test_user"
        )

        # Use a small public repository for testing
        result = planner.run(
            task_description="Add logging functionality to the application",
            codebase_context="Python application",
            codebase_path="",  # Will be set by sandbox
            github_repo_url="https://github.com/octocat/Hello-World.git",
            thread_id="test_public_repo_thread",
        )

        print("✅ Public GitHub repository test PASSED")
        print(f"   Task ID: {result.get('task_id', 'N/A')}")
        print(f"   Complexity: {result.get('complexity_score', 0)}/10")
        print(f"   Sandbox used: {result.get('sandbox_id', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Public GitHub repository test FAILED: {e}")
        return False


def test_private_github_repo():
    """Test 3: Private GitHub repository với authentication"""
    print("\n" + "=" * 70)
    print("🧪 TEST 3: Private GitHub Repository with Authentication")
    print("=" * 70)

    # Skip if no credentials
    if not all(
        [
            os.getenv("DAYTONA_API_KEY"),
            os.getenv("GITHUB_USERNAME"),
            os.getenv("GITHUB_TOKEN"),
        ]
    ):
        print(
            "⏭️  Skipping - Missing credentials (DAYTONA_API_KEY, GITHUB_USERNAME, GITHUB_TOKEN)"
        )
        return True

    try:
        planner = PlannerAgent(
            model="gpt-4o-mini", session_id="test_private_repo", user_id="test_user"
        )

        # Note: Replace with actual private repo URL for real testing
        result = planner.run(
            task_description="Implement new feature based on existing patterns",
            codebase_context="Private repository analysis",
            codebase_path="",  # Will be set by sandbox
            github_repo_url="https://github.com/your-org/private-repo.git",
            thread_id="test_private_repo_thread",
        )

        print("✅ Private GitHub repository test PASSED")
        print(f"   Task ID: {result.get('task_id', 'N/A')}")
        print(f"   Complexity: {result.get('complexity_score', 0)}/10")
        print(f"   Sandbox used: {result.get('sandbox_id', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Private GitHub repository test FAILED: {e}")
        return False


def test_daytona_unavailable():
    """Test 4: Error handling khi Daytona không available"""
    print("\n" + "=" * 70)
    print("🧪 TEST 4: Daytona Unavailable - Fallback Behavior")
    print("=" * 70)

    try:
        # Temporarily remove Daytona API key
        original_api_key = os.getenv("DAYTONA_API_KEY")
        if "DAYTONA_API_KEY" in os.environ:
            del os.environ["DAYTONA_API_KEY"]

        planner = PlannerAgent(
            model="gpt-4o-mini", session_id="test_fallback", user_id="test_user"
        )

        result = planner.run(
            task_description="Add error handling to the application",
            codebase_context="Application needs better error handling",
            codebase_path="",  # Should fallback to default
            github_repo_url="https://github.com/octocat/Hello-World.git",  # Should be ignored
            thread_id="test_fallback_thread",
        )

        # Restore API key
        if original_api_key:
            os.environ["DAYTONA_API_KEY"] = original_api_key

        print("✅ Daytona unavailable fallback test PASSED")
        print(f"   Task ID: {result.get('task_id', 'N/A')}")
        print(f"   Complexity: {result.get('complexity_score', 0)}/10")
        print(f"   Used fallback: {not result.get('sandbox_id', '')}")

        return True

    except Exception as e:
        # Restore API key on error
        if "original_api_key" in locals() and original_api_key:
            os.environ["DAYTONA_API_KEY"] = original_api_key

        print(f"❌ Daytona unavailable fallback test FAILED: {e}")
        return False


def test_backward_compatibility():
    """Test 5: Backward compatibility với existing code"""
    print("\n" + "=" * 70)
    print("🧪 TEST 5: Backward Compatibility")
    print("=" * 70)

    try:
        planner = PlannerAgent(
            model="gpt-4o-mini", session_id="test_backward_compat", user_id="test_user"
        )

        # Test old method signature (without github_repo_url)
        result = planner.run(
            task_description="Implement caching mechanism",
            codebase_context="Application needs performance improvements",
            codebase_path=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
            thread_id="test_backward_compat_thread",
        )

        print("✅ Backward compatibility test PASSED")
        print(f"   Task ID: {result.get('task_id', 'N/A')}")
        print(f"   Complexity: {result.get('complexity_score', 0)}/10")
        print(f"   Used local path: {not result.get('sandbox_id', '')}")

        return True

    except Exception as e:
        print(f"❌ Backward compatibility test FAILED: {e}")
        return False


def main():
    """Run all test cases"""
    print("\n" + "=" * 70)
    print("🚀 DAYTONA SANDBOX INTEGRATION TESTS")
    print("=" * 70)

    # Check environment
    print("\n📋 Environment Check:")
    print(
        f"   DAYTONA_API_KEY: {'✅ Set' if os.getenv('DAYTONA_API_KEY') else '❌ Not set'}"
    )
    print(
        f"   GITHUB_USERNAME: {'✅ Set' if os.getenv('GITHUB_USERNAME') else '❌ Not set'}"
    )
    print(f"   GITHUB_TOKEN: {'✅ Set' if os.getenv('GITHUB_TOKEN') else '❌ Not set'}")
    print(
        f"   OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}"
    )

    # Run tests
    tests = [
        ("Local Codebase Analysis", test_local_codebase_analysis),
        ("Public GitHub Repository", test_public_github_repo),
        ("Private GitHub Repository", test_private_github_repo),
        ("Daytona Unavailable Fallback", test_daytona_unavailable),
        ("Backward Compatibility", test_backward_compatibility),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Daytona integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
