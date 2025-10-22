#!/usr/bin/env python3
"""
Debug script to analyze line boundaries validation issue in authService.js.
"""


def debug_line_boundaries():
    """Debug the exact line boundaries validation logic"""
    print("🔍 Debugging Line Boundaries Validation")
    print("=" * 50)
    
    # Read the actual file content
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Split into lines (same as IncrementalModificationValidator)
        file_lines = file_content.splitlines()
        
        print(f"✅ Read file: {len(file_content)} characters, {len(file_lines)} lines")
        
        # The OLD_CODE that agent is trying to find
        old_code_agent_expects = """    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;"""
        
        print(f"\n📋 OLD_CODE that agent expects:")
        print(f"Raw string: {repr(old_code_agent_expects)}")
        
        # Split OLD_CODE into lines (same as validation logic)
        old_lines = old_code_agent_expects.split("\n")
        
        print(f"\n📋 OLD_CODE split into {len(old_lines)} lines:")
        for i, line in enumerate(old_lines):
            print(f"  Expected line {i + 1}: {repr(line)}")
        
        # Now simulate the exact validation logic from IncrementalModificationValidator
        print(f"\n🔍 Simulating line boundaries validation...")
        
        found_start = -1
        
        # This is the exact logic from lines 102-110
        for i in range(len(file_lines) - len(old_lines) + 1):
            match = True
            print(f"\n🔎 Checking starting at file line {i + 1}:")
            
            for j, old_line in enumerate(old_lines):
                file_line_idx = i + j
                if file_line_idx >= len(file_lines):
                    print(f"   ❌ Line {j + 1}: File line {file_line_idx + 1} out of bounds")
                    match = False
                    break
                
                file_line = file_lines[file_line_idx]
                
                print(f"   🔍 Line {j + 1}:")
                print(f"      Expected: {repr(old_line)}")
                print(f"      Actual  : {repr(file_line)}")
                
                if file_line != old_line:
                    print(f"      ❌ MISMATCH!")
                    match = False
                    break
                else:
                    print(f"      ✅ MATCH")
            
            if match:
                found_start = i
                print(f"\n✅ Found complete match starting at line {found_start + 1}")
                break
            else:
                print(f"   ❌ No complete match starting at line {i + 1}")
        
        if found_start == -1:
            print(f"\n❌ No complete line boundaries match found!")
            
            # Let's find where the content actually is
            print(f"\n🔍 Looking for partial matches...")
            
            for i, file_line in enumerate(file_lines):
                for j, old_line in enumerate(old_lines):
                    if old_line.strip() and old_line.strip() in file_line:
                        print(f"   📍 Expected line {j + 1} found at file line {i + 1}")
                        print(f"      Expected: {repr(old_line)}")
                        print(f"      File    : {repr(file_line)}")
                        
                        # Analyze differences
                        if old_line != file_line:
                            print(f"      🔍 Differences:")
                            if len(old_line) != len(file_line):
                                print(f"         Length: expected {len(old_line)}, got {len(file_line)}")
                            
                            # Check leading whitespace
                            old_leading = len(old_line) - len(old_line.lstrip())
                            file_leading = len(file_line) - len(file_line.lstrip())
                            if old_leading != file_leading:
                                print(f"         Leading spaces: expected {old_leading}, got {file_leading}")
                            
                            # Check trailing whitespace
                            old_trailing = len(old_line) - len(old_line.rstrip())
                            file_trailing = len(file_line) - len(file_line.rstrip())
                            if old_trailing != file_trailing:
                                print(f"         Trailing spaces: expected {old_trailing}, got {file_trailing}")
        else:
            print(f"\n✅ Complete match found starting at line {found_start + 1}")
        
        return found_start != -1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def suggest_fix():
    """Suggest how to fix the line boundaries issue"""
    print("\n💡 Suggested Fixes:")
    print("=" * 50)
    
    print("1. 🔧 Check for line ending differences:")
    print("   - File might have CRLF (\\r\\n) while OLD_CODE expects LF (\\n)")
    print("   - Use consistent line endings")
    
    print("\n2. 🔧 Check for trailing whitespace:")
    print("   - File lines might have trailing spaces")
    print("   - OLD_CODE might not include trailing spaces")
    
    print("\n3. 🔧 Use more robust validation:")
    print("   - Strip whitespace before comparison")
    print("   - Normalize line endings")
    print("   - Use fuzzy matching for minor differences")
    
    print("\n4. 🔧 Use smaller, more specific OLD_CODE:")
    print("   - Instead of 5 lines, use 1-2 lines")
    print("   - Focus on unique identifiers")


def main():
    """Run the debug analysis"""
    print("🚀 Debugging authService.js Line Boundaries Issue")
    print("=" * 60)
    
    success = debug_line_boundaries()
    suggest_fix()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Line boundaries validation should work")
    else:
        print("❌ Line boundaries validation failed - need to fix OLD_CODE format")


if __name__ == "__main__":
    main()
