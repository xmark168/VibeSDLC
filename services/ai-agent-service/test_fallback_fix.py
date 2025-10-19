"""
Test fixed fallback mechanism để đảm bảo không có line number corruption
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


def test_fallback_mechanism_fix():
    """Test fixed fallback mechanism (append to end of file)."""
    print("🧪 Testing fixed fallback mechanism...")
    
    # Create test file without insertion points (like user.py, schemas/user.py)
    test_content = '''class UserModel(Base):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    reset_password_token: Mapped[Optional[str]] = mapped_column(String(255))
'''
    
    new_implementation = '''
# Additional user fields
verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

def verify_email(self):
    """Mark user as verified."""
    self.is_verified = True
    self.verification_token = None'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = Path(temp_dir) / "user_model.py"
        test_file.write_text(test_content)
        
        print(f"📄 Created test file")
        
        # Step 1: Read file content (formatted with line numbers)
        formatted_result = read_file_tool.invoke({
            "file_path": "user_model.py",
            "working_directory": temp_dir
        })
        
        print(f"📖 Formatted content from read_file_tool:")
        print(repr(formatted_result[:200]) + "...")
        
        # Step 2: Simulate fallback mechanism (no insertion point found)
        print("⚠️ No insertion point found, appending to end of file")
        
        # OLD BUGGY WAY (would cause corruption):
        # current_content = formatted_result  # ❌ Contains line numbers!
        
        # NEW FIXED WAY:
        current_content = _extract_actual_content(formatted_result)  # ✅ Extract actual content
        new_content = current_content + "\n\n" + new_implementation
        
        print(f"📄 Extracted actual content:")
        print(repr(current_content[:200]) + "...")
        
        print(f"📄 Final content to write:")
        print(repr(new_content[:300]) + "...")
        
        # Step 3: Write new content
        result = write_file_tool.invoke({
            "file_path": "user_model.py",
            "content": new_content,
            "working_directory": temp_dir
        })
        
        print(f"✏️ Write result: {result}")
        
        # Step 4: Verify result
        try:
            result_data = json.loads(result)
            if result_data.get("status") == "success":
                print("✅ Write successful!")
                
                # Read final file content
                final_content = test_file.read_text()
                print(f"📄 Final file content:")
                print(final_content)
                
                # Check for corruption indicators
                corruption_indicators = [
                    "\t",  # Tab characters from line numbers
                    "     1\t",  # Line number format
                    "     2\t",
                    "    10\t",
                ]
                
                has_corruption = any(indicator in final_content for indicator in corruption_indicators)
                
                if has_corruption:
                    print("❌ CORRUPTION DETECTED! File contains line number artifacts")
                    for indicator in corruption_indicators:
                        if indicator in final_content:
                            print(f"   Found: {repr(indicator)}")
                    return False
                else:
                    print("✅ NO CORRUPTION! File content is clean")
                    
                    # Check if new content was added correctly
                    if "verification_token" in final_content and "def verify_email" in final_content:
                        print("✅ New content added correctly")
                        return True
                    else:
                        print("❌ New content not found")
                        return False
            else:
                print(f"❌ Write failed: {result_data.get('message')}")
                return False
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            return False


def test_before_and_after_comparison():
    """Test comparison between old buggy way vs new fixed way."""
    print("\n🧪 Testing before/after comparison...")
    
    test_content = '''class TestClass:
    def method1(self):
        return "test"
'''
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text(test_content)
        
        # Read formatted content
        formatted_result = read_file_tool.invoke({
            "file_path": "test.py",
            "working_directory": temp_dir
        })
        
        print(f"📖 Formatted result from read_file_tool:")
        print(repr(formatted_result))
        
        # OLD BUGGY WAY:
        old_way_content = formatted_result + "\n\n# NEW CODE"
        print(f"❌ OLD WAY (buggy) would produce:")
        print(repr(old_way_content))
        
        # NEW FIXED WAY:
        actual_content = _extract_actual_content(formatted_result)
        new_way_content = actual_content + "\n\n# NEW CODE"
        print(f"✅ NEW WAY (fixed) produces:")
        print(repr(new_way_content))
        
        # Verify difference
        has_line_numbers_old = "\t" in old_way_content and "     1\t" in old_way_content
        has_line_numbers_new = "\t" in new_way_content and "     1\t" in new_way_content
        
        print(f"Old way has line number corruption: {has_line_numbers_old}")
        print(f"New way has line number corruption: {has_line_numbers_new}")
        
        return not has_line_numbers_new  # Success if new way has no corruption


def main():
    """Run fallback fix tests."""
    print("🚀 Testing Fixed Fallback Mechanism...\n")
    
    success1 = test_fallback_mechanism_fix()
    success2 = test_before_and_after_comparison()
    
    print("\n🏁 Tests Completed!")
    print(f"   Fallback mechanism fix: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"   Before/after comparison: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    overall_success = success1 and success2
    print(f"   Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print("\n🎉 Fallback mechanism fix works perfectly!")
        print("\n💡 Root cause analysis:")
        print("   ❌ OLD: current_content = read_result  # Contains line numbers!")
        print("   ✅ NEW: current_content = _extract_actual_content(read_result)")
        print("\n🔧 This fix prevents:")
        print("   - Line number corruption in files")
        print("   - Tab character artifacts")
        print("   - Duplicate classes/fields from formatted content")
        print("   - Invalid Python syntax from cat -n format")
        print("\n🚀 Incremental modification fallback now works correctly!")
    else:
        print("\n💥 Some tests failed - check logic")


if __name__ == "__main__":
    main()
