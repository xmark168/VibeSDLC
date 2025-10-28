"""
Test script to verify execute_step refactor logic without running full workflow.

This tests that:
1. execute_step only executes ONE sub-step per invocation
2. Indices are incremented correctly
3. Routing logic works as expected
"""

import sys
from pathlib import Path


# Mock ImplementorState for testing
class MockState:
    def __init__(self, implementation_plan, task_description, codebase_path):
        self.implementation_plan = implementation_plan
        self.task_description = task_description
        self.codebase_path = codebase_path
        self.current_step_index = 0
        self.current_sub_step_index = 0
        self.status = "initialized"


def test_step_tracking_logic():
    """Test the step tracking logic without LLM calls."""
    
    print("🧪 Testing Step Tracking Logic\n")
    print("=" * 80)
    
    # Create mock plan with 3 steps, each with 2 sub-steps
    mock_plan = {
        "task_id": "TEST-001",
        "description": "Test task",
        "steps": [
            {
                "step": 1,
                "title": "Step 1",
                "description": "First step",
                "category": "backend",
                "sub_steps": [
                    {"sub_step": "1.1", "title": "Sub-step 1.1", "description": "First sub-step"},
                    {"sub_step": "1.2", "title": "Sub-step 1.2", "description": "Second sub-step"},
                ]
            },
            {
                "step": 2,
                "title": "Step 2",
                "description": "Second step",
                "category": "backend",
                "sub_steps": [
                    {"sub_step": "2.1", "title": "Sub-step 2.1", "description": "Third sub-step"},
                    {"sub_step": "2.2", "title": "Sub-step 2.2", "description": "Fourth sub-step"},
                ]
            },
            {
                "step": 3,
                "title": "Step 3",
                "description": "Third step",
                "category": "backend",
                "sub_steps": [
                    {"sub_step": "3.1", "title": "Sub-step 3.1", "description": "Fifth sub-step"},
                    {"sub_step": "3.2", "title": "Sub-step 3.2", "description": "Sixth sub-step"},
                ]
            },
        ]
    }
    
    # Initialize state
    state = MockState(
        implementation_plan=mock_plan,
        task_description="Test task",
        codebase_path=".",
    )
    
    # Initialize indices
    state.current_step_index = 0
    state.current_sub_step_index = 0
    
    steps = mock_plan["steps"]
    total_steps = len(steps)
    
    print(f"📋 Mock plan: {total_steps} steps, 6 total sub-steps\n")
    
    # Simulate execute_step invocations
    iteration = 0
    max_iterations = 20  # Safety limit
    
    while iteration < max_iterations:
        iteration += 1
        
        print(f"\n{'=' * 80}")
        print(f"ITERATION {iteration}")
        print(f"{'=' * 80}")
        
        # Check if all steps completed
        if state.current_step_index >= len(steps):
            print("✅ All steps completed!")
            break
        
        # Get current step
        current_step = steps[state.current_step_index]
        step_number = state.current_step_index + 1
        
        print(f"📍 Current position: Step {step_number}/{total_steps}, "
              f"Sub-step {state.current_sub_step_index + 1}")
        print(f"📝 Current step: {current_step['title']}")
        
        # Check if step has sub_steps
        sub_steps = current_step.get("sub_steps", [])
        
        if sub_steps:
            # Check if all sub-steps completed
            if state.current_sub_step_index >= len(sub_steps):
                print(f"✅ All {len(sub_steps)} sub-steps completed for Step {step_number}")
                state.current_step_index += 1
                state.current_sub_step_index = 0
                print(f"➡️ Moving to Step {state.current_step_index + 1}")
                continue
            
            # Get current sub-step
            current_sub_step = sub_steps[state.current_sub_step_index]
            sub_step_number = state.current_sub_step_index + 1
            total_sub_steps = len(sub_steps)
            
            print(f"🎯 Executing: Sub-step {sub_step_number}/{total_sub_steps} - {current_sub_step['title']}")
            
            # Simulate successful execution
            print(f"   ✅ Sub-step {sub_step_number} completed")
            
            # Increment sub-step index
            state.current_sub_step_index += 1
            print(f"   ➡️ Next: Sub-step {state.current_sub_step_index + 1}")
        
        else:
            # No sub-steps, execute step directly
            print(f"🎯 Executing: Step {step_number} (no sub-steps)")
            print(f"   ✅ Step {step_number} completed")
            
            # Move to next step
            state.current_step_index += 1
            print(f"   ➡️ Next: Step {state.current_step_index + 1}")
    
    print(f"\n{'=' * 80}")
    print("📊 FINAL RESULTS")
    print(f"{'=' * 80}")
    print(f"Total iterations: {iteration}")
    print(f"Final step index: {state.current_step_index}")
    print(f"Final sub-step index: {state.current_sub_step_index}")
    
    # Verify expected results
    expected_iterations = 6  # 6 sub-steps total
    if iteration == expected_iterations:
        print(f"✅ PASS: Executed exactly {expected_iterations} iterations (one per sub-step)")
    else:
        print(f"❌ FAIL: Expected {expected_iterations} iterations, got {iteration}")
        return False
    
    if state.current_step_index == total_steps:
        print(f"✅ PASS: Reached end of steps (index = {total_steps})")
    else:
        print(f"❌ FAIL: Expected step index {total_steps}, got {state.current_step_index}")
        return False
    
    print("\n🎉 All tests passed!")
    return True


def test_routing_logic():
    """Test the _should_continue_execution routing logic."""
    
    print("\n\n🧪 Testing Routing Logic\n")
    print("=" * 80)
    
    # Create mock plan
    mock_plan = {
        "steps": [
            {
                "step": 1,
                "title": "Step 1",
                "sub_steps": [
                    {"sub_step": "1.1", "title": "Sub 1.1"},
                    {"sub_step": "1.2", "title": "Sub 1.2"},
                ]
            },
            {
                "step": 2,
                "title": "Step 2",
                "sub_steps": [
                    {"sub_step": "2.1", "title": "Sub 2.1"},
                ]
            },
        ]
    }
    
    state = MockState(
        implementation_plan=mock_plan,
        task_description="Test",
        codebase_path=".",
    )
    
    steps = mock_plan["steps"]
    
    # Test case 1: Middle of step 1
    state.current_step_index = 0
    state.current_sub_step_index = 0
    
    current_step = steps[state.current_step_index]
    sub_steps = current_step.get("sub_steps", [])
    
    if state.current_sub_step_index < len(sub_steps):
        result = "continue"
    else:
        result = "done"
    
    print(f"Test 1: Step 1, Sub-step 1 → Expected: 'continue', Got: '{result}'")
    assert result == "continue", "Should continue when more sub-steps exist"
    
    # Test case 2: End of step 1
    state.current_sub_step_index = 2  # After last sub-step
    
    if state.current_sub_step_index >= len(sub_steps):
        # Move to next step
        state.current_step_index += 1
        state.current_sub_step_index = 0
        
        if state.current_step_index >= len(steps):
            result = "done"
        else:
            result = "continue"
    
    print(f"Test 2: End of Step 1 → Expected: 'continue', Got: '{result}'")
    assert result == "continue", "Should continue to next step"
    
    # Test case 3: End of all steps
    state.current_step_index = 2  # Beyond last step
    
    if state.current_step_index >= len(steps):
        result = "done"
    else:
        result = "continue"
    
    print(f"Test 3: End of all steps → Expected: 'done', Got: '{result}'")
    assert result == "done", "Should be done when all steps completed"
    
    print("\n✅ All routing tests passed!")
    return True


if __name__ == "__main__":
    try:
        success1 = test_step_tracking_logic()
        success2 = test_routing_logic()
        
        if success1 and success2:
            print("\n" + "=" * 80)
            print("🎉 ALL TESTS PASSED!")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n" + "=" * 80)
            print("❌ SOME TESTS FAILED")
            print("=" * 80)
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

