#!/usr/bin/env python3
"""
Test script để verify import fix cho structured modifications
"""

import sys
import os

def test_imports():
    """Test that all imports work correctly"""
    
    print("🧪 Testing Import Fix")
    print("=" * 60)
    
    try:
        # Add current directory to path for imports
        sys.path.insert(0, os.path.abspath('.'))
        sys.path.insert(0, os.path.abspath('ai-agent-service'))
        
        # Test import of incremental_modifications module
        from app.agents.developer.implementor.utils.incremental_modifications import (
            CodeModification,
            IncrementalModificationValidator,
            parse_structured_modifications,
        )
        print("✅ Successfully imported incremental_modifications utilities")
        
        # Test import in implement_files (this should work now)
        from app.agents.developer.implementor.nodes.implement_files import (
            implement_files,
            _extract_actual_content,
        )
        print("✅ Successfully imported implement_files functions")
        
        # Test that parse_structured_modifications is accessible
        sample_output = """
MODIFICATION #1:
FILE: test.js
DESCRIPTION: Test modification

OLD_CODE:
```javascript
console.log('old');
```

NEW_CODE:
```javascript
console.log('new');
```
"""
        
        modifications = parse_structured_modifications(sample_output)
        if len(modifications) == 1:
            print("✅ parse_structured_modifications working correctly")
            print(f"   Parsed modification: {modifications[0].description}")
        else:
            print(f"❌ Expected 1 modification, got {len(modifications)}")
            return False
        
        # Test CodeModification creation
        mod = CodeModification(
            file_path="test.js",
            old_code="console.log('old');",
            new_code="console.log('new');",
            description="Test modification"
        )
        print("✅ CodeModification creation working")
        
        # Test validator creation
        validator = IncrementalModificationValidator("console.log('old');")
        print("✅ IncrementalModificationValidator creation working")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_file_structure():
    """Test that required files exist with correct structure"""
    
    print("\n🧪 Testing File Structure")
    print("=" * 60)
    
    files_to_check = [
        "ai-agent-service/app/agents/developer/implementor/utils/incremental_modifications.py",
        "ai-agent-service/app/agents/developer/implementor/nodes/implement_files.py",
        "ai-agent-service/app/agents/developer/implementor/nodes/generate_code.py",
    ]
    
    all_exist = True
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
            
            # Check for specific imports in implement_files.py
            if "implement_files.py" in file_path:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                if "parse_structured_modifications" in content:
                    print("      ✅ parse_structured_modifications import found")
                else:
                    print("      ❌ parse_structured_modifications import missing")
                    all_exist = False
                
                if "IncrementalModificationValidator" in content:
                    print("      ✅ IncrementalModificationValidator import found")
                else:
                    print("      ❌ IncrementalModificationValidator import missing")
                    all_exist = False
        else:
            print(f"   ❌ {file_path}")
            all_exist = False
    
    return all_exist

def main():
    """Main test function"""
    
    print("🚀 Import Fix Verification Test")
    print("=" * 80)
    
    tests = [
        ("Import functionality", test_imports),
        ("File structure", test_file_structure),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 IMPORT FIX TEST SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Import Fix Successful!")
        print("\n✅ Fixed Issues:")
        print("   - Added missing import for parse_structured_modifications")
        print("   - Added missing import for IncrementalModificationValidator")
        print("   - All structured modification utilities now accessible")
        
        print("\n🚀 Expected Behavior:")
        print("   - No more 'file_path' KeyError")
        print("   - Structured modifications parsing works")
        print("   - File modification workflow completes successfully")
        
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
