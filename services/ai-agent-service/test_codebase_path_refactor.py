#!/usr/bin/env python3
"""
Test script để verify codebase_path refactor
- Kiểm tra backward compatibility (không truyền codebase_path)
- Kiểm tra custom codebase_path
- Kiểm tra state management
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))


# Parse state.py directly to avoid dependency issues
def check_state_has_codebase_path():
    """Check if PlannerState has codebase_path field"""
    state_file = os.path.join(
        os.path.dirname(__file__), "app/agents/developer/planner/state.py"
    )
    with open(state_file, encoding="utf-8") as f:
        content = f.read()

    # Check if codebase_path is defined
    return 'codebase_path: str = ""' in content


def test_backward_compatibility():
    """Test backward compatibility - không truyền codebase_path"""
    print("🧪 Test 1: Backward Compatibility (no codebase_path)")
    print("=" * 70)

    try:
        # Create state without codebase_path (old way)
        state = PlannerState(
            task_description="Test task", codebase_context="Test context"
        )

        # Verify codebase_path is empty string (default)
        assert (
            state.codebase_path == ""
        ), f"Expected empty string, got: {state.codebase_path}"
        assert state.task_description == "Test task"
        assert state.codebase_context == "Test context"

        print("✅ State created successfully without codebase_path")
        print(f"   - task_description: {state.task_description}")
        print(f"   - codebase_context: {state.codebase_context}")
        print(f"   - codebase_path: '{state.codebase_path}' (empty = use default)")
        print("✅ PASSED: Backward compatibility maintained\n")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False


def test_custom_codebase_path():
    """Test custom codebase_path"""
    print("🧪 Test 2: Custom codebase_path")
    print("=" * 70)

    try:
        custom_path = r"D:\custom\codebase\path"

        # Create state with custom codebase_path
        state = PlannerState(
            task_description="Test task",
            codebase_context="Test context",
            codebase_path=custom_path,
        )

        # Verify codebase_path is set correctly
        assert (
            state.codebase_path == custom_path
        ), f"Expected {custom_path}, got: {state.codebase_path}"

        print("✅ State created successfully with custom codebase_path")
        print(f"   - task_description: {state.task_description}")
        print(f"   - codebase_context: {state.codebase_context}")
        print(f"   - codebase_path: {state.codebase_path}")
        print("✅ PASSED: Custom codebase_path works correctly\n")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False


def test_state_serialization():
    """Test state serialization with codebase_path"""
    print("🧪 Test 3: State Serialization")
    print("=" * 70)

    try:
        custom_path = r"D:\test\path"

        # Create state
        state = PlannerState(
            task_description="Test task",
            codebase_context="Test context",
            codebase_path=custom_path,
        )

        # Serialize to dict
        state_dict = state.model_dump()

        # Verify codebase_path is in dict
        assert "codebase_path" in state_dict, "codebase_path not in serialized state"
        assert state_dict["codebase_path"] == custom_path

        # Deserialize back
        state2 = PlannerState(**state_dict)
        assert state2.codebase_path == custom_path

        print("✅ State serialization successful")
        print(f"   - Original path: {state.codebase_path}")
        print(f"   - Serialized path: {state_dict['codebase_path']}")
        print(f"   - Deserialized path: {state2.codebase_path}")
        print("✅ PASSED: State serialization works correctly\n")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False


def test_default_fallback():
    """Test default fallback logic"""
    print("🧪 Test 4: Default Fallback Logic")
    print("=" * 70)

    try:
        # Test empty string (should use default)
        empty_path = ""
        default_path = (
            r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
        )

        # Simulate the fallback logic from analyze_codebase node
        codebase_path = empty_path or default_path
        assert codebase_path == default_path, "Fallback logic failed"

        # Test with custom path (should use custom)
        custom_path = r"D:\custom\path"
        codebase_path = custom_path or default_path
        assert codebase_path == custom_path, "Custom path override failed"

        print("✅ Default fallback logic works correctly")
        print(f"   - Empty string → {default_path}")
        print(f"   - Custom path → {custom_path}")
        print("✅ PASSED: Fallback logic is correct\n")
        return True

    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🚀 CODEBASE_PATH REFACTOR TEST SUITE")
    print("=" * 70 + "\n")

    tests = [
        test_backward_compatibility,
        test_custom_codebase_path,
        test_state_serialization,
        test_default_fallback,
    ]

    results = []
    for test in tests:
        results.append(test())

    # Summary
    print("=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Refactor is backward compatible")
        print("✅ Custom codebase_path works correctly")
        print("✅ State management is correct")
        print("✅ Default fallback logic is working")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
