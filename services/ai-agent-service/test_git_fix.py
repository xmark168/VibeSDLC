"""
Test Git Fix for Empty Repository Issue

Test that the Git tools can handle empty repositories correctly.
"""

import tempfile
import json
from pathlib import Path

def test_git_fix():
    """Test Git repository initialization with empty directory."""
    
    print("🧪 Testing Git fix for empty repository...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"📁 Test directory: {temp_path}")
        
        try:
            # Import the fixed Git tool
            from app.agents.developer.implementor.tool.git_tools_gitpython import create_feature_branch_tool
            
            # Test branch creation in empty directory
            result = create_feature_branch_tool(
                branch_name="feature/test-fix",
                base_branch="main",
                working_directory=str(temp_path)
            )
            
            print(f"🔍 Git tool result:")
            result_data = json.loads(result)
            print(json.dumps(result_data, indent=2))
            
            if result_data.get("status") == "success":
                print("✅ Git fix successful!")
                print(f"✅ Branch created: {result_data.get('branch_name')}")
                print(f"✅ Initial commit: {result_data.get('initial_commit_created', False)}")
                
                # Check if README.md was created
                readme_path = temp_path / "README.md"
                if readme_path.exists():
                    print("✅ README.md created for initial commit")
                    with open(readme_path, 'r') as f:
                        content = f.read()
                        print(f"📄 README content: {content[:50]}...")
                
                return True
            else:
                print(f"❌ Git fix failed: {result_data.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            return False


def main():
    """Run Git fix test."""
    
    print("🚀 Testing Git Fix for Empty Repository Issue\n")
    print("This test verifies that Git tools can handle empty directories")
    print("by automatically creating initial files for the first commit.\n")
    
    success = test_git_fix()
    
    if success:
        print("\n🎉 GIT FIX SUCCESSFUL!")
        print("✅ Empty repositories are now handled correctly")
        print("✅ Initial commit will be created with README.md")
        print("✅ Feature branches can be created from 'main'")
    else:
        print("\n💥 GIT FIX FAILED!")
        print("❌ Empty repository issue still exists")
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
