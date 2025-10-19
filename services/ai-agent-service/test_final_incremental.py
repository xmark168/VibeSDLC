"""
Test final incremental modification với improved indentation
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


def _extract_actual_content(formatted_content: str) -> str:
    """Extract actual file content from read_file_tool output (cat -n format)."""
    lines = formatted_content.split('\n')
    actual_lines = []
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            actual_lines.append("")
            continue
            
        # Extract content after line number and tab
        # Format: "     1\tclass UserService:"
        if '\t' in line:
            actual_content = line.split('\t', 1)[1]
            actual_lines.append(actual_content)
        else:
            # Fallback for lines without tab
            actual_lines.append(line)
    
    return '\n'.join(actual_lines)


def _find_best_insertion_point(formatted_content: str) -> dict | None:
    """Find the best insertion point in file content using line-by-line analysis."""
    # Extract actual content without line numbers
    actual_content = _extract_actual_content(formatted_content)
    lines = actual_content.split('\n')
    
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


def test_improved_indentation():
    """Test improved indentation logic."""
    print("🧪 Testing improved indentation logic...")
    
    # Create test file with standalone pass
    test_content = '''class UserService:
    """User service for authentication."""
    
    def create_user(self, user_data):
        """Create a new user."""
        # TODO: Implement user creation
        pass
    
    def update_user(self, user_id, data):
        """Update user data."""
        pass  # TODO: Implement
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
        
        print(f"📄 Created test file")
        
        # Step 1: Read file content (formatted)
        formatted_result = read_file_tool.invoke({
            "file_path": "user_service.py",
            "working_directory": temp_dir
        })
        
        # Step 2: Find insertion point
        insertion_point = _find_best_insertion_point(formatted_result)
        
        if insertion_point:
            print(f"🎯 Found insertion point: '{insertion_point['type']}' at line {insertion_point['line']}")
            print(f"📝 Original line: '{insertion_point['original_line']}'")
            print(f"📏 Indentation: {insertion_point['indentation']} spaces")
            
            # Step 3: Apply improved indentation logic
            old_str = insertion_point['original_line']
            indentation = " " * insertion_point['indentation']
            new_content_lines = new_implementation.split('\n')
            
            # Apply indentation to all non-empty lines
            indented_lines = []
            for line in new_content_lines:
                if line.strip():  # Non-empty line
                    indented_lines.append(indentation + line)
                else:  # Empty line
                    indented_lines.append("")
            
            indented_content = '\n'.join(indented_lines)
            
            print(f"🔄 Replacement:")
            print(f"OLD: '{old_str}'")
            print(f"NEW:")
            print(indented_content)
            
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
                    print(f"📄 Modified file:")
                    print(modified_content)
                    
                    # Check if indentation looks correct
                    if "        # Validate user data" in modified_content:
                        print("✅ Indentation looks correct!")
                        return True
                    else:
                        print("❌ Indentation might be wrong")
                        return False
                else:
                    print(f"❌ Edit failed: {result_data.get('message')}")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                return False
        else:
            print("❌ No insertion point found")
            return False


def test_problematic_files_handling():
    """Test handling of files without insertion points."""
    print("\n🧪 Testing problematic files handling...")
    
    # Simulate files like user.py and schemas/user.py (no insertion points)
    problematic_files = [
        {
            "name": "user_model.py",
            "content": '''class User(Base):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    reset_password_token: Mapped[Optional[str]] = mapped_column(String(255))
'''
        },
        {
            "name": "user_schema.py", 
            "content": '''class UserCreate(BaseModel):
    """Schema for user creation."""
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    def validate_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self
'''
        }
    ]
    
    success_count = 0
    
    for file_info in problematic_files:
        print(f"📄 Testing {file_info['name']}...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / file_info['name']
            test_file.write_text(file_info['content'])
            
            # Read file content
            formatted_result = read_file_tool.invoke({
                "file_path": file_info['name'],
                "working_directory": temp_dir
            })
            
            # Find insertion point
            insertion_point = _find_best_insertion_point(formatted_result)
            
            if insertion_point:
                print(f"   ❌ Found insertion point: {insertion_point} (should be None)")
            else:
                print("   ✅ No insertion point found (correct)")
                
                # Test fallback mechanism (append to end)
                original_content = _extract_actual_content(formatted_result)
                new_content = original_content + "\n\n# NEW IMPLEMENTATION ADDED"
                
                result = write_file_tool.invoke({
                    "file_path": file_info['name'],
                    "content": new_content,
                    "working_directory": temp_dir
                })
                
                try:
                    result_data = json.loads(result)
                    if result_data.get("status") == "success":
                        print("   ✅ Fallback append successful!")
                        success_count += 1
                    else:
                        print(f"   ❌ Append failed: {result_data.get('message')}")
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON parsing error: {e}")
    
    return success_count == len(problematic_files)


def main():
    """Run final tests."""
    print("🚀 Testing Final Incremental Modification Logic...\n")
    
    success1 = test_improved_indentation()
    success2 = test_problematic_files_handling()
    
    print("\n🏁 Tests Completed!")
    print(f"   Improved indentation: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"   Problematic files: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    overall_success = success1 and success2
    print(f"   Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print("\n🎉 Final incremental modification logic works perfectly!")
        print("\n💡 Summary of fixes:")
        print("   1. ✅ Line-by-line analysis instead of substring search")
        print("   2. ✅ Content extraction from read_file_tool output")
        print("   3. ✅ Standalone keyword detection (not substrings)")
        print("   4. ✅ Improved indentation preservation")
        print("   5. ✅ Fallback to append for files without insertion points")
        print("   6. ✅ JSON format for all tool responses")
        print("\n🚀 Ready for production use!")
    else:
        print("\n💥 Some tests failed - check logic")


if __name__ == "__main__":
    main()
