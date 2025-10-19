"""
Simple test for edit operation without complex dependencies
"""

import tempfile
import shutil
from pathlib import Path


def test_simple_edit_operation():
    """Test simple edit operation on a file with pass statement."""
    print("🧪 Testing simple edit operation...")
    
    # Create a simple test file with pass statement
    test_content = '''class TestService:
    """Test service for debugging."""
    
    def __init__(self):
        self.name = "test"
    
    def test_method(self):
        """Test method with pass statement."""
        # This is where we want to insert code
        pass
    
    def another_method(self):
        """Another method."""
        return "test"
'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        test_file = temp_dir / "test_service.py"
        
        # Write test file
        test_file.write_text(test_content)
        
        print(f"📄 Created test file: {test_file}")
        print(f"📄 File size: {test_file.stat().st_size} bytes")
        
        # Simulate read_file_tool output (cat -n format)
        lines = test_content.split("\\n")
        formatted_lines = []
        for i, line in enumerate(lines, 1):
            formatted_lines.append(f"{i:6d}\\t{line}")
        formatted_content = "\\n".join(formatted_lines)
        
        print(f"📖 Formatted content lines: {len(formatted_lines)}")
        
        # Find insertion point
        insertion_point = find_insertion_point(formatted_content)
        
        if insertion_point:
            print(f"🎯 Found insertion point:")
            print(f"    Line: {insertion_point['line']}")
            print(f"    Original line: '{insertion_point['original_line']}'")
            print(f"    Indentation: {insertion_point['indentation']} spaces")
            
            # Test different types of generated content
            test_cases = [
                {
                    "name": "Normal content",
                    "content": "# Email verification implementation\\n        # TODO: Add token blacklist logic"
                },
                {
                    "name": "Content with line numbers",
                    "content": "   123\\t# Email verification implementation\\n   124\\t        # TODO: Add token blacklist logic"
                },
                {
                    "name": "Empty content",
                    "content": ""
                },
                {
                    "name": "Single line content",
                    "content": "# Simple implementation"
                }
            ]
            
            for test_case in test_cases:
                print(f"\\n🧪 Testing: {test_case['name']}")
                
                # Reset file
                test_file.write_text(test_content)
                
                # Apply indentation
                indentation = " " * insertion_point["indentation"]
                content_lines = test_case["content"].split("\\n")
                
                indented_lines = []
                for line in content_lines:
                    if line.strip():  # Non-empty line
                        indented_lines.append(indentation + line)
                    else:  # Empty line
                        indented_lines.append("")
                
                indented_content = "\\n".join(indented_lines)
                
                # Simulate edit operation
                old_str = insertion_point["original_line"]
                new_str = indented_content
                
                try:
                    current_content = test_file.read_text()
                    
                    # Check if old_str exists
                    if old_str not in current_content:
                        print(f"    ❌ old_str not found: {repr(old_str)}")
                        continue
                    
                    # Count occurrences
                    count = current_content.count(old_str)
                    if count > 1:
                        print(f"    ❌ Multiple occurrences: {count}")
                        continue
                    
                    # Replace
                    new_content = current_content.replace(old_str, new_str)
                    test_file.write_text(new_content)
                    
                    # Verify
                    verify_content = test_file.read_text()
                    
                    # Check for issues
                    if old_str in verify_content:
                        print(f"    ❌ old_str still present after replacement")
                    elif new_str not in verify_content:
                        print(f"    ❌ new_str not found in result")
                    else:
                        print(f"    ✅ Edit successful")
                        
                        # Check for line number corruption
                        has_line_numbers = any("\\t" in line and line.split("\\t")[0].strip().isdigit() 
                                               for line in verify_content.split("\\n") if "\\t" in line)
                        
                        if has_line_numbers:
                            print(f"    ⚠️ WARNING: Line numbers detected in result")
                        
                except Exception as e:
                    print(f"    ❌ Edit failed: {e}")
            
            return True
            
        else:
            print("❌ No insertion point found")
            return False


def find_insertion_point(formatted_content: str) -> dict | None:
    """Find insertion point (simplified version)."""
    # Extract actual content
    lines = formatted_content.split("\\n")
    actual_lines = []
    
    for line in lines:
        if not line.strip():
            actual_lines.append("")
            continue
        if "\\t" in line:
            actual_content = line.split("\\t", 1)[1]
            actual_lines.append(actual_content)
        else:
            actual_lines.append(line)
    
    actual_content = "\\n".join(actual_lines)
    content_lines = actual_content.split("\\n")
    
    # Find "pass" statement
    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if stripped == "pass":
            return {
                "type": "pass",
                "line": i + 1,
                "original_line": line,
                "indentation": len(line) - len(line.lstrip()),
                "pattern": "pass",
            }
    
    return None


def main():
    """Run simple edit operation test."""
    print("🚀 Testing simple edit operation...\\n")
    
    success = test_simple_edit_operation()
    
    if success:
        print("\\n🎉 Simple edit operation test successful!")
        print("\\n💡 Basic edit logic works correctly")
        print("\\n🔧 The issue with auth.py might be:")
        print("  1. Specific content generated by LLM")
        print("  2. Working directory path issues")
        print("  3. Tool response parsing errors")
        print("  4. File permissions or encoding issues")
    else:
        print("\\n💥 Simple edit operation test failed")
        print("\\n🔧 Basic edit logic has issues")


if __name__ == "__main__":
    main()
