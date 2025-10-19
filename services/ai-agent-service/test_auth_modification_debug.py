"""
Debug auth.py modification failure
"""

import json
import tempfile
from pathlib import Path

# Simulate the filesystem tools
def read_file_tool_invoke(params):
    """Simulate read_file_tool.invoke()"""
    file_path = params["file_path"]
    working_dir = params["working_directory"]
    
    full_path = Path(working_dir) / file_path
    
    if not full_path.exists():
        return "File not found"
    
    # Read and format with line numbers (cat -n format)
    content = full_path.read_text()
    lines = content.split("\n")
    formatted_lines = []
    
    for i, line in enumerate(lines, 1):
        formatted_lines.append(f"{i:6d}\t{line}")
    
    return "\n".join(formatted_lines)


def edit_file_tool_invoke(params):
    """Simulate edit_file_tool.invoke()"""
    file_path = params["file_path"]
    working_dir = params["working_directory"]
    old_str = params["old_str"]
    new_str = params["new_str"]
    
    full_path = Path(working_dir) / file_path
    
    if not full_path.exists():
        return json.dumps({"status": "error", "message": "File not found"})
    
    content = full_path.read_text()
    
    # Check if old_str exists
    if old_str not in content:
        return json.dumps({"status": "error", "message": f"String not found: {old_str[:50]}..."})
    
    # Count occurrences
    count = content.count(old_str)
    if count > 1:
        return json.dumps({"status": "error", "message": f"Multiple occurrences found: {count}"})
    
    # Replace
    new_content = content.replace(old_str, new_str)
    full_path.write_text(new_content)
    
    return json.dumps({"status": "success", "message": "File updated successfully"})


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
    """Find insertion point in auth.py content."""
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
                if stripped == pattern:
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern,
                    }

    return None


def test_auth_modification():
    """Test auth.py modification with realistic content."""
    print("🧪 Testing auth.py modification failure...")
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Create auth.py with the problematic content
        auth_content = '''"""
Authentication service for user login, token management, and security.
"""

from datetime import datetime, timedelta
from typing import Optional

class AuthService:
    """Authentication service for user management and JWT tokens."""

    def __init__(self, db):
        self.db = db

    async def logout_user(self, token: str) -> None:
        """Logout user (token invalidation would be implemented with Redis/cache)."""
        # In a production app, you would add the token to a blacklist
        # stored in Redis or similar cache system
        pass

# Dependency to get current user
async def get_current_user(token: str):
    """FastAPI dependency to get current authenticated user."""
    auth_service = AuthService(db)
    return await auth_service.get_current_user(token.credentials)
'''
        
        auth_file = temp_dir / "auth.py"
        auth_file.write_text(auth_content)
        
        print(f"📄 Created test auth.py with {len(auth_content.split('\\n'))} lines")
        
        # Step 1: Read file content (simulate read_file_tool)
        read_result = read_file_tool_invoke({
            "file_path": "auth.py",
            "working_directory": str(temp_dir)
        })
        
        print("📖 Read file content (first 5 lines):")
        for line in read_result.split("\\n")[:5]:
            print(f"    {line}")
        print("    ...")
        
        # Step 2: Find insertion point
        insertion_point = _find_best_insertion_point(read_result)
        
        if insertion_point:
            print(f"🎯 Found insertion point: {insertion_point['type']} at line {insertion_point['line']}")
            print(f"    Original line: '{insertion_point['original_line']}'")
            print(f"    Indentation: {insertion_point['indentation']} spaces")
        else:
            print("❌ No insertion point found")
            return False
        
        # Step 3: Simulate problematic content that might cause failure
        test_cases = [
            {
                "name": "Normal content",
                "content": "# Token blacklist implementation\\n    token_blacklist.add(token)"
            },
            {
                "name": "Content with line numbers (corrupted)",
                "content": "   123\\t# Token blacklist implementation\\n   124\\t    token_blacklist.add(token)"
            },
            {
                "name": "Content with wrong indentation",
                "content": "# Token blacklist implementation\\ntoken_blacklist.add(token)"  # No indentation
            },
            {
                "name": "Empty content",
                "content": ""
            },
            {
                "name": "Very long content",
                "content": "\\n".join([f"    # Line {i}" for i in range(100)])
            }
        ]
        
        for test_case in test_cases:
            print(f"\\n🧪 Testing: {test_case['name']}")
            
            # Reset file
            auth_file.write_text(auth_content)
            
            # Apply indentation to content
            indentation = " " * insertion_point["indentation"]
            content_lines = test_case["content"].split("\\n")
            
            indented_lines = []
            for line in content_lines:
                if line.strip():  # Non-empty line
                    indented_lines.append(indentation + line)
                else:  # Empty line
                    indented_lines.append("")
            
            indented_content = "\\n".join(indented_lines)
            
            # Try to edit file
            result = edit_file_tool_invoke({
                "file_path": "auth.py",
                "old_str": insertion_point["original_line"],
                "new_str": indented_content,
                "working_directory": str(temp_dir)
            })
            
            print(f"    📝 Edit result: {result}")
            
            # Check if successful
            try:
                result_data = json.loads(result)
                success = result_data.get("status") == "success"
                print(f"    {'✅' if success else '❌'} Status: {result_data.get('status')}")
                if not success:
                    print(f"    💥 Error: {result_data.get('message')}")
            except json.JSONDecodeError as e:
                print(f"    💥 JSON decode error: {e}")
                success = False
            
            # Check file content after edit
            if success:
                new_content = auth_file.read_text()
                print(f"    📄 File size after edit: {len(new_content)} chars")
                
                # Check for corruption
                if "\\t" in new_content and any(line.split("\\t")[0].strip().isdigit() 
                                               for line in new_content.split("\\n") if "\\t" in line):
                    print("    ⚠️ WARNING: File contains line numbers (corruption detected)")
        
        return True


def main():
    """Run auth.py modification debug test."""
    print("🚀 Debugging auth.py modification failure...\\n")
    
    success = test_auth_modification()
    
    if success:
        print("\\n🎉 Debug test completed!")
        print("\\n💡 Potential causes of auth.py modification failure:")
        print("  1. Content with line numbers (corruption from LLM)")
        print("  2. Wrong indentation in generated content")
        print("  3. Empty or malformed content")
        print("  4. JSON parsing errors in tool responses")
        print("  5. Multiple 'pass' statements causing ambiguity")
        print("\\n🔧 Recommended fixes:")
        print("  1. Ensure generated content is clean (no line numbers)")
        print("  2. Proper indentation handling in _apply_incremental_change()")
        print("  3. Better error handling and logging")
        print("  4. Fallback to append-to-end if insertion point fails")
    else:
        print("\\n💥 Debug test failed")


if __name__ == "__main__":
    main()
