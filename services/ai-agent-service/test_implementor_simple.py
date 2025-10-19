"""
Simple test for Implementor Agent with generate_code workflow.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.developer.implementor.agent import ImplementorAgent


def test_implementor_simple():
    """Test implementor với simple plan."""
    
    print("\n🧪 Testing Implementor with Generate Code...")
    
    # Create test directory structure
    test_dir = r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
        print(f"📁 Created test directory: {test_dir}")
    
    # Initialize git repo if needed
    if not os.path.exists(os.path.join(test_dir, ".git")):
        import subprocess
        try:
            subprocess.run(["git", "init"], cwd=test_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_dir, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_dir, check=True)
            print(f"🔧 Initialized git repo in {test_dir}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Git init failed: {e}")

    implementor = ImplementorAgent(model="gpt-4o")

    # Simple test plan - correct format for Implementor
    simple_plan = {
        "task_id": "TSK-TEST-001",
        "description": "Test code generation workflow",
        "files_to_create": [
            {
                "file_path": "test_service.py",
                "description": "Simple test service file",
            },
        ],
        "files_to_modify": [
            {
                "file_path": "existing_file.py",
                "description": "Modify existing file",
                "change_type": "incremental",
            },
        ],
    }

    print(f"📋 Test Plan:")
    print(f"   Task ID: {simple_plan['task_id']}")
    print(f"   Files to Create: {len(simple_plan['files_to_create'])}")
    print(f"   Files to Modify: {len(simple_plan['files_to_modify'])}")

    result = implementor.run(
        implementation_plan=simple_plan,
        task_description="Test generate_code workflow",
        codebase_path=test_dir,
        thread_id="simple_test",
    )

    print(f"\n📊 Test Result: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'error':
        print(f"❌ Error: {result.get('error_message', 'Unknown error')}")
    else:
        print(f"✅ Success!")
        
    return result


def main():
    """Run simple test."""
    print("🚀 Starting Simple Implementor Test...\n")
    
    result = test_implementor_simple()
    
    print("\n🏁 Test Completed!")
    print(f"   Result: {'✅ PASSED' if result and result.get('status') != 'error' else '❌ FAILED'}")


if __name__ == "__main__":
    main()
