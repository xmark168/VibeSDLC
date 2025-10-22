#!/usr/bin/env python3
"""
Simple debug script to test validation logic without dependencies.
"""


def test_validation_logic():
    """Test the validation logic with exact same parameters"""
    print("🔍 Testing Validation Logic (Simplified)")
    print("=" * 50)
    
    # Read the actual file content
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        print(f"✅ Read file: {len(file_content)} chars")
        
        # The exact OLD_CODE that's failing
        old_code = """    // Remove the password field from the returned user object
    const userWithoutPassword = savedUser.toObject();
    delete userWithoutPassword.password;

    return userWithoutPassword;"""
        
        print(f"📋 OLD_CODE to validate:")
        print(f"   Length: {len(old_code)} chars")
        print(f"   Raw: {repr(old_code)}")
        
        # Step 1: Test substring match (this should pass)
        print(f"\n🔍 Step 1: Substring match test...")
        old_code_stripped = old_code.strip()
        
        if old_code_stripped in file_content:
            print("✅ Substring match PASSED")
        else:
            print("❌ Substring match FAILED")
            return False
        
        # Step 2: Test uniqueness (this should pass)
        print(f"\n🔍 Step 2: Uniqueness test...")
        count = file_content.count(old_code_stripped)
        print(f"OLD_CODE appears {count} times in file")
        
        if count == 0:
            print("❌ Count is 0 - this shouldn't happen!")
            return False
        elif count > 1:
            print("❌ OLD_CODE appears multiple times - need more context")
            return False
        else:
            print("✅ Uniqueness test PASSED")
        
        # Step 3: Test line boundaries (this is where it might fail)
        print(f"\n🔍 Step 3: Line boundaries test...")
        
        if "\n" in old_code_stripped:
            file_lines = file_content.splitlines()
            old_lines = old_code_stripped.split("\n")
            
            print(f"   File has {len(file_lines)} lines")
            print(f"   OLD_CODE has {len(old_lines)} lines")
            
            found_start = -1
            
            # This is the exact logic from IncrementalModificationValidator
            for i in range(len(file_lines) - len(old_lines) + 1):
                match = True
                
                for j, old_line in enumerate(old_lines):
                    file_line_idx = i + j
                    if file_line_idx >= len(file_lines):
                        match = False
                        break
                    
                    file_line = file_lines[file_line_idx]
                    
                    if file_line != old_line:
                        match = False
                        break
                
                if match:
                    found_start = i
                    break
            
            if found_start == -1:
                print("❌ Line boundaries test FAILED")
                
                # Debug why it failed
                print(f"\n🔍 Debugging line boundaries failure...")
                
                # Show expected vs actual lines
                print(f"Expected lines:")
                for i, old_line in enumerate(old_lines):
                    print(f"  Line {i + 1}: {repr(old_line)}")
                
                # Try to find where each line appears in the file
                print(f"\nSearching for each line in file:")
                for i, old_line in enumerate(old_lines):
                    found_at = []
                    for j, file_line in enumerate(file_lines):
                        if file_line == old_line:
                            found_at.append(j + 1)
                    
                    if found_at:
                        print(f"  Line {i + 1}: Found at file lines {found_at}")
                    else:
                        print(f"  Line {i + 1}: NOT FOUND")
                        
                        # Check for similar lines
                        similar_at = []
                        for j, file_line in enumerate(file_lines):
                            if old_line.strip() == file_line.strip():
                                similar_at.append(j + 1)
                        
                        if similar_at:
                            print(f"    Similar (content match) at file lines {similar_at}")
                            # Show the difference
                            for line_num in similar_at[:1]:  # Show first match
                                file_line = file_lines[line_num - 1]
                                print(f"      Expected: {repr(old_line)}")
                                print(f"      File    : {repr(file_line)}")
                                
                                # Analyze differences
                                if len(old_line) != len(file_line):
                                    print(f"      Length diff: {len(old_line)} vs {len(file_line)}")
                                
                                # Check character by character
                                for k, (c1, c2) in enumerate(zip(old_line, file_line)):
                                    if c1 != c2:
                                        print(f"      First diff at pos {k}: {repr(c1)} vs {repr(c2)}")
                                        break
                
                return False
            else:
                print(f"✅ Line boundaries test PASSED (found at line {found_start + 1})")
        
        print(f"\n✅ All validation tests PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_file_encoding():
    """Check if there are any encoding issues with the file"""
    print("\n🔍 Checking File Encoding")
    print("=" * 30)
    
    file_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
    
    try:
        # Read as binary first
        with open(file_path, 'rb') as f:
            raw_bytes = f.read()
        
        print(f"File size: {len(raw_bytes)} bytes")
        
        # Check for BOM
        if raw_bytes.startswith(b'\xef\xbb\xbf'):
            print("⚠️ File has UTF-8 BOM")
        else:
            print("✅ No BOM detected")
        
        # Check line endings
        has_crlf = b'\r\n' in raw_bytes
        has_lf_only = b'\n' in raw_bytes and not has_crlf
        has_cr_only = b'\r' in raw_bytes and not has_crlf
        
        print(f"Line endings:")
        print(f"  CRLF (\\r\\n): {has_crlf}")
        print(f"  LF only (\\n): {has_lf_only}")
        print(f"  CR only (\\r): {has_cr_only}")
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"✅ {encoding}: {len(content)} chars")
            except UnicodeDecodeError:
                print(f"❌ {encoding}: decode error")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Debugging Validation Logic Issues")
    print("=" * 60)
    
    success = test_validation_logic()
    check_file_encoding()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Validation logic should work - issue might be in agent implementation")
    else:
        print("❌ Found validation issues - this explains the error")


if __name__ == "__main__":
    main()
