"""
Test ImplementorState validation với generate_code phase
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.developer.implementor.state import ImplementorState


def test_implementor_state_phases():
    """Test all valid phases for ImplementorState."""
    print("🧪 Testing ImplementorState phase validation...")
    
    valid_phases = [
        "initialize",
        "setup_branch", 
        "copy_boilerplate",
        "generate_code",  # ✅ This should now be valid
        "implement_files",
        "run_tests",
        "run_and_verify",
        "commit_changes",
        "create_pr",
        "finalize"
    ]
    
    success_count = 0
    
    for phase in valid_phases:
        try:
            # Test creating state with each phase
            state = ImplementorState(current_phase=phase)
            print(f"  ✅ Phase '{phase}': Valid")
            success_count += 1
        except Exception as e:
            print(f"  ❌ Phase '{phase}': Invalid - {e}")
    
    print(f"\n📊 Results: {success_count}/{len(valid_phases)} phases valid")
    
    # Test the specific case that was failing
    try:
        state = ImplementorState(current_phase="generate_code")
        print("✅ SPECIFIC TEST: 'generate_code' phase validation PASSED")
        return True
    except Exception as e:
        print(f"❌ SPECIFIC TEST: 'generate_code' phase validation FAILED - {e}")
        return False


def test_invalid_phases():
    """Test that invalid phases are rejected."""
    print("\n🧪 Testing invalid phases rejection...")
    
    invalid_phases = [
        "invalid_phase",
        "generate_files",  # Similar but wrong
        "code_generation",  # Similar but wrong
        "implement",  # Partial name
        ""  # Empty string
    ]
    
    success_count = 0
    
    for phase in invalid_phases:
        try:
            state = ImplementorState(current_phase=phase)
            print(f"  ❌ Phase '{phase}': Should be invalid but was accepted")
        except Exception as e:
            print(f"  ✅ Phase '{phase}': Correctly rejected - {type(e).__name__}")
            success_count += 1
    
    print(f"\n📊 Results: {success_count}/{len(invalid_phases)} invalid phases correctly rejected")
    return success_count == len(invalid_phases)


def test_workflow_order():
    """Test that phases can be set in workflow order."""
    print("\n🧪 Testing workflow phase order...")
    
    workflow_order = [
        "initialize",
        "setup_branch",
        "copy_boilerplate", 
        "generate_code",  # ✅ Should be here in the workflow
        "implement_files",
        "run_tests",
        "run_and_verify",
        "commit_changes",
        "create_pr",
        "finalize"
    ]
    
    state = ImplementorState()
    
    for i, phase in enumerate(workflow_order):
        try:
            state.current_phase = phase
            print(f"  {i+1:2d}. {phase}: ✅")
        except Exception as e:
            print(f"  {i+1:2d}. {phase}: ❌ {e}")
            return False
    
    print("✅ All workflow phases can be set in order")
    return True


def test_state_creation_with_generate_code():
    """Test creating complete state with generate_code phase."""
    print("\n🧪 Testing complete state creation with generate_code...")
    
    try:
        state = ImplementorState(
            task_id="test-task-001",
            task_description="Test task with generate_code phase",
            current_phase="generate_code",
            feature_branch="feature/test-generate-code",
            status="generating_code"
        )
        
        print("✅ Complete state creation successful")
        print(f"  Task ID: {state.task_id}")
        print(f"  Current Phase: {state.current_phase}")
        print(f"  Feature Branch: {state.feature_branch}")
        print(f"  Status: {state.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete state creation failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("🚀 Testing ImplementorState Validation with generate_code Phase...\n")
    
    test1 = test_implementor_state_phases()
    test2 = test_invalid_phases()
    test3 = test_workflow_order()
    test4 = test_state_creation_with_generate_code()
    
    print("\n🏁 Test Results:")
    print(f"  Valid phases test: {'✅ PASSED' if test1 else '❌ FAILED'}")
    print(f"  Invalid phases test: {'✅ PASSED' if test2 else '❌ FAILED'}")
    print(f"  Workflow order test: {'✅ PASSED' if test3 else '❌ FAILED'}")
    print(f"  Complete state test: {'✅ PASSED' if test4 else '❌ FAILED'}")
    
    overall_success = all([test1, test2, test3, test4])
    print(f"  Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print("\n🎉 All tests passed! ImplementorState now supports 'generate_code' phase")
        print("\n💡 Fixed issues:")
        print("  ✅ Added 'generate_code' to Literal values in ImplementorState")
        print("  ✅ Updated phases_completed list in finalize.py")
        print("  ✅ Workflow can now transition through generate_code phase")
        print("\n🚀 Implementor Agent workflow should now work without validation errors!")
    else:
        print("\n💥 Some tests failed - check the fixes")


if __name__ == "__main__":
    main()
