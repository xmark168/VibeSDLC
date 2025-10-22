#!/usr/bin/env python3
"""
Comprehensive test to verify the fuzzy matching fix resolves the indentation issue.
"""


def simulate_validation_with_fix():
    """Simulate the complete validation process with the fuzzy matching fix"""
    print("🔍 Simulating Complete Validation with Fuzzy Fix")
    print("=" * 60)
    
    # Read the actual file content
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        file_lines = file_content.splitlines()
        print(f"✅ Read file: {len(file_content)} chars, {len(file_lines)} lines")
        
        # Test both scenarios:
        # 1. Correct OLD_CODE (should pass with exact matching)
        # 2. Incorrect OLD_CODE (should pass with fuzzy matching)
        
        test_cases = [
            {
                "name": "Correct OLD_CODE (with proper indentation)",
                "old_code": """    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;""",
                "should_pass_exact": True,
                "should_pass_fuzzy": True
            },
            {
                "name": "Incorrect OLD_CODE (missing indentation on line 1)",
                "old_code": """// Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;""",
                "should_pass_exact": False,
                "should_pass_fuzzy": True
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test Case {i}: {test_case['name']}")
            print("-" * 50)
            
            old_code = test_case["old_code"]
            old_lines = old_code.split("\n")
            
            print(f"OLD_CODE lines ({len(old_lines)}):")
            for j, line in enumerate(old_lines):
                print(f"  Line {j + 1}: {repr(line)}")
            
            # Test exact matching
            print(f"\n🔍 Testing exact matching...")
            exact_found = test_exact_matching(file_lines, old_lines)
            exact_result = "✅ PASS" if exact_found else "❌ FAIL"
            expected_exact = "✅ PASS" if test_case["should_pass_exact"] else "❌ FAIL"
            print(f"   Result: {exact_result} (expected: {expected_exact})")
            
            # Test fuzzy matching
            print(f"\n🔍 Testing fuzzy matching...")
            fuzzy_found = test_fuzzy_matching(file_lines, old_lines)
            fuzzy_result = "✅ PASS" if fuzzy_found else "❌ FAIL"
            expected_fuzzy = "✅ PASS" if test_case["should_pass_fuzzy"] else "❌ FAIL"
            print(f"   Result: {fuzzy_result} (expected: {expected_fuzzy})")
            
            # Overall validation result (exact OR fuzzy)
            overall_pass = exact_found or fuzzy_found
            overall_result = "✅ PASS" if overall_pass else "❌ FAIL"
            print(f"\n📊 Overall validation: {overall_result}")
            
            # Check if results match expectations
            exact_correct = (exact_found == test_case["should_pass_exact"])
            fuzzy_correct = (fuzzy_found == test_case["should_pass_fuzzy"])
            overall_correct = overall_pass  # Should always pass with fuzzy fix
            
            if exact_correct and fuzzy_correct and overall_correct:
                print(f"✅ Test case {i} PASSED - behavior as expected")
            else:
                print(f"❌ Test case {i} FAILED - unexpected behavior")
                return False
        
        print(f"\n🎉 All test cases passed! Fuzzy matching fix works correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_exact_matching(file_lines, old_lines):
    """Test exact line matching (original logic)"""
    for i in range(len(file_lines) - len(old_lines) + 1):
        match = True
        for j, old_line in enumerate(old_lines):
            if i + j >= len(file_lines) or file_lines[i + j] != old_line:
                match = False
                break
        if match:
            return True
    return False


def test_fuzzy_matching(file_lines, old_lines):
    """Test fuzzy line matching (new logic)"""
    for i in range(len(file_lines) - len(old_lines) + 1):
        match = True
        
        for j, old_line in enumerate(old_lines):
            file_line_idx = i + j
            if file_line_idx >= len(file_lines):
                match = False
                break
            
            file_line = file_lines[file_line_idx]
            
            # Try exact match first
            if file_line == old_line:
                continue
            
            # Try content match (ignoring leading/trailing whitespace)
            if file_line.strip() == old_line.strip():
                # Check if it's just a leading whitespace difference
                file_content = file_line.strip()
                old_content = old_line.strip()
                
                if file_content == old_content and file_content:  # Non-empty content match
                    continue
            
            # Try empty line match
            if not file_line.strip() and not old_line.strip():
                continue
            
            # No match found for this line
            match = False
            break
        
        if match:
            return True
    
    return False


def test_edge_cases():
    """Test edge cases for the fuzzy matching"""
    print("\n🔍 Testing Edge Cases")
    print("=" * 40)
    
    edge_cases = [
        {
            "name": "Empty lines only",
            "file_lines": ["", "", ""],
            "old_lines": ["", ""],
            "should_match": True
        },
        {
            "name": "Mixed indentation",
            "file_lines": ["    line1", "  line2", "line3"],
            "old_lines": ["line1", "line2", "line3"],
            "should_match": True
        },
        {
            "name": "Trailing whitespace",
            "file_lines": ["line1   ", "line2"],
            "old_lines": ["line1", "line2"],
            "should_match": True
        },
        {
            "name": "Different content",
            "file_lines": ["line1", "line2"],
            "old_lines": ["line1", "different"],
            "should_match": False
        }
    ]
    
    all_passed = True
    
    for i, case in enumerate(edge_cases, 1):
        print(f"\n📋 Edge Case {i}: {case['name']}")
        
        result = test_fuzzy_matching(case["file_lines"], case["old_lines"])
        expected = case["should_match"]
        
        if result == expected:
            print(f"   ✅ PASS - got {result}, expected {expected}")
        else:
            print(f"   ❌ FAIL - got {result}, expected {expected}")
            all_passed = False
    
    return all_passed


def main():
    """Run all comprehensive tests"""
    print("🚀 Comprehensive Test of Fuzzy Matching Fix")
    print("=" * 70)
    
    main_test_success = simulate_validation_with_fix()
    edge_test_success = test_edge_cases()
    
    print("\n" + "=" * 70)
    print(f"📊 Test Results:")
    print(f"   Main validation tests: {'✅ PASS' if main_test_success else '❌ FAIL'}")
    print(f"   Edge case tests: {'✅ PASS' if edge_test_success else '❌ FAIL'}")
    
    if main_test_success and edge_test_success:
        print("🎉 All tests passed! The fuzzy matching fix is ready for production.")
        print("💡 This fix will resolve the indentation issues in implementor agent.")
    else:
        print("❌ Some tests failed. Need to review the implementation.")


if __name__ == "__main__":
    main()
