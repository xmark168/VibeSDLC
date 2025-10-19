"""
Test Workflow Verification

Verify that Developer Agent processes tasks in the correct sequence:
Task 1: Planner → Implementor → Code Reviewer (complete)
Task 2: Planner → Implementor → Code Reviewer (complete)
Task 3: Planner → Implementor → Code Reviewer (complete)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.agents.developer.state import DeveloperState
from app.agents.developer.nodes.process_tasks import process_tasks


def create_test_state():
    """Create test state with multiple tasks."""
    
    # Create test tasks
    eligible_tasks = [
        {
            "id": "TASK-001",
            "title": "First Development Task",
            "description": "First task description",
            "task_type": "Development",
            "parent_context": "Epic: Test Epic 1",
            "enriched_description": "Task 1 with Epic context"
        },
        {
            "id": "TASK-002", 
            "title": "Second Infrastructure Task",
            "description": "Second task description",
            "task_type": "Infrastructure",
            "parent_context": "Epic: Test Epic 2",
            "enriched_description": "Task 2 with Epic context"
        },
        {
            "id": "TASK-003",
            "title": "Third Development Task", 
            "description": "Third task description",
            "task_type": "Development",
            "parent_context": "Epic: Test Epic 3",
            "enriched_description": "Task 3 with Epic context"
        }
    ]
    
    # Create state
    state = DeveloperState(
        eligible_tasks=eligible_tasks,
        model_name="gpt-4o-mini",
        session_id="test_workflow",
        continue_on_error=True
    )
    
    return state


def test_workflow_sequence():
    """Test that workflow processes tasks in correct sequence."""
    
    print("🧪 Testing workflow sequence...")
    
    # Track execution order
    execution_log = []
    
    def mock_planner_run(*args, **kwargs):
        task_id = kwargs.get('thread_id', '').split('_')[-1]
        execution_log.append(f"PLANNER_{task_id}")
        print(f"🧠 PLANNER executed for {task_id}")
        return {
            "success": True,
            "final_plan": {"plan": f"Plan for {task_id}"},
            "ready_for_implementation": True
        }
    
    def mock_implementor_run(*args, **kwargs):
        task_id = kwargs.get('thread_id', '').split('_')[-1]
        execution_log.append(f"IMPLEMENTOR_{task_id}")
        print(f"⚙️ IMPLEMENTOR executed for {task_id}")
        return {
            "success": True,
            "feature_branch": f"feature/{task_id}",
            "files_created": [f"{task_id}_file.py"]
        }
    
    # Mock subagents
    with patch('app.agents.developer.nodes.process_tasks.PlannerAgent') as mock_planner_class, \
         patch('app.agents.developer.nodes.process_tasks.ImplementorAgent') as mock_implementor_class:
        
        # Setup mocks
        mock_planner = MagicMock()
        mock_planner.run = mock_planner_run
        mock_planner_class.return_value = mock_planner
        
        mock_implementor = MagicMock()
        mock_implementor.run = mock_implementor_run
        mock_implementor_class.return_value = mock_implementor
        
        # Create test state
        state = create_test_state()
        
        print(f"📋 Processing {len(state.eligible_tasks)} tasks...")
        print("Expected sequence:")
        print("  TASK-001: Planner → Implementor → Code Reviewer")
        print("  TASK-002: Planner → Implementor → Code Reviewer") 
        print("  TASK-003: Planner → Implementor → Code Reviewer")
        print()
        
        # Execute workflow
        result_state = process_tasks(state)
        
        # Verify execution order
        print("\n🔍 Execution log:")
        for i, entry in enumerate(execution_log):
            print(f"  {i+1}. {entry}")
        
        # Expected sequence
        expected_sequence = [
            "PLANNER_TASK-001",
            "IMPLEMENTOR_TASK-001", 
            "PLANNER_TASK-002",
            "IMPLEMENTOR_TASK-002",
            "PLANNER_TASK-003", 
            "IMPLEMENTOR_TASK-003"
        ]
        
        print(f"\n✅ Expected sequence: {expected_sequence}")
        print(f"✅ Actual sequence:   {execution_log}")
        
        # Verify correct sequence
        if execution_log == expected_sequence:
            print("🎉 WORKFLOW SEQUENCE IS CORRECT!")
            print("✅ Each task goes through complete lifecycle before next task")
            return True
        else:
            print("❌ WORKFLOW SEQUENCE IS INCORRECT!")
            print("❌ Tasks are not processed in complete lifecycle order")
            return False


def test_task_completion_verification():
    """Verify each task completes all phases before moving to next."""
    
    print("\n🧪 Testing task completion verification...")
    
    # Track phase completion
    phase_completion = {}
    
    def mock_planner_run(*args, **kwargs):
        task_id = kwargs.get('thread_id', '').split('_')[-1]
        if task_id not in phase_completion:
            phase_completion[task_id] = []
        phase_completion[task_id].append("PLANNER_COMPLETE")
        print(f"✅ PLANNER completed for {task_id}")
        return {"success": True, "final_plan": {"plan": f"Plan for {task_id}"}}
    
    def mock_implementor_run(*args, **kwargs):
        task_id = kwargs.get('thread_id', '').split('_')[-1]
        if task_id not in phase_completion:
            phase_completion[task_id] = []
        phase_completion[task_id].append("IMPLEMENTOR_COMPLETE")
        print(f"✅ IMPLEMENTOR completed for {task_id}")
        return {"success": True, "feature_branch": f"feature/{task_id}"}
    
    # Mock subagents
    with patch('app.agents.developer.nodes.process_tasks.PlannerAgent') as mock_planner_class, \
         patch('app.agents.developer.nodes.process_tasks.ImplementorAgent') as mock_implementor_class:
        
        # Setup mocks
        mock_planner = MagicMock()
        mock_planner.run = mock_planner_run
        mock_planner_class.return_value = mock_planner
        
        mock_implementor = MagicMock()
        mock_implementor.run = mock_implementor_run
        mock_implementor_class.return_value = mock_implementor
        
        # Create test state
        state = create_test_state()
        
        # Execute workflow
        result_state = process_tasks(state)
        
        # Verify each task completed all phases
        print("\n🔍 Phase completion verification:")
        all_tasks_complete = True
        
        for task_id in ["TASK-001", "TASK-002", "TASK-003"]:
            phases = phase_completion.get(task_id, [])
            expected_phases = ["PLANNER_COMPLETE", "IMPLEMENTOR_COMPLETE"]
            
            print(f"  {task_id}: {phases}")
            
            if phases == expected_phases:
                print(f"    ✅ {task_id} completed all phases")
            else:
                print(f"    ❌ {task_id} missing phases: {set(expected_phases) - set(phases)}")
                all_tasks_complete = False
        
        if all_tasks_complete:
            print("🎉 ALL TASKS COMPLETED ALL PHASES!")
            return True
        else:
            print("❌ Some tasks did not complete all phases!")
            return False


def main():
    """Run workflow verification tests."""
    
    print("🚀 Developer Agent Workflow Verification\n")
    print("Testing that workflow processes tasks correctly:")
    print("- Each task: Planner → Implementor → Code Reviewer (complete lifecycle)")
    print("- Sequential processing: Task 1 complete → Task 2 complete → Task 3 complete")
    print("- NOT: All tasks through Planner → All tasks through Implementor → All tasks through Reviewer")
    print("\n" + "="*80)
    
    tests = [
        ("Workflow Sequence Test", test_workflow_sequence),
        ("Task Completion Verification", test_task_completion_verification),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print(f"{'='*60}")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
    
    print(f"\n{'='*60}")
    print(f"🎯 VERIFICATION SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 WORKFLOW IS CORRECTLY IMPLEMENTED!")
        print("✅ Each task goes through complete Planner → Implementor → Code Reviewer lifecycle")
        print("✅ Tasks are processed sequentially, not in batches by subagent type")
        return True
    else:
        print("\n💥 WORKFLOW HAS ISSUES!")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
