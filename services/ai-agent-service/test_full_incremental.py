"""
Test full incremental modification workflow với improved logic
"""

import sys
import json
import tempfile
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import tools directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "filesystem_tools", 
    "app/agents/developer/implementor/tool/filesystem_tools.py"
)
filesystem_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filesystem_tools)

write_file_tool = filesystem_tools.write_file_tool
edit_file_tool = filesystem_tools.edit_file_tool
read_file_tool = filesystem_tools.read_file_tool


def _find_best_insertion_point(content: str) -> dict | None:
    """Copy of improved insertion point logic."""
    lines = content.split('\n')
    
    insertion_patterns = [
        {"pattern": "pass", "type": "pass"},
        {"pattern": "# TODO: Implement", "type": "todo_implement"},
        {"pattern": "# TODO", "type": "todo"},
        {"pattern": "...", "type": "ellipsis"},
        {"pattern": "# Add implementation here", "type": "add_implementation"},
        {"pattern": "# Implementation goes here", "type": "implementation_here"},
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        for pattern_info in insertion_patterns:
            pattern = pattern_info["pattern"]
            
            if pattern == "pass":
                if stripped == "pass" or (stripped.startswith("pass ") and "#" in stripped):
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern
                    }
            elif pattern == "...":
                if stripped == "..." or stripped.startswith("... "):
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern
                    }
            else:
                if pattern in stripped:
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern
                    }
    
    return None


def test_full_incremental_workflow():
    """Test full incremental modification workflow."""
    print("🧪 Testing full incremental modification workflow...")
    
    # Create test file with standalone pass
    test_content = '''class UserService:
    """User service for authentication."""
    
    def __init__(self, db):
        self.db = db
    
    def create_user(self, user_data):
        """Create a new user."""
        # TODO: Implement user creation
        pass
    
    def authenticate_user(self, email, password):
        """Authenticate user credentials."""
        pass  # TODO: Implement authentication
    
    def get_user_by_email(self, email):
        """Get user by email address."""
        # Add implementation here
        return None
'''
    
    new_implementation = '''# Validate user data
        if not user_data.get('email'):
            raise ValueError("Email is required")
        
        # Create user instance
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        
        return user'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = Path(temp_dir) / "user_service.py"
        test_file.write_text(test_content)
        
        print(f"📄 Created test file: {test_file}")
        
        # Step 1: Read file content
        read_result = read_file_tool.invoke({
            "file_path": "user_service.py",
            "working_directory": temp_dir
        })
        
        print(f"📖 File read successfully: {len(read_result)} chars")
        
        # Step 2: Find insertion point
        insertion_point = _find_best_insertion_point(read_result)
        
        if insertion_point:
            print(f"🎯 Found insertion point: '{insertion_point['type']}' at line {insertion_point['line']}")
            print(f"📝 Original line: '{insertion_point['original_line']}'")
            print(f"📏 Indentation: {insertion_point['indentation']} spaces")
            
            # Step 3: Prepare replacement with proper indentation
            old_str = insertion_point['original_line']
            
            # Preserve indentation
            indentation = " " * insertion_point['indentation']
            new_content_lines = new_implementation.split('\n')
            indented_content = '\n'.join([
                indentation + line if i > 0 and line.strip() else line
                for i, line in enumerate(new_content_lines)
            ])
            
            print(f"🔄 Replacement content:")
            print(f"OLD: '{old_str}'")
            print(f"NEW: '{indented_content[:100]}...'")
            
            # Step 4: Apply edit
            result = edit_file_tool.invoke({
                "file_path": "user_service.py",
                "old_str": old_str,
                "new_str": indented_content,
                "working_directory": temp_dir
            })
            
            print(f"✏️ Edit result: {result}")
            
            # Step 5: Verify result
            try:
                result_data = json.loads(result)
                if result_data.get("status") == "success":
                    print("✅ Edit successful!")
                    
                    # Read modified file
                    modified_content = test_file.read_text()
                    print(f"📄 Modified file preview:")
                    print(modified_content[:500] + "..." if len(modified_content) > 500 else modified_content)
                    
                    return True
                else:
                    print(f"❌ Edit failed: {result_data.get('message')}")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                return False
        else:
            print("❌ No insertion point found")
            return False


def test_problematic_file():
    """Test với file có substring 'pass' nhưng không có standalone pass."""
    print("\n🧪 Testing problematic file (substring 'pass' but no standalone)...")
    
    # File content tương tự như user.py và schemas/user.py
    problematic_content = '''class UserCreate(BaseModel):
    """Schema for user creation."""
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    def validate_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self
'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = Path(temp_dir) / "user_schema.py"
        test_file.write_text(problematic_content)
        
        # Read file content
        read_result = read_file_tool.invoke({
            "file_path": "user_schema.py",
            "working_directory": temp_dir
        })
        
        # Find insertion point
        insertion_point = _find_best_insertion_point(read_result)
        
        if insertion_point:
            print(f"❌ Found insertion point: {insertion_point} (should be None)")
            return False
        else:
            print("✅ No insertion point found (correct - should fallback to append)")
            
            # Test fallback mechanism (append to end)
            new_content = read_result + "\n\n# NEW IMPLEMENTATION ADDED"
            
            result = write_file_tool.invoke({
                "file_path": "user_schema.py",
                "content": new_content,
                "working_directory": temp_dir
            })
            
            print(f"📝 Append result: {result}")
            
            try:
                result_data = json.loads(result)
                if result_data.get("status") == "success":
                    print("✅ Fallback append successful!")
                    return True
                else:
                    print(f"❌ Append failed: {result_data.get('message')}")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                return False


def main():
    """Run full workflow tests."""
    print("🚀 Testing Full Incremental Modification Workflow...\n")
    
    success1 = test_full_incremental_workflow()
    success2 = test_problematic_file()
    
    print("\n🏁 Tests Completed!")
    print(f"   Full workflow: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"   Problematic file: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    overall_success = success1 and success2
    print(f"   Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print("\n🎉 Improved incremental modification logic works perfectly!")
        print("✅ Ready to fix the Implementor Agent workflow")
    else:
        print("\n💥 Some tests failed - check logic")


if __name__ == "__main__":
    main()
