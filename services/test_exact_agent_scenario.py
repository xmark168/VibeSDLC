#!/usr/bin/env python3
"""
Test script to simulate the exact scenario that the agent encountered.
"""


def test_exact_agent_scenario():
    """Test with the exact OLD_CODE from the error log"""
    print("🔍 Testing Exact Agent Scenario")
    print("=" * 50)
    
    # Read the actual file content
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        file_lines = file_content.splitlines()
        print(f"✅ Read file: {len(file_content)} chars, {len(file_lines)} lines")
        
        # From the error log, the agent expected these exact lines:
        # Line 1: '// Remove the password field from the returned user object'
        # Line 2: '    const userWithoutPassword = savedUser.toObject();'
        # Line 3: '    delete userWithoutPassword.password;'
        # Line 4: ''
        # Line 5: '    return userWithoutPassword;'
        
        # Notice Line 1 has NO leading spaces in the error log!
        old_code_from_error = """// Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;"""
        
        print(f"📋 OLD_CODE from error log (Line 1 has no leading spaces):")
        old_lines = old_code_from_error.split("\n")
        for i, line in enumerate(old_lines):
            print(f"  Line {i + 1}: {repr(line)}")
        
        # Test this against the file
        print(f"\n🔍 Testing this OLD_CODE against file...")
        
        # Test substring match
        if old_code_from_error.strip() in file_content:
            print("✅ Substring match PASSED")
        else:
            print("❌ Substring match FAILED")
        
        # Test line boundaries (exact match)
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
            print(f"✅ Exact line boundaries match at line {found_start + 1}")
        else:
            print(f"❌ Exact line boundaries don't match")
            
            # Show what the file actually has around line 33
            print(f"\n📄 File content around line 33:")
            for i in range(32, min(38, len(file_lines))):
                line_num = i + 1
                file_line = file_lines[i]
                expected_line = old_lines[i - 32] if i - 32 < len(old_lines) else "N/A"
                
                match_status = "✅" if file_line == expected_line else "❌"
                print(f"  Line {line_num} {match_status}:")
                print(f"    File    : {repr(file_line)}")
                print(f"    Expected: {repr(expected_line)}")
                
                if file_line != expected_line:
                    # Analyze the difference
                    if file_line.strip() == expected_line.strip():
                        print(f"    🔍 Content match, whitespace difference")
                        file_leading = len(file_line) - len(file_line.lstrip())
                        expected_leading = len(expected_line) - len(expected_line.lstrip())
                        print(f"    🔍 Leading spaces: file={file_leading}, expected={expected_leading}")
        
        # Test fuzzy matching
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
        
        fuzzy_start = try_fuzzy_line_match(file_lines, old_lines)
        
        if fuzzy_start != -1:
            print(f"✅ Fuzzy match found at line {fuzzy_start + 1}")
            return True
        else:
            print(f"❌ Fuzzy match failed")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_possible_parsing_issue():
    """Test if there's a parsing issue in the modification extraction"""
    print("\n🔍 Testing Possible Parsing Issue")
    print("=" * 50)
    
    # Simulate what might happen during parsing
    # Maybe the regex is stripping leading whitespace?
    
    sample_llm_output = """MODIFICATION #1:
FILE: src/services/authService.js
DESCRIPTION: Add functionality to generate a JWT token upon successful registration.

OLD_CODE:
```javascript
    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;
```

NEW_CODE:
```javascript
    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    // Generate JWT token
    const token = jwt.sign(
      { userId: savedUser._id, email: savedUser.email },
      process.env.JWT_SECRET,
      { expiresIn: '24h' }
    );

    return {
      user: userWithoutPassword,
      token
    };
```"""
    
    print("📋 Sample LLM output:")
    print(sample_llm_output[:200] + "...")
    
    # Test the regex extraction
    import re
    
    old_code_match = re.search(
        r"OLD_CODE:\s*```\w*\n(.*?)\n```", sample_llm_output, re.DOTALL
    )
    
    if old_code_match:
        extracted_old_code = old_code_match.group(1)
        print(f"\n✅ Extracted OLD_CODE:")
        print(f"Raw: {repr(extracted_old_code)}")
        
        lines = extracted_old_code.split('\n')
        print(f"Lines ({len(lines)}):")
        for i, line in enumerate(lines):
            print(f"  Line {i + 1}: {repr(line)}")
        
        # Check if first line has proper indentation
        first_line = lines[0] if lines else ""
        if first_line.startswith("    "):
            print(f"✅ First line has proper indentation (4 spaces)")
        else:
            print(f"❌ First line missing indentation: {repr(first_line)}")
        
        return first_line.startswith("    ")
    else:
        print("❌ Failed to extract OLD_CODE")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Exact Agent Scenario")
    print("=" * 60)
    
    scenario_success = test_exact_agent_scenario()
    parsing_success = test_possible_parsing_issue()
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results:")
    print(f"   Agent scenario test: {'✅ PASS' if scenario_success else '❌ FAIL'}")
    print(f"   Parsing test: {'✅ PASS' if parsing_success else '❌ FAIL'}")
    
    if not scenario_success and parsing_success:
        print("🎯 Issue confirmed: Agent is receiving OLD_CODE with incorrect indentation")
        print("💡 Solution: The fuzzy matching fix should resolve this issue")
    elif scenario_success:
        print("⚠️ Cannot reproduce the issue - might be intermittent or environment-specific")
    else:
        print("❌ Multiple issues detected - need deeper investigation")


if __name__ == "__main__":
    main()
