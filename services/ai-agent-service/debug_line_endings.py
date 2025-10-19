"""
Debug line endings in auth.py
"""

from pathlib import Path


def debug_line_endings():
    """Debug line endings in auth.py file."""
    print("🧪 Debugging line endings in auth.py...")
    
    auth_file = Path("app/agents/demo/app/services/auth.py")
    
    if not auth_file.exists():
        print(f"❌ File not found: {auth_file}")
        return False
    
    # Read file as bytes to check line endings
    content_bytes = auth_file.read_bytes()
    content_text = auth_file.read_text()
    
    print(f"📄 File size (bytes): {len(content_bytes)}")
    print(f"📄 File size (text): {len(content_text)}")
    
    # Check for different line ending types
    crlf_count = content_bytes.count(b'\\r\\n')
    lf_count = content_bytes.count(b'\\n') - crlf_count  # Subtract CRLF occurrences
    cr_count = content_bytes.count(b'\\r') - crlf_count  # Subtract CRLF occurrences
    
    print(f"\\n🔍 Line ending analysis:")
    print(f"    CRLF (\\\\r\\\\n): {crlf_count}")
    print(f"    LF (\\\\n): {lf_count}")
    print(f"    CR (\\\\r): {cr_count}")
    
    # Check what Python sees when splitting lines
    lines_split_n = content_text.split('\\n')
    lines_split_rn = content_text.split('\\r\\n')
    lines_splitlines = content_text.splitlines()
    
    print(f"\\n📄 Line splitting results:")
    print(f"    split('\\\\n'): {len(lines_split_n)} lines")
    print(f"    split('\\\\r\\\\n'): {len(lines_split_rn)} lines")
    print(f"    splitlines(): {len(lines_splitlines)} lines")
    
    # Show first few lines to see the structure
    print(f"\\n📄 First 5 lines using splitlines():")
    for i, line in enumerate(lines_splitlines[:5]):
        print(f"    Line {i+1}: '{line[:50]}{'...' if len(line) > 50 else ''}'")
    
    # Check around line 169
    if len(lines_splitlines) >= 169:
        print(f"\\n🔍 Around line 169:")
        for i in range(165, min(175, len(lines_splitlines))):
            line = lines_splitlines[i]
            print(f"    Line {i+1:3d}: '{line}' (stripped: '{line.strip()}')")
            if line.strip() == "pass":
                print(f"                 ✅ Found pass statement!")
    else:
        print(f"\\n❌ File only has {len(lines_splitlines)} lines, expected 186")
    
    return True


def main():
    """Run line endings debug."""
    print("🚀 Debugging line endings in auth.py...\\n")
    
    success = debug_line_endings()
    
    if success:
        print("\\n🎉 Line endings debug completed!")
    else:
        print("\\n💥 Line endings debug failed")


if __name__ == "__main__":
    main()
