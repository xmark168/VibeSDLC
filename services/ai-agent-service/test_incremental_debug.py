"""
Test để debug incremental modification issue
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

read_file_tool = filesystem_tools.read_file_tool
edit_file_tool = filesystem_tools.edit_file_tool


def test_pass_substring_issue():
    """Test vấn đề substring 'pass' trong files."""
    print("🧪 Testing 'pass' substring issue...")
    
    # Test với file có substring "password"
    test_content = '''class UserCreate(BaseModel):
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
        test_file = Path(temp_dir) / "test_schema.py"
        test_file.write_text(test_content)
        
        # Read file content
        read_result = read_file_tool.invoke({
            "file_path": "test_schema.py",
            "working_directory": temp_dir
        })
        
        print(f"📄 File content preview:")
        print(read_result[:200] + "..." if len(read_result) > 200 else read_result)
        
        # Check if "pass" substring exists
        if "pass" in read_result:
            print("✅ Found 'pass' substring in file (this is the problem!)")
            
            # Try to replace "pass" - this will corrupt the file
            print("🔧 Attempting to replace 'pass' with new content...")
            result = edit_file_tool.invoke({
                "file_path": "test_schema.py",
                "old_str": "pass",
                "new_str": "# NEW IMPLEMENTATION",
                "working_directory": temp_dir
            })
            
            print(f"📝 Edit result: {result}")
            
            # Check file after edit
            corrupted_content = test_file.read_text()
            print(f"💥 File after edit:")
            print(corrupted_content[:300] + "..." if len(corrupted_content) > 300 else corrupted_content)
            
        else:
            print("❌ No 'pass' substring found")


def test_standalone_pass_detection():
    """Test logic để detect standalone 'pass' statements."""
    print("\n🧪 Testing standalone 'pass' detection...")
    
    # Test với file có standalone pass
    test_content_with_pass = '''class UserService:
    """User service class."""
    
    def create_user(self, user_data):
        # TODO: Implement user creation
        pass
    
    def update_password(self, user_id, new_password):
        # TODO: Implement password update
        pass
'''
    
    # Test với file có substring pass nhưng không có standalone pass
    test_content_no_pass = '''class UserCreate(BaseModel):
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
'''
    
    def check_standalone_pass(content):
        """Check for standalone 'pass' statements."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Check if line is exactly "pass" or "pass" followed by comment
            if stripped == "pass" or (stripped.startswith("pass ") and "#" in stripped):
                return True, i + 1, stripped
        return False, -1, ""
    
    print("📄 Testing file WITH standalone pass:")
    has_pass, line_num, line_content = check_standalone_pass(test_content_with_pass)
    print(f"   Result: {has_pass}, Line {line_num}: '{line_content}'")
    
    print("📄 Testing file WITHOUT standalone pass:")
    has_pass, line_num, line_content = check_standalone_pass(test_content_no_pass)
    print(f"   Result: {has_pass}, Line {line_num}: '{line_content}'")


def test_improved_insertion_logic():
    """Test improved insertion point detection."""
    print("\n🧪 Testing improved insertion point detection...")
    
    test_content = '''class UserService:
    """User service class."""
    
    def create_user(self, user_data):
        # TODO: Implement user creation
        pass
    
    def get_user_by_email(self, email):
        # Implementation here
        return None
        
    def update_password(self, user_id, new_password):
        pass  # TODO: Implement
'''
    
    def find_insertion_points(content):
        """Find proper insertion points."""
        lines = content.split('\n')
        insertion_points = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check for standalone pass
            if stripped == "pass" or stripped.startswith("pass "):
                insertion_points.append({
                    "type": "pass",
                    "line": i + 1,
                    "content": stripped,
                    "indentation": len(line) - len(line.lstrip())
                })
            
            # Check for TODO comments
            elif "# TODO" in stripped:
                insertion_points.append({
                    "type": "todo",
                    "line": i + 1,
                    "content": stripped,
                    "indentation": len(line) - len(line.lstrip())
                })
        
        return insertion_points
    
    points = find_insertion_points(test_content)
    print(f"📍 Found {len(points)} insertion points:")
    for point in points:
        print(f"   Line {point['line']}: {point['type']} - '{point['content']}'")


def main():
    """Run debug tests."""
    print("🚀 Debugging Incremental Modification Issues...\n")
    
    test_pass_substring_issue()
    test_standalone_pass_detection()
    test_improved_insertion_logic()
    
    print("\n🏁 Debug Tests Completed!")
    print("\n💡 Key Findings:")
    print("   1. Current logic uses substring search 'pass' in content")
    print("   2. This matches 'password', 'confirm_password', etc.")
    print("   3. edit_file_tool replaces first 'pass' substring, corrupting file")
    print("   4. Need to use line-by-line analysis for standalone 'pass' statements")


if __name__ == "__main__":
    main()
