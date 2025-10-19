"""
Test JSON format của filesystem tools
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


def test_write_file_tool_json():
    """Test write_file_tool returns JSON format."""
    print("🧪 Testing write_file_tool JSON format...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test successful write
        result = write_file_tool.invoke({
            "file_path": "test.py",
            "content": "print('Hello World')",
            "working_directory": temp_dir
        })
        
        print(f"Raw result: {result}")
        
        try:
            result_data = json.loads(result)
            print(f"✅ JSON parsed successfully: {result_data}")
            
            if result_data.get("status") == "success":
                print("✅ Status is 'success'")
            else:
                print(f"❌ Unexpected status: {result_data.get('status')}")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            return False
            
    return True


def test_edit_file_tool_json():
    """Test edit_file_tool returns JSON format."""
    print("\n🧪 Testing edit_file_tool JSON format...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test file first
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("# TODO: Implement\nprint('placeholder')")
        
        # Test successful edit
        result = edit_file_tool.invoke({
            "file_path": "test.py",
            "old_str": "# TODO: Implement",
            "new_str": "# Implementation complete",
            "working_directory": temp_dir
        })
        
        print(f"Raw result: {result}")
        
        try:
            result_data = json.loads(result)
            print(f"✅ JSON parsed successfully: {result_data}")
            
            if result_data.get("status") == "success":
                print("✅ Status is 'success'")
            else:
                print(f"❌ Unexpected status: {result_data.get('status')}")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            return False
            
        # Test error case - string not found
        result = edit_file_tool.invoke({
            "file_path": "test.py",
            "old_str": "# TODO: Implement",  # This should not exist anymore
            "new_str": "# Another change",
            "working_directory": temp_dir
        })
        
        print(f"Error case raw result: {result}")
        
        try:
            result_data = json.loads(result)
            print(f"✅ Error JSON parsed successfully: {result_data}")
            
            if result_data.get("status") == "error":
                print("✅ Error status is 'error'")
            else:
                print(f"❌ Unexpected error status: {result_data.get('status')}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Error JSON parsing failed: {e}")
            return False
            
    return True


def main():
    """Run JSON format tests."""
    print("🚀 Testing Filesystem Tools JSON Format...\n")
    
    success1 = test_write_file_tool_json()
    success2 = test_edit_file_tool_json()
    
    print("\n🏁 Tests Completed!")
    print(f"   write_file_tool: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"   edit_file_tool: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    overall_success = success1 and success2
    print(f"   Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print("\n🎉 All tools now return proper JSON format!")
        print("✅ Ready to fix implement_files.py JSON parsing errors")
    else:
        print("\n💥 Some tests failed - check tool implementations")


if __name__ == "__main__":
    main()
