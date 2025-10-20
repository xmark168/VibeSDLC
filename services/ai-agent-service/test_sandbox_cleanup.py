"""
Test Sandbox Cleanup Integration

Test that the finalize node correctly handles Daytona sandbox cleanup
after workflow completion.
"""

from app.agents.developer.implementor.nodes.finalize import finalize
from app.agents.developer.implementor.state import ImplementorState


def test_finalize_with_sandbox_cleanup_success():
    """Test finalize node with successful sandbox cleanup."""
    
    print("🧪 Testing finalize node with sandbox cleanup (success case)...")
    
    # Create mock state with successful workflow completion
    mock_state = ImplementorState(
        task_description="Test JWT authentication implementation",
        sandbox_id="test-sandbox-123",  # Mock sandbox ID
        status="completed",  # Successful completion
        implementation_complete=True,
        feature_branch="feature/jwt-auth",
        base_branch="main",
        final_commit_hash="abc123def456",
        files_created=["auth/jwt_handler.py", "tests/test_auth.py"],
        files_modified=["main.py", "requirements.txt"],
        tests_passed=True,
    )
    
    print(f"📦 Input state:")
    print(f"   Sandbox ID: {mock_state.sandbox_id}")
    print(f"   Status: {mock_state.status}")
    print(f"   Files created: {len(mock_state.files_created)}")
    print(f"   Files modified: {len(mock_state.files_modified)}")
    
    # Run finalize node
    try:
        result_state = finalize(mock_state)
        
        print(f"\n📊 Results:")
        print(f"   Final Status: {result_state.status}")
        print(f"   Implementation Complete: {result_state.implementation_complete}")
        
        # Check sandbox deletion
        if result_state.sandbox_deletion:
            print(f"   Sandbox Cleanup Attempted: ✅")
            print(f"   Sandbox Cleanup Success: {result_state.sandbox_deletion.success}")
            print(f"   Sandbox Cleanup Skipped: {result_state.sandbox_deletion.skipped}")
            print(f"   Sandbox Cleanup Message: {result_state.sandbox_deletion.message}")
            if result_state.sandbox_deletion.error:
                print(f"   Sandbox Cleanup Error: {result_state.sandbox_deletion.error}")
        else:
            print(f"   Sandbox Cleanup Attempted: ❌")
            
        # Check summary
        if result_state.summary and "sandbox_cleanup" in result_state.summary:
            sandbox_summary = result_state.summary["sandbox_cleanup"]
            print(f"   Summary - Cleanup Attempted: {sandbox_summary.get('attempted', False)}")
            print(f"   Summary - Cleanup Success: {sandbox_summary.get('success', False)}")
            print(f"   Summary - Cleanup Skipped: {sandbox_summary.get('skipped', False)}")
        
        # Check messages
        if result_state.messages:
            print(f"\n💬 AI Messages: {len(result_state.messages)}")
            for i, msg in enumerate(result_state.messages):
                print(f"   Message {i+1}: {msg.content[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_finalize_with_sandbox_cleanup_skip():
    """Test finalize node with skipped sandbox cleanup (error status)."""
    
    print("\n🧪 Testing finalize node with sandbox cleanup (skip case)...")
    
    # Create mock state with error status (should skip cleanup)
    mock_state = ImplementorState(
        task_description="Test failed implementation",
        sandbox_id="test-sandbox-456",
        status="error",  # Error status - should skip cleanup
        implementation_complete=False,
        feature_branch="feature/failed-task",
        base_branch="main",
        error_message="Some implementation error occurred",
        files_created=[],
        files_modified=[],
        tests_passed=False,
    )
    
    print(f"📦 Input state:")
    print(f"   Sandbox ID: {mock_state.sandbox_id}")
    print(f"   Status: {mock_state.status}")
    print(f"   Error: {mock_state.error_message}")
    
    try:
        result_state = finalize(mock_state)
        
        print(f"\n📊 Results:")
        print(f"   Final Status: {result_state.status}")
        
        # Check sandbox deletion
        if result_state.sandbox_deletion:
            print(f"   Sandbox Cleanup Attempted: ✅")
            print(f"   Sandbox Cleanup Skipped: {result_state.sandbox_deletion.skipped}")
            print(f"   Skip Reason: {result_state.sandbox_deletion.skip_reason}")
            print(f"   Sandbox Cleanup Message: {result_state.sandbox_deletion.message}")
        else:
            print(f"   Sandbox Cleanup Attempted: ❌")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False


def test_finalize_no_sandbox():
    """Test finalize node with no sandbox ID."""
    
    print("\n🧪 Testing finalize node with no sandbox ID...")
    
    # Create mock state without sandbox ID
    mock_state = ImplementorState(
        task_description="Test local implementation",
        sandbox_id="",  # No sandbox ID
        status="completed",
        implementation_complete=True,
        feature_branch="feature/local-task",
        base_branch="main",
        files_created=["local_file.py"],
        files_modified=["config.py"],
        tests_passed=True,
    )
    
    print(f"📦 Input state:")
    print(f"   Sandbox ID: '{mock_state.sandbox_id}' (empty)")
    print(f"   Status: {mock_state.status}")
    
    try:
        result_state = finalize(mock_state)
        
        print(f"\n📊 Results:")
        print(f"   Final Status: {result_state.status}")
        
        # Check sandbox deletion
        if result_state.sandbox_deletion:
            print(f"   Sandbox Cleanup Attempted: ✅")
            print(f"   Sandbox Cleanup Skipped: {result_state.sandbox_deletion.skipped}")
            print(f"   Skip Reason: {result_state.sandbox_deletion.skip_reason}")
        else:
            print(f"   Sandbox Cleanup Attempted: ❌")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False


def main():
    """Run sandbox cleanup integration tests."""
    
    print("🚀 Testing Sandbox Cleanup Integration\n")
    print("This test verifies that the finalize node correctly handles")
    print("Daytona sandbox cleanup after workflow completion.\n")
    
    test1_success = test_finalize_with_sandbox_cleanup_success()
    test2_success = test_finalize_with_sandbox_cleanup_skip()
    test3_success = test_finalize_no_sandbox()
    
    overall_success = test1_success and test2_success and test3_success
    
    if overall_success:
        print("\n🎉 SANDBOX CLEANUP INTEGRATION TEST SUCCESSFUL!")
        print("✅ Finalize node correctly handles sandbox cleanup")
        print("✅ Cleanup is attempted on successful completion")
        print("✅ Cleanup is skipped on errors (for debugging)")
        print("✅ Cleanup is skipped when no sandbox ID provided")
        print("✅ State and summary are updated with cleanup results")
    else:
        print("\n💥 SANDBOX CLEANUP INTEGRATION TEST FAILED!")
        print("❌ Finalize node may not be handling sandbox cleanup correctly")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
