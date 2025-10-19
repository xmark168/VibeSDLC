"""
Simple Test for Developer Agent Components

Test individual components without external dependencies.
"""

import json
import tempfile
from pathlib import Path


def test_state_model():
    """Test DeveloperState model."""
    print("🧪 Testing DeveloperState model...")
    
    try:
        from app.agents.developer.state import DeveloperState, TaskResult, SprintExecutionSummary
        
        # Test basic state creation
        state = DeveloperState()
        assert state.current_phase == "initialize"
        assert state.current_task_index == 0
        assert len(state.eligible_tasks) == 0
        
        # Test with custom values
        state = DeveloperState(
            working_directory="/test/dir",
            model_name="gpt-4",
            session_id="test_session"
        )
        assert state.working_directory == "/test/dir"
        assert state.model_name == "gpt-4"
        assert state.session_id == "test_session"
        
        # Test TaskResult
        task_result = TaskResult(
            task_id="TEST-001",
            task_type="Development",
            status="success"
        )
        assert task_result.task_id == "TEST-001"
        assert task_result.status == "success"
        
        print("✅ State model test passed!")
        return True
        
    except Exception as e:
        print(f"❌ State model test failed: {e}")
        return False


def test_parse_sprint_node():
    """Test parse_sprint node."""
    print("🧪 Testing parse_sprint node...")
    
    try:
        from app.agents.developer.state import DeveloperState
        from app.agents.developer.nodes.parse_sprint import parse_sprint
        
        # Create test data
        backlog_data = [
            {
                "id": "TASK-001",
                "type": "Task",
                "title": "Test task",
                "description": "Test description",
                "task_type": "Development"
            }
        ]
        
        sprint_data = [
            {
                "sprint_id": "test-sprint",
                "sprint_goal": "Test goal",
                "assigned_items": ["TASK-001"]
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write test files
            backlog_file = temp_path / "backlog.json"
            sprint_file = temp_path / "sprint.json"
            
            with open(backlog_file, 'w') as f:
                json.dump(backlog_data, f)
            
            with open(sprint_file, 'w') as f:
                json.dump(sprint_data, f)
            
            # Test parse_sprint
            state = DeveloperState(
                backlog_path=str(backlog_file),
                sprint_path=str(sprint_file)
            )
            
            result_state = parse_sprint(state)
            
            # Verify results
            assert result_state.current_phase == "filter_tasks"
            assert len(result_state.backlog_data) == 1
            assert result_state.sprint_data["sprint_id"] == "test-sprint"
            assert result_state.execution_summary.sprint_id == "test-sprint"
            assert result_state.execution_summary.total_assigned_items == 1
            
        print("✅ Parse sprint node test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Parse sprint node test failed: {e}")
        return False


def test_filter_tasks_node():
    """Test filter_tasks node."""
    print("🧪 Testing filter_tasks node...")
    
    try:
        from app.agents.developer.state import DeveloperState
        from app.agents.developer.nodes.filter_tasks import filter_tasks
        
        # Create test data
        backlog_data = [
            {
                "id": "EPIC-001",
                "type": "Epic",
                "title": "Test Epic",
                "description": "Epic description",
                "business_value": "Test value"
            },
            {
                "id": "TASK-001",
                "type": "Task",
                "parent_id": "EPIC-001",
                "title": "Development Task",
                "description": "Dev task description",
                "task_type": "Development"
            },
            {
                "id": "TASK-002",
                "type": "Task",
                "parent_id": "EPIC-001",
                "title": "Infrastructure Task",
                "description": "Infra task description",
                "task_type": "Infrastructure"
            },
            {
                "id": "US-001",
                "type": "User Story",
                "title": "User Story",
                "description": "User story description",
                "task_type": None  # Should be filtered out
            }
        ]
        
        sprint_data = {
            "sprint_id": "test-sprint",
            "assigned_items": ["TASK-001", "TASK-002", "US-001", "MISSING-TASK"]
        }
        
        # Test filter_tasks
        state = DeveloperState(
            backlog_data=backlog_data,
            sprint_data=sprint_data
        )
        
        result_state = filter_tasks(state)
        
        # Verify results
        assert result_state.current_phase == "process_tasks"
        assert len(result_state.eligible_tasks) == 2  # Only TASK-001 and TASK-002
        assert result_state.execution_summary.eligible_tasks_count == 2
        
        # Check task enrichment
        task1 = result_state.eligible_tasks[0]
        assert task1["id"] == "TASK-001"
        assert task1["task_type"] == "Development"
        assert "Epic: Test Epic" in task1["parent_context"]
        assert "Epic description" in task1["parent_context"]
        assert "Test value" in task1["parent_context"]
        
        task2 = result_state.eligible_tasks[1]
        assert task2["id"] == "TASK-002"
        assert task2["task_type"] == "Infrastructure"
        
        print("✅ Filter tasks node test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Filter tasks node test failed: {e}")
        return False


def test_initialize_node():
    """Test initialize node."""
    print("🧪 Testing initialize node...")
    
    try:
        from app.agents.developer.state import DeveloperState
        from app.agents.developer.nodes.initialize import initialize
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create dummy files
            backlog_file = temp_path / "backlog.json"
            sprint_file = temp_path / "sprint.json"
            
            backlog_file.write_text("[]")
            sprint_file.write_text("[]")
            
            # Test initialize
            state = DeveloperState(
                backlog_path=str(backlog_file),
                sprint_path=str(sprint_file)
            )
            
            result_state = initialize(state)
            
            # Verify results
            assert result_state.current_phase == "parse_sprint"
            assert result_state.session_id != ""
            assert result_state.execution_summary.start_time is not None
            
        print("✅ Initialize node test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Initialize node test failed: {e}")
        return False


def test_workflow_structure():
    """Test workflow structure without execution."""
    print("🧪 Testing workflow structure...")
    
    try:
        # Test that all nodes are importable
        from app.agents.developer.nodes import (
            initialize,
            parse_sprint,
            filter_tasks,
            process_tasks,
            finalize
        )
        
        # Test that all functions are callable
        assert callable(initialize)
        assert callable(parse_sprint)
        assert callable(filter_tasks)
        assert callable(process_tasks)
        assert callable(finalize)
        
        print("✅ Workflow structure test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Workflow structure test failed: {e}")
        return False


def main():
    """Run all simple tests."""
    print("🚀 Testing Developer Agent Components...\n")
    
    tests = [
        ("State Model", test_state_model),
        ("Initialize Node", test_initialize_node),
        ("Parse Sprint Node", test_parse_sprint_node),
        ("Filter Tasks Node", test_filter_tasks_node),
        ("Workflow Structure", test_workflow_structure),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name}")
        print(f"{'='*50}")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
    
    print(f"\n{'='*50}")
    print(f"🎯 TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All component tests passed!")
        return True
    else:
        print("💥 Some component tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
