#!/usr/bin/env python3
"""
Test script to validate the fuzzy line matching fix.
"""


def test_fuzzy_line_match():
    """Test the fuzzy line matching logic"""
    print("🔍 Testing Fuzzy Line Matching Fix")
    print("=" * 50)
    
    # Read the actual file content
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        file_lines = file_content.splitlines()
        print(f"✅ Read file: {len(file_content)} chars, {len(file_lines)} lines")
        
        # The problematic OLD_CODE (with incorrect indentation on first line)
        old_code = """    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;"""
        
        old_lines = old_code.split("\n")
        
        print(f"📋 Testing OLD_CODE with {len(old_lines)} lines:")
        for i, line in enumerate(old_lines):
            print(f"  Line {i + 1}: {repr(line)}")
        
        # Simulate the fuzzy matching logic
        print(f"\n🔍 Testing fuzzy line matching...")
        
        def try_fuzzy_line_match(file_lines, old_lines):
            """Simulate the fuzzy matching logic"""
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
                    return i
            
            return -1
        
        found_start = try_fuzzy_line_match(file_lines, old_lines)
        
        if found_start != -1:
            print(f"✅ Fuzzy match found starting at line {found_start + 1}")
            
            # Show the match details
            print(f"\n📋 Match details:")
            for j, old_line in enumerate(old_lines):
                file_line = file_lines[found_start + j]
                match_type = "exact" if file_line == old_line else "fuzzy"
                print(f"  Line {j + 1} ({match_type}):")
                print(f"    Expected: {repr(old_line)}")
                print(f"    File    : {repr(file_line)}")
            
            return True
        else:
            print(f"❌ Fuzzy match failed")
            
            # Debug why it failed
            print(f"\n🔍 Debugging fuzzy match failure...")
            
            # Check each line individually
            for i, old_line in enumerate(old_lines):
                print(f"\nLine {i + 1}: {repr(old_line)}")
                
                # Find exact matches
                exact_matches = []
                fuzzy_matches = []
                
                for j, file_line in enumerate(file_lines):
                    if file_line == old_line:
                        exact_matches.append(j + 1)
                    elif file_line.strip() == old_line.strip() and old_line.strip():
                        fuzzy_matches.append(j + 1)
                
                if exact_matches:
                    print(f"  Exact matches at file lines: {exact_matches}")
                elif fuzzy_matches:
                    print(f"  Fuzzy matches at file lines: {fuzzy_matches}")
                else:
                    print(f"  No matches found")
            
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_original_validation():
    """Test the original validation logic for comparison"""
    print("\n🔍 Testing Original Validation Logic")
    print("=" * 50)
    
    # Read the actual file content
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        file_lines = file_content.splitlines()
        
        # The problematic OLD_CODE
        old_code = """    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;"""
        
        old_lines = old_code.split("\n")
        
        # Test original exact matching
        print(f"🔍 Testing original exact matching...")
        
        found_start = -1
        for i in range(len(file_lines) - len(old_lines) + 1):
            match = True
            for j, old_line in enumerate(old_lines):
                if i + j >= len(file_lines) or file_lines[i + j] != old_line:
                    match = False
                    break
            if match:
                found_start = i
                break
        
        if found_start != -1:
            print(f"✅ Original exact match found at line {found_start + 1}")
        else:
            print(f"❌ Original exact match failed (as expected)")
        
        return found_start != -1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Fuzzy Line Matching Fix")
    print("=" * 60)
    
    original_success = test_original_validation()
    fuzzy_success = test_fuzzy_line_match()
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results:")
    print(f"   Original validation: {'✅ PASS' if original_success else '❌ FAIL'}")
    print(f"   Fuzzy validation: {'✅ PASS' if fuzzy_success else '❌ FAIL'}")
    
    if not original_success and fuzzy_success:
        print("🎉 Fix successful! Fuzzy matching resolves the indentation issue.")
    elif original_success:
        print("⚠️ Original validation already works - issue might be elsewhere.")
    else:
        print("❌ Fix didn't work - need to investigate further.")


if __name__ == "__main__":
    main()
