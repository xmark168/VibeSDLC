#!/usr/bin/env python3
"""
Debug script to analyze the authService.js modification issue.
"""

import re


def debug_old_code_matching():
    """Debug why OLD_CODE doesn't match in authService.js"""
    print("🔍 Debugging authService.js OLD_CODE matching issue...")
    
    # Read the actual file content
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        print(f"✅ Read file: {len(file_content)} characters")
        
        # The OLD_CODE that agent is trying to find
        old_code_agent_expects = """    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;"""
        
        print("\n📋 OLD_CODE that agent expects:")
        print("=" * 50)
        for i, line in enumerate(old_code_agent_expects.split('\n'), 1):
            print(f"Line {i}: '{line}'")
        
        # Check if this exact pattern exists
        if old_code_agent_expects in file_content:
            print("\n✅ Exact OLD_CODE found in file!")
        else:
            print("\n❌ Exact OLD_CODE NOT found in file")
            
            # Let's find the actual lines in the file
            file_lines = file_content.split('\n')
            
            print("\n📄 Actual file content around lines 33-37:")
            print("=" * 50)
            for i in range(32, min(38, len(file_lines))):
                line_num = i + 1
                line_content = file_lines[i]
                print(f"Line {line_num}: '{line_content}'")
            
            # Try to find similar patterns
            print("\n🔍 Looking for similar patterns...")
            
            # Extract the key lines from expected OLD_CODE
            expected_lines = old_code_agent_expects.split('\n')
            
            for i, expected_line in enumerate(expected_lines, 1):
                print(f"\n🔎 Searching for expected line {i}: '{expected_line}'")
                
                # Look for similar lines in file
                for j, file_line in enumerate(file_lines, 1):
                    # Check for substring match (ignoring exact whitespace)
                    expected_stripped = expected_line.strip()
                    file_stripped = file_line.strip()
                    
                    if expected_stripped and expected_stripped in file_stripped:
                        print(f"   📍 Similar found at line {j}: '{file_line}'")
                        
                        # Check indentation difference
                        expected_indent = len(expected_line) - len(expected_line.lstrip())
                        file_indent = len(file_line) - len(file_line.lstrip())
                        
                        if expected_indent != file_indent:
                            print(f"   ⚠️ Indentation mismatch: expected {expected_indent} spaces, got {file_indent} spaces")
            
            # Try to construct the correct OLD_CODE
            print("\n💡 Suggested correct OLD_CODE:")
            print("=" * 50)
            
            # Find the actual lines that should be replaced
            start_line = None
            end_line = None
            
            for i, line in enumerate(file_lines):
                if "Remove the password field from the returned user object" in line:
                    start_line = i
                    break
            
            if start_line is not None:
                # Find the end (return statement)
                for i in range(start_line, len(file_lines)):
                    if "return userWithoutPassword;" in file_lines[i]:
                        end_line = i
                        break
                
                if end_line is not None:
                    print("Correct OLD_CODE should be:")
                    for i in range(start_line, end_line + 1):
                        print(f"'{file_lines[i]}'")
                    
                    # Show the exact string
                    correct_old_code = '\n'.join(file_lines[start_line:end_line + 1])
                    print(f"\nExact string:\n{repr(correct_old_code)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def analyze_whitespace_issues():
    """Analyze potential whitespace and encoding issues"""
    print("\n🔍 Analyzing whitespace and encoding issues...")
    
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
    
    try:
        # Read as bytes to check encoding
        with open(file_path, 'rb') as f:
            raw_content = f.read()
        
        # Check for different line endings
        has_crlf = b'\r\n' in raw_content
        has_lf = b'\n' in raw_content
        has_cr = b'\r' in raw_content
        
        print(f"📊 Line ending analysis:")
        print(f"   CRLF (\\r\\n): {has_crlf}")
        print(f"   LF (\\n): {has_lf}")
        print(f"   CR (\\r): {has_cr}")
        
        # Check encoding
        try:
            utf8_content = raw_content.decode('utf-8')
            print(f"   ✅ UTF-8 encoding: OK")
        except UnicodeDecodeError:
            print(f"   ❌ UTF-8 encoding: FAILED")
        
        # Analyze specific lines around the problem area
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"\n📋 Detailed line analysis (lines 33-37):")
        for i in range(32, min(38, len(lines))):
            line = lines[i]
            line_num = i + 1
            
            # Analyze the line
            raw_repr = repr(line)
            stripped = line.strip()
            leading_spaces = len(line) - len(line.lstrip())
            
            print(f"Line {line_num}:")
            print(f"   Raw: {raw_repr}")
            print(f"   Stripped: '{stripped}'")
            print(f"   Leading spaces: {leading_spaces}")
            print(f"   Length: {len(line)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def suggest_fix():
    """Suggest how to fix the modification"""
    print("\n💡 Suggested Fix:")
    print("=" * 50)
    
    print("1. 🔧 Update the OLD_CODE in the modification to match exact indentation:")
    print("   - Use 2 spaces instead of 4 spaces for indentation")
    print("   - Remove the empty line between delete and return statements")
    
    print("\n2. 🔧 Correct OLD_CODE should be:")
    print("""  // Remove the password field from the returned user object
  const userWithoutPassword = savedUser.toObject();
  delete userWithoutPassword.password;

  return userWithoutPassword;""")
    
    print("\n3. 🔧 Or use a more specific, smaller OLD_CODE pattern:")
    print("   Instead of replacing 5 lines, replace just the return statement:")
    print("   OLD_CODE: 'return userWithoutPassword;'")
    print("   NEW_CODE: Add JWT generation before return")


def main():
    """Run all debug analyses"""
    print("🚀 Debugging authService.js Modification Issue")
    print("=" * 60)
    
    debug_old_code_matching()
    analyze_whitespace_issues()
    suggest_fix()
    
    print("\n" + "=" * 60)
    print("🎯 Summary: The issue is indentation mismatch between expected and actual code.")
    print("💡 Solution: Update OLD_CODE to match exact file indentation (2 spaces, not 4).")


if __name__ == "__main__":
    main()
