#!/usr/bin/env python3
"""
Test script to verify Pydantic validation fix for FileChange.change_type
"""

import sys
import os

sys.path.append('ai-agent-service/app/agents/developer/implementor')

def test_filechange_validation():
    """Test that FileChange accepts 'full_file' change_type"""
    print("=" * 60)
    print("Testing FileChange Pydantic Validation")
    print("=" * 60)
    
    try:
        from state import FileChange
        
        print("\n✅ Successfully imported FileChange")
        
        # Test 1: Create FileChange with "full_file" (should work)
        print("\n📝 Test 1: Creating FileChange with change_type='full_file'")
        try:
            file_change_full = FileChange(
                file_path="src/test.js",
                operation="modify",
                content="console.log('test');",
                change_type="full_file",
                description="Test modification"
            )
            print("   ✅ PASS: FileChange created successfully with 'full_file'")
            print(f"   📊 change_type: {file_change_full.change_type}")
        except Exception as e:
            print(f"   ❌ FAIL: {e}")
            return False
        
        # Test 2: Create FileChange with "incremental" (should work)
        print("\n📝 Test 2: Creating FileChange with change_type='incremental'")
        try:
            file_change_inc = FileChange(
                file_path="src/test.js",
                operation="modify",
                content="",
                change_type="incremental",
                structured_modifications="MODIFICATION #1...",
                description="Test modification"
            )
            print("   ✅ PASS: FileChange created successfully with 'incremental'")
            print(f"   📊 change_type: {file_change_inc.change_type}")
        except Exception as e:
            print(f"   ❌ FAIL: {e}")
            return False
        
        # Test 3: Try to create FileChange with "full" (should fail)
        print("\n📝 Test 3: Creating FileChange with change_type='full' (should fail)")
        try:
            file_change_invalid = FileChange(
                file_path="src/test.js",
                operation="modify",
                content="console.log('test');",
                change_type="full",  # Invalid value
                description="Test modification"
            )
            print("   ❌ FAIL: Should have raised validation error but didn't")
            return False
        except Exception as e:
            if "literal_error" in str(e) or "Input should be" in str(e):
                print(f"   ✅ PASS: Correctly rejected invalid value 'full'")
                print(f"   📊 Error: {str(e)[:100]}...")
            else:
                print(f"   ❌ FAIL: Unexpected error: {e}")
                return False
        
        # Test 4: Check default value
        print("\n📝 Test 4: Creating FileChange without change_type (check default)")
        try:
            file_change_default = FileChange(
                file_path="src/test.js",
                operation="modify",
                content="console.log('test');",
                description="Test modification"
            )
            print(f"   ✅ PASS: FileChange created with default change_type")
            print(f"   📊 Default change_type: {file_change_default.change_type}")
            
            if file_change_default.change_type == "incremental":
                print("   ✅ Default value is 'incremental' (as expected)")
            else:
                print(f"   ⚠️ Warning: Default value is '{file_change_default.change_type}' (expected 'incremental')")
        except Exception as e:
            print(f"   ❌ FAIL: {e}")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_execute_step_usage():
    """Test that execute_step.py uses correct change_type value"""
    print("\n" + "=" * 60)
    print("Testing execute_step.py Usage")
    print("=" * 60)
    
    try:
        file_path = "ai-agent-service/app/agents/developer/implementor/nodes/execute_step.py"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n✅ Read {file_path}")
        
        # Check for correct usage: change_type="full_file"
        correct_usage_count = content.count('change_type="full_file"')
        print(f"\n📊 Found {correct_usage_count} occurrences of change_type=\"full_file\"")
        
        if correct_usage_count >= 2:
            print("   ✅ PASS: Both callers use correct value 'full_file'")
        else:
            print(f"   ⚠️ Warning: Expected at least 2 occurrences, found {correct_usage_count}")
        
        # Check for incorrect usage: change_type="full"
        incorrect_usage_count = content.count('change_type="full"')
        print(f"\n📊 Found {incorrect_usage_count} occurrences of change_type=\"full\"")
        
        if incorrect_usage_count == 0:
            print("   ✅ PASS: No incorrect usage of 'full' found")
        else:
            print(f"   ❌ FAIL: Found {incorrect_usage_count} incorrect usage(s) of 'full'")
            return False
        
        return correct_usage_count >= 2
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Pydantic Validation Fix")
    print("=" * 70)
    
    test1 = test_filechange_validation()
    test2 = test_execute_step_usage()
    
    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print(f"   FileChange Validation: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   execute_step.py Usage: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    all_pass = test1 and test2
    
    print("\n" + "=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASSED - Pydantic validation fix is correct!")
        print("\n💡 Summary:")
        print("   - FileChange accepts 'full_file' and 'incremental'")
        print("   - FileChange rejects invalid value 'full'")
        print("   - execute_step.py uses correct value 'full_file'")
    else:
        print("❌ SOME TESTS FAILED - Review implementation")
    
    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

