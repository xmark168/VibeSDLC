"""
Simple debug of auth.py content
"""

from pathlib import Path


def debug_auth_content():
    """Debug auth.py content to find why insertion point is not found."""
    print("🧪 Debugging auth.py content...")
    
    auth_file = Path("app/agents/demo/app/services/auth.py")
    
    if not auth_file.exists():
        print(f"❌ File not found: {auth_file}")
        return False
    
    # Read file content
    content = auth_file.read_text()
    lines = content.split("\\n")
    
    print(f"📄 File size: {len(content)} chars")
    print(f"📄 Number of lines: {len(lines)}")
    
    # Look for lines containing "pass"
    pass_lines = []
    for i, line in enumerate(lines):
        if "pass" in line:
            pass_lines.append((i + 1, line))
    
    print(f"\\n🔍 Found {len(pass_lines)} lines containing 'pass':")
    for line_num, line in pass_lines:
        print(f"    Line {line_num:3d}: '{line}'")
        print(f"                 Stripped: '{line.strip()}'")
        print(f"                 Is exactly 'pass': {line.strip() == 'pass'}")
        print(f"                 Repr: {repr(line)}")
        print()
    
    # Check specifically around line 169 (where we expect the pass statement)
    print("🔍 Checking around line 169:")
    for i in range(165, min(175, len(lines))):
        line = lines[i]
        print(f"    Line {i+1:3d}: '{line}' (stripped: '{line.strip()}')")
    
    # Check for the exact pass statement we expect
    expected_pass_line = "        pass"
    if expected_pass_line in content:
        print(f"\\n✅ Found expected pass line: '{expected_pass_line}'")
        count = content.count(expected_pass_line)
        print(f"    Occurrences: {count}")
    else:
        print(f"\\n❌ Expected pass line not found: '{expected_pass_line}'")
        
        # Look for similar lines
        print("    Looking for similar lines:")
        for i, line in enumerate(lines):
            if line.strip() == "pass":
                print(f"        Line {i+1}: '{line}' (repr: {repr(line)})")
    
    return True


def main():
    """Run simple auth.py debug."""
    print("🚀 Simple auth.py content debug...\\n")
    
    success = debug_auth_content()
    
    if success:
        print("\\n🎉 Debug completed!")
    else:
        print("\\n💥 Debug failed")


if __name__ == "__main__":
    main()
