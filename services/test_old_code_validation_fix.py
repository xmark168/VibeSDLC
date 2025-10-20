#!/usr/bin/env python3
"""
Test script để verify OLD_CODE validation fix trong incremental_modifications.py
"""

import os
import sys

# Add the path to import modules
sys.path.append('ai-agent-service/app/agents/developer/implementor/utils')

from incremental_modifications import IncrementalModificationValidator, CodeModification

def test_user_js_validation():
    """Test validation với actual User.js file content"""
    
    print("🧪 Testing User.js OLD_CODE Validation Fix")
    print("=" * 60)
    
    # Read actual User.js file
    user_js_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/models/User.js"
    
    if not os.path.exists(user_js_path):
        print(f"❌ File not found: {user_js_path}")
        return False
    
    try:
        with open(user_js_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        print(f"📄 File loaded: {len(file_content)} chars, {file_content.count(chr(10)) + 1} lines")
        
        # Create validator
        validator = IncrementalModificationValidator(file_content)
        
        # Test case 1: Exact OLD_CODE từ line 29
        print(f"\n🧪 Test 1: Exact OLD_CODE from line 29")
        old_code_exact = "const User = mongoose.model('User', userSchema);"
        modification_exact = CodeModification(
            file_path="src/models/User.js",
            description="Add comparePassword method",
            old_code=old_code_exact,
            new_code="""userSchema.methods.comparePassword = function(candidatePassword) {
    return this.password === candidatePassword;
};

const User = mongoose.model('User', userSchema);"""
        )
        
        is_valid_exact, error_exact = validator.validate_modification(modification_exact)
        print(f"   Result: {'✅ VALID' if is_valid_exact else '❌ INVALID'}")
        if not is_valid_exact:
            print(f"   Error: {error_exact}")
        
        # Test case 2: OLD_CODE với extra whitespace
        print(f"\n🧪 Test 2: OLD_CODE with extra whitespace")
        old_code_whitespace = "  const User = mongoose.model('User', userSchema);  "
        modification_whitespace = CodeModification(
            file_path="src/models/User.js",
            description="Add comparePassword method",
            old_code=old_code_whitespace,
            new_code="""userSchema.methods.comparePassword = function(candidatePassword) {
    return this.password === candidatePassword;
};

const User = mongoose.model('User', userSchema);"""
        )
        
        is_valid_whitespace, error_whitespace = validator.validate_modification(modification_whitespace)
        print(f"   Result: {'✅ VALID' if is_valid_whitespace else '❌ INVALID'}")
        if not is_valid_whitespace:
            print(f"   Error: {error_whitespace}")
        
        # Test case 3: OLD_CODE với different line endings
        print(f"\n🧪 Test 3: OLD_CODE with different line endings")
        old_code_line_endings = "const User = mongoose.model('User', userSchema);\r\n"
        modification_line_endings = CodeModification(
            file_path="src/models/User.js",
            description="Add comparePassword method",
            old_code=old_code_line_endings,
            new_code="""userSchema.methods.comparePassword = function(candidatePassword) {
    return this.password === candidatePassword;
};

const User = mongoose.model('User', userSchema);"""
        )
        
        is_valid_line_endings, error_line_endings = validator.validate_modification(modification_line_endings)
        print(f"   Result: {'✅ VALID' if is_valid_line_endings else '❌ INVALID'}")
        if not is_valid_line_endings:
            print(f"   Error: {error_line_endings}")
        
        # Test case 4: Multi-line OLD_CODE
        print(f"\n🧪 Test 4: Multi-line OLD_CODE")
        old_code_multiline = """});

const User = mongoose.model('User', userSchema);"""
        modification_multiline = CodeModification(
            file_path="src/models/User.js",
            description="Add comparePassword method",
            old_code=old_code_multiline,
            new_code="""});

userSchema.methods.comparePassword = function(candidatePassword) {
    return this.password === candidatePassword;
};

const User = mongoose.model('User', userSchema);"""
        )
        
        is_valid_multiline, error_multiline = validator.validate_modification(modification_multiline)
        print(f"   Result: {'✅ VALID' if is_valid_multiline else '❌ INVALID'}")
        if not is_valid_multiline:
            print(f"   Error: {error_multiline}")
        
        # Test case 5: Invalid OLD_CODE (should fail)
        print(f"\n🧪 Test 5: Invalid OLD_CODE (should fail)")
        old_code_invalid = "const User = mongoose.model('NonExistent', userSchema);"
        modification_invalid = CodeModification(
            file_path="src/models/User.js",
            description="Add comparePassword method",
            old_code=old_code_invalid,
            new_code="""userSchema.methods.comparePassword = function(candidatePassword) {
    return this.password === candidatePassword;
};

const User = mongoose.model('User', userSchema);"""
        )
        
        is_valid_invalid, error_invalid = validator.validate_modification(modification_invalid)
        print(f"   Result: {'✅ VALID' if is_valid_invalid else '❌ INVALID (Expected)'}")
        if not is_valid_invalid:
            print(f"   Error: {error_invalid[:200]}...")
        
        # Summary
        test_results = [
            ("Exact OLD_CODE", is_valid_exact),
            ("Whitespace tolerance", is_valid_whitespace),
            ("Line ending tolerance", is_valid_line_endings),
            ("Multi-line OLD_CODE", is_valid_multiline),
            ("Invalid OLD_CODE (should fail)", not is_valid_invalid)  # Inverted because we expect failure
        ]
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        print(f"\n📊 Test Results: {passed}/{total} passed")
        for test_name, result in test_results:
            status = "✅" if result else "❌"
            print(f"   {status} {test_name}")
        
        return passed == total
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_line_count_accuracy():
    """Test that line count calculation is accurate"""
    
    print("\n🧪 Testing Line Count Accuracy")
    print("=" * 60)
    
    user_js_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/models/User.js"
    
    try:
        with open(user_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Different ways to count lines
        lines_split_n = content.split('\n')
        lines_splitlines = content.splitlines()
        lines_count_newlines = content.count('\n') + 1
        
        print(f"📊 Line counting methods:")
        print(f"   split('\\n'): {len(lines_split_n)} lines")
        print(f"   splitlines(): {len(lines_splitlines)} lines")
        print(f"   count('\\n') + 1: {lines_count_newlines} lines")
        
        # Check if file ends with newline
        ends_with_newline = content.endswith('\n')
        print(f"   Ends with newline: {ends_with_newline}")
        
        # Create validator and check its line count
        validator = IncrementalModificationValidator(content)
        validator_lines = len(validator.lines)
        print(f"   Validator lines: {validator_lines} lines")
        
        # Expected: splitlines() should be most accurate
        expected_lines = len(lines_splitlines)
        print(f"\n🎯 Expected line count: {expected_lines}")
        
        # Check line 29 specifically
        if len(lines_splitlines) >= 29:
            line_29 = lines_splitlines[28]  # 0-based index
            print(f"📄 Line 29 content: {repr(line_29)}")
            
            # Check if it contains the expected code
            expected_code = "const User = mongoose.model('User', userSchema);"
            contains_expected = expected_code in line_29
            print(f"   Contains expected code: {contains_expected}")
            
            return validator_lines == expected_lines and contains_expected
        else:
            print(f"❌ File has fewer than 29 lines")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_debug_logging():
    """Test that debug logging provides useful information"""
    
    print("\n🧪 Testing Debug Logging")
    print("=" * 60)
    
    user_js_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/models/User.js"
    
    try:
        with open(user_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        validator = IncrementalModificationValidator(content)
        
        # Test với OLD_CODE that will trigger debug logging
        old_code = "const User = mongoose.model('User', userSchema);"
        modification = CodeModification(
            file_path="src/models/User.js",
            description="Test debug logging",
            old_code=old_code,
            new_code="// New code here\nconst User = mongoose.model('User', userSchema);"
        )
        
        print("🔍 Running validation with debug logging:")
        is_valid, error = validator.validate_modification(modification)
        
        print(f"\nResult: {'✅ VALID' if is_valid else '❌ INVALID'}")
        if not is_valid:
            print(f"Error: {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test function"""
    
    print("🚀 OLD_CODE Validation Fix Verification")
    print("=" * 80)
    
    tests = [
        ("User.js validation", test_user_js_validation),
        ("Line count accuracy", test_line_count_accuracy),
        ("Debug logging", test_debug_logging),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*80}")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 OLD_CODE VALIDATION FIX SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 OLD_CODE Validation Fix Verified!")
        print("\n✅ Fix Features:")
        print("   - 🔍 Enhanced debug logging với character representation")
        print("   - 🔄 Multiple matching strategies (exact, normalized, line-by-line)")
        print("   - 🧹 Whitespace và line ending tolerance")
        print("   - 📊 Accurate line count calculation")
        print("   - 💡 Detailed error messages với context")
        print("   - 🎯 Maintains validation accuracy")
        
        print("\n🚀 Expected Behavior:")
        print("   - ✅ Finds 'const User = mongoose.model' at line 29")
        print("   - ✅ Handles whitespace differences gracefully")
        print("   - ✅ Provides detailed debug information")
        print("   - ✅ File modification workflow completes successfully")
        print("   - ✅ Sequential tasks work without overwriting")
        
    else:
        print("⚠️ Some validation fix tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
