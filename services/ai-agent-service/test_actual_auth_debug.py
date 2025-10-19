"""
Debug actual auth.py file modification
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.developer.implementor.tool.filesystem_tools import read_file_tool, edit_file_tool


def _extract_actual_content(formatted_content: str) -> str:
    """Extract actual content from read_file_tool output."""
    lines = formatted_content.split("\n")
    actual_lines = []

    for line in lines:
        if not line.strip():
            actual_lines.append("")
            continue

        if "\t" in line:
            actual_content = line.split("\t", 1)[1]
            actual_lines.append(actual_content)
        else:
            actual_lines.append(line)

    return "\n".join(actual_lines)


def _find_best_insertion_point(formatted_content: str) -> dict | None:
    """Find insertion point in actual auth.py content."""
    actual_content = _extract_actual_content(formatted_content)
    lines = actual_content.split("\n")

    insertion_patterns = [
        {"pattern": "pass", "type": "pass"},
        {"pattern": "# TODO: Implement", "type": "todo_implement"},
        {"pattern": "# TODO", "type": "todo"},
        {"pattern": "...", "type": "ellipsis"},
    ]

    for i, line in enumerate(lines):
        stripped = line.strip()

        for pattern_info in insertion_patterns:
            pattern = pattern_info["pattern"]
            
            if pattern == "pass":
                # Check if line is exactly "pass" (standalone)
                if stripped == "pass" or (
                    stripped.startswith("pass ") and "#" in stripped
                ):
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern,
                    }

    return None


def test_actual_auth_file():
    """Test modification of actual auth.py file."""
    print("🧪 Testing actual auth.py file modification...")
    
    working_dir = "app/agents/demo"
    file_path = "app/services/auth.py"
    
    # Step 1: Read actual file
    try:
        read_result = read_file_tool.invoke({
            "file_path": file_path,
            "working_directory": working_dir
        })
        
        print(f"📖 Read file result type: {type(read_result)}")
        print(f"📖 Read file result length: {len(read_result) if read_result else 0}")
        
        if "File not found" in read_result or "Error:" in read_result:
            print(f"❌ File read error: {read_result}")
            return False
            
        print("📖 First 10 lines of read result:")
        for i, line in enumerate(read_result.split("\\n")[:10]):
            print(f"    {i+1:2d}: {line}")
        print("    ...")
        
    except Exception as e:
        print(f"❌ Exception reading file: {e}")
        return False
    
    # Step 2: Find insertion point
    try:
        insertion_point = _find_best_insertion_point(read_result)
        
        if insertion_point:
            print(f"🎯 Found insertion point: {insertion_point['type']} at line {insertion_point['line']}")
            print(f"    Original line: '{insertion_point['original_line']}'")
            print(f"    Indentation: {insertion_point['indentation']} spaces")
            print(f"    Pattern: '{insertion_point['pattern']}'")
        else:
            print("❌ No insertion point found")
            return False
            
    except Exception as e:
        print(f"❌ Exception finding insertion point: {e}")
        return False
    
    # Step 3: Check if original_line exists in actual content
    try:
        actual_content = _extract_actual_content(read_result)
        old_str = insertion_point["original_line"]
        
        print(f"\\n🔍 Checking old_str in actual content...")
        print(f"    old_str: '{old_str}'")
        print(f"    old_str length: {len(old_str)}")
        print(f"    old_str repr: {repr(old_str)}")
        
        # Count occurrences
        count = actual_content.count(old_str)
        print(f"    Occurrences in actual content: {count}")
        
        if count == 0:
            print("    ❌ old_str not found in actual content!")
            
            # Try to find similar lines
            lines = actual_content.split("\\n")
            for i, line in enumerate(lines):
                if "pass" in line:
                    print(f"    Line {i+1}: '{line}' (repr: {repr(line)})")
                    
        elif count > 1:
            print("    ⚠️ Multiple occurrences found!")
            
            # Show all occurrences
            lines = actual_content.split("\\n")
            for i, line in enumerate(lines):
                if line == old_str:
                    print(f"    Match at line {i+1}: '{line}'")
        else:
            print("    ✅ Exactly one occurrence found")
            
    except Exception as e:
        print(f"❌ Exception checking old_str: {e}")
        return False
    
    # Step 4: Test edit_file_tool with simple content
    try:
        print(f"\\n🔧 Testing edit_file_tool...")
        
        # Generate simple test content
        test_content = "# Email verification implementation\\n        # TODO: Add token blacklist logic"
        
        # Apply indentation
        indentation = " " * insertion_point["indentation"]
        content_lines = test_content.split("\\n")
        
        indented_lines = []
        for line in content_lines:
            if line.strip():  # Non-empty line
                indented_lines.append(indentation + line)
            else:  # Empty line
                indented_lines.append("")
        
        indented_content = "\\n".join(indented_lines)
        
        print(f"    Test content: {repr(test_content)}")
        print(f"    Indented content: {repr(indented_content)}")
        
        # Call edit_file_tool
        edit_result = edit_file_tool.invoke({
            "file_path": file_path,
            "old_str": old_str,
            "new_str": indented_content,
            "working_directory": working_dir
        })
        
        print(f"    Edit result: {edit_result}")
        print(f"    Edit result type: {type(edit_result)}")
        
        # Parse result
        try:
            if isinstance(edit_result, str):
                result_data = json.loads(edit_result)
            else:
                result_data = edit_result
                
            status = result_data.get("status")
            message = result_data.get("message")
            
            print(f"    Status: {status}")
            print(f"    Message: {message}")
            
            if status == "success":
                print("    ✅ Edit successful!")
                return True
            else:
                print(f"    ❌ Edit failed: {message}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"    ❌ JSON decode error: {e}")
            print(f"    Raw result: {edit_result}")
            return False
            
    except Exception as e:
        print(f"❌ Exception testing edit_file_tool: {e}")
        return False


def main():
    """Run actual auth.py debug test."""
    print("🚀 Debugging actual auth.py modification failure...\\n")
    
    success = test_actual_auth_file()
    
    if success:
        print("\\n🎉 Debug test successful!")
        print("\\n💡 auth.py modification should work correctly")
    else:
        print("\\n💥 Debug test failed - found the root cause!")
        print("\\n🔧 Potential fixes:")
        print("  1. Check file path and working directory")
        print("  2. Verify insertion point detection logic")
        print("  3. Handle whitespace and indentation issues")
        print("  4. Improve error handling in edit_file_tool")


if __name__ == "__main__":
    main()
