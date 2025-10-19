"""
Test fixed incremental modification logic với content extraction
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


def test_content_extraction():
    """Test content extraction from read_file_tool output."""
    print("🧪 Testing content extraction from read_file_tool...")
    
    # Create test file
    test_content = '''class UserService:
    def create_user(self, data):
        # TODO: Implement
        pass
'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text(test_content)
        
        # Read with read_file_tool (returns formatted content)
        formatted_result = read_file_tool.invoke({
            "file_path": "test.py",
            "working_directory": temp_dir
        })
        
        print(f"📄 Formatted content from read_file_tool:")
        print(repr(formatted_result))
        
        # Extract actual content
        actual_content = _extract_actual_content(formatted_result)
        print(f"📄 Extracted actual content:")
        print(repr(actual_content))
        
        # Compare with original
        if actual_content.strip() == test_content.strip():
            print("✅ Content extraction successful!")
            return True
        else:
            print("❌ Content extraction failed!")
            print(f"Expected: {repr(test_content.strip())}")
            print(f"Got: {repr(actual_content.strip())}")
            return False


def test_fixed_incremental_workflow():
    """Test fixed incremental modification workflow."""
    print("\n🧪 Testing fixed incremental modification workflow...")
    
    # Create test file with standalone pass
    test_content = '''class UserService:
    """User service for authentication."""
    
    def create_user(self, user_data):
        """Create a new user."""
        # TODO: Implement user creation
        pass
'''
    
    new_implementation = '''# Validate user data
        if not user_data.get('email'):
            raise ValueError("Email is required")
        
        # Create user instance
        user = User(**user_data)
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
        
        print(f"📖 File read successfully: {len(formatted_result)} chars")
        
        # Step 2: Find insertion point
        insertion_point = _find_best_insertion_point(formatted_result)
        
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
            
            print(f"🔄 Replacement:")
            print(f"OLD: '{old_str}'")
            print(f"NEW: '{indented_content}'")
            
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


def main():
    """Run fixed workflow tests."""
    print("🚀 Testing Fixed Incremental Modification Logic...\n")
    
    success1 = test_content_extraction()
    success2 = test_fixed_incremental_workflow()
    
    print("\n🏁 Tests Completed!")
    print(f"   Content extraction: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"   Fixed workflow: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    overall_success = success1 and success2
    print(f"   Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print("\n🎉 Fixed incremental modification logic works perfectly!")
        print("✅ Ready to test with real Implementor Agent workflow")
    else:
        print("\n💥 Some tests failed - check logic")


if __name__ == "__main__":
    main()
