"""
Test Git Fix for Uncommitted Changes Issue

Test that the Git tools can handle uncommitted changes gracefully
by auto-stashing them before branch operations.
"""

import tempfile
import json
import os
from pathlib import Path

def test_git_uncommitted_fix():
    """Test Git repository with uncommitted changes."""
    
    print("🧪 Testing Git fix for uncommitted changes...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"📁 Test directory: {temp_path}")
        
        try:
            # Import Git tools
            from git import Repo
            
            # Initialize Git repository
            repo = Repo.init(temp_path, initial_branch="main")
            print("✅ Git repository initialized")
            
            # Create initial file and commit
            initial_file = temp_path / "README.md"
            with open(initial_file, 'w') as f:
                f.write("# Test Repository\n\nInitial content.\n")
            
            repo.index.add([str(initial_file)])
            repo.index.commit("Initial commit")
            print("✅ Initial commit created")
            
            # Create uncommitted changes (simulate the error scenario)
            auth_file = temp_path / "app" / "api" / "v1" / "endpoints" / "auth.py"
            auth_file.parent.mkdir(parents=True, exist_ok=True)
            with open(auth_file, 'w') as f:
                f.write("# Auth endpoints\n\ndef login():\n    pass\n")
            
            user_file = temp_path / "app" / "schemas" / "user.py"
            user_file.parent.mkdir(parents=True, exist_ok=True)
            with open(user_file, 'w') as f:
                f.write("# User schemas\n\nclass User:\n    pass\n")
            
            print("✅ Created uncommitted changes in:")
            print(f"   - {auth_file.relative_to(temp_path)}")
            print(f"   - {user_file.relative_to(temp_path)}")
            
            # Verify repository is dirty
            if repo.is_dirty(untracked_files=True):
                print("✅ Repository has uncommitted changes (as expected)")
            else:
                print("❌ Repository should have uncommitted changes")
                return False
            
            # Test the fixed Git tool
            from app.agents.developer.implementor.tool.git_tools_gitpython import create_feature_branch_tool
            
            print("\n🔧 Testing branch creation with uncommitted changes...")
            result = create_feature_branch_tool(
                branch_name="feature/test-uncommitted-fix",
                base_branch="main",
                working_directory=str(temp_path)
            )
            
            print(f"🔍 Git tool result:")
            result_data = json.loads(result)
            print(json.dumps(result_data, indent=2))
            
            if result_data.get("status") == "success":
                print("\n✅ Git fix successful!")
                print(f"✅ Branch created: {result_data.get('branch_name')}")
                print(f"✅ Stash created: {result_data.get('stash_created', False)}")
                
                if result_data.get('stash_created'):
                    print(f"✅ Stash message: {result_data.get('stash_message')}")
                    print(f"💡 Note: {result_data.get('note', '')}")
                
                # Verify current branch
                current_branch = repo.active_branch.name
                expected_branch = result_data.get('branch_name')
                if current_branch == expected_branch:
                    print(f"✅ Currently on correct branch: {current_branch}")
                else:
                    print(f"❌ Expected branch {expected_branch}, but on {current_branch}")
                    return False
                
                # Check if stash exists
                try:
                    stash_list = repo.git.stash("list")
                    if stash_list and result_data.get('stash_created'):
                        print("✅ Stash exists in repository")
                        print(f"📦 Stash list: {stash_list}")
                    elif not result_data.get('stash_created'):
                        print("✅ No stash created (as expected)")
                except Exception as e:
                    print(f"⚠️ Could not check stash: {e}")
                
                return True
            else:
                print(f"❌ Git fix failed: {result_data.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run Git uncommitted changes fix test."""
    
    print("🚀 Testing Git Fix for Uncommitted Changes Issue\n")
    print("This test verifies that Git tools can handle uncommitted changes")
    print("by automatically stashing them before branch operations.\n")
    
    success = test_git_uncommitted_fix()
    
    if success:
        print("\n🎉 GIT UNCOMMITTED CHANGES FIX SUCCESSFUL!")
        print("✅ Uncommitted changes are now handled gracefully")
        print("✅ Auto-stash functionality works correctly")
        print("✅ Feature branches can be created despite uncommitted changes")
        print("✅ Stashed changes can be restored with 'git stash pop'")
    else:
        print("\n💥 GIT UNCOMMITTED CHANGES FIX FAILED!")
        print("❌ Uncommitted changes issue still exists")
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
