"""
Test Implementor Agent

Test file để verify Implementor Agent functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.agents.developer.implementor.agent import ImplementorAgent


def test_implementor_basic():
    """Test basic implementor functionality với mock implementation plan."""
    
    print("🧪 Testing Implementor Agent...")
    
    # Create implementor agent
    implementor = ImplementorAgent(
        model="gpt-4o",
        session_id="test_session",
        user_id="test_user"
    )
    
    # Mock implementation plan từ Planner Agent
    mock_implementation_plan = {
        "task_id": "test-task-001",
        "description": "Create a simple FastAPI endpoint",
        "tech_stack": "fastapi",
        "files_to_create": [
            {
                "file_path": "app/main.py",
                "content": '''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
''',
                "description": "Main FastAPI application file"
            },
            {
                "file_path": "requirements.txt",
                "content": '''fastapi==0.104.1
uvicorn==0.24.0
''',
                "description": "Python dependencies"
            }
        ],
        "files_to_modify": [
            {
                "file_path": "README.md",
                "content": "# FastAPI Test Application\n\nA simple FastAPI application for testing.",
                "change_type": "full_file",
                "description": "Update README with project description"
            }
        ]
    }
    
    # Test parameters
    test_params = {
        "implementation_plan": mock_implementation_plan,
        "task_description": "Create a simple FastAPI endpoint for testing",
        "codebase_path": "./test_implementation",  # Local test directory
        "thread_id": "test_thread_001"
    }
    
    print(f"📋 Test Parameters:")
    print(f"   Task: {test_params['task_description']}")
    print(f"   Files to create: {len(mock_implementation_plan['files_to_create'])}")
    print(f"   Files to modify: {len(mock_implementation_plan['files_to_modify'])}")
    print(f"   Codebase path: {test_params['codebase_path']}")
    
    try:
        # Run implementor
        result = implementor.run(**test_params)
        
        print(f"\n📊 Test Results:")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Implementation Complete: {result.get('implementation_complete', False)}")
        print(f"   Feature Branch: {result.get('feature_branch', 'N/A')}")
        print(f"   Files Created: {len(result.get('files_created', []))}")
        print(f"   Files Modified: {len(result.get('files_modified', []))}")
        print(f"   Tests Passed: {result.get('tests_passed', False)}")
        print(f"   Error: {result.get('error_message', 'None')}")
        
        # Print summary if available
        summary = result.get('summary', {})
        if summary:
            print(f"\n📈 Summary:")
            print(f"   Implementation Type: {summary.get('implementation_type', 'N/A')}")
            print(f"   Tech Stack: {summary.get('tech_stack', 'N/A')}")
            print(f"   Git Operations: {summary.get('git_operations', 0)}")
            print(f"   Tools Used: {', '.join(summary.get('tools_used', []))}")
        
        # Print messages
        messages = result.get('messages', [])
        if messages:
            print(f"\n💬 Messages ({len(messages)}):")
            for i, msg in enumerate(messages[-3:], 1):  # Show last 3 messages
                print(f"   {i}. {msg[:100]}{'...' if len(msg) > 100 else ''}")
        
        if result.get('status') == 'completed':
            print("\n✅ Test PASSED - Implementor completed successfully!")
        elif result.get('status') == 'error':
            print(f"\n❌ Test FAILED - Error: {result.get('error_message')}")
        else:
            print(f"\n⚠️  Test PARTIAL - Status: {result.get('status')}")
            
        return result
        
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_implementor_new_project():
    """Test implementor với new project scenario."""
    
    print("\n🧪 Testing New Project Scenario...")
    
    implementor = ImplementorAgent(model="gpt-4o")
    
    # Mock plan for new FastAPI project
    new_project_plan = {
        "task_id": "new-project-001",
        "description": "Initialize new FastAPI project with authentication",
        "tech_stack": "fastapi",
        "files_to_create": [
            {
                "file_path": "app/auth.py",
                "content": '''from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

def verify_token(token: str = Depends(security)):
    if token.credentials != "valid-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return token
''',
                "description": "Authentication module"
            }
        ],
        "files_to_modify": []
    }
    
    result = implementor.run(
        implementation_plan=new_project_plan,
        task_description="Initialize new FastAPI project with authentication",
        codebase_path="./test_new_project",
        thread_id="new_project_test"
    )
    
    print(f"New Project Test Result: {result.get('status', 'unknown')}")
    return result


def main():
    """Run all tests."""
    print("🚀 Starting Implementor Agent Tests...\n")
    
    # Test 1: Basic functionality
    result1 = test_implementor_basic()
    
    # Test 2: New project scenario
    result2 = test_implementor_new_project()
    
    print(f"\n🏁 All Tests Completed!")
    print(f"   Test 1 (Basic): {'✅ PASSED' if result1 and result1.get('status') != 'error' else '❌ FAILED'}")
    print(f"   Test 2 (New Project): {'✅ PASSED' if result2 and result2.get('status') != 'error' else '❌ FAILED'}")


if __name__ == "__main__":
    main()
