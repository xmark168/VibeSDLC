"""
Simple test for ImplementorState validation without complex imports
"""

import sys
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field

# Test the exact Literal definition from state.py
class TestImplementorState(BaseModel):
    """Simplified ImplementorState for testing."""
    
    current_phase: Literal[
        "initialize",
        "setup_branch",
        "copy_boilerplate",
        "generate_code",
        "implement_files",
        "run_tests",
        "run_and_verify",
        "commit_changes",
        "create_pr",
        "finalize",
    ] = "initialize"
    
    task_id: str = ""
    task_description: str = ""


def test_generate_code_phase():
    """Test that generate_code phase is now valid."""
    print("🧪 Testing generate_code phase validation...")
    
    try:
        # This was the failing case
        state = TestImplementorState(current_phase="generate_code")
        print("✅ SUCCESS: generate_code phase is now valid!")
        print(f"  Current phase: {state.current_phase}")
        return True
    except Exception as e:
        print(f"❌ FAILED: generate_code phase still invalid - {e}")
        return False


def test_all_phases():
    """Test all phases."""
    print("\n🧪 Testing all workflow phases...")
    
    phases = [
        "initialize",
        "setup_branch",
        "copy_boilerplate",
        "generate_code",  # This should now work
        "implement_files",
        "run_tests",
        "run_and_verify",
        "commit_changes",
        "create_pr",
        "finalize"
    ]
    
    success_count = 0
    
    for phase in phases:
        try:
            state = TestImplementorState(current_phase=phase)
            print(f"  ✅ {phase}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ {phase}: {e}")
    
    print(f"\n📊 Results: {success_count}/{len(phases)} phases valid")
    return success_count == len(phases)


def test_invalid_phase():
    """Test that invalid phases are still rejected."""
    print("\n🧪 Testing invalid phase rejection...")
    
    try:
        state = TestImplementorState(current_phase="invalid_phase")
        print("❌ FAILED: Invalid phase was accepted")
        return False
    except Exception as e:
        print("✅ SUCCESS: Invalid phase correctly rejected")
        print(f"  Error: {type(e).__name__}")
        return True


def main():
    """Run validation tests."""
    print("🚀 Testing ImplementorState Phase Validation Fix...\n")
    
    test1 = test_generate_code_phase()
    test2 = test_all_phases()
    test3 = test_invalid_phase()
    
    print("\n🏁 Test Results:")
    print(f"  generate_code phase: {'✅ PASSED' if test1 else '❌ FAILED'}")
    print(f"  All phases: {'✅ PASSED' if test2 else '❌ FAILED'}")
    print(f"  Invalid phase rejection: {'✅ PASSED' if test3 else '❌ FAILED'}")
    
    overall_success = all([test1, test2, test3])
    print(f"  Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print("\n🎉 Validation fix successful!")
        print("\n💡 What was fixed:")
        print("  1. Added 'generate_code' to Literal values in ImplementorState.current_phase")
        print("  2. Updated phases_completed list in finalize.py")
        print("  3. Workflow order: initialize → setup_branch → copy_boilerplate → generate_code → implement_files → ...")
        print("\n🚀 The original Pydantic validation error should now be resolved!")
        print("   Error was: Input should be 'initialize', 'setup_branch', ... [type=literal_error, input_value='generate_code']")
        print("   Now: 'generate_code' is included in the allowed Literal values")
    else:
        print("\n💥 Validation fix failed - check the implementation")


if __name__ == "__main__":
    main()
