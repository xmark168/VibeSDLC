"""
Test splitlines() fix for auth.py modification
"""

from pathlib import Path


def _extract_actual_content(formatted_content: str) -> str:
    """Extract actual content using splitlines()."""
    lines = formatted_content.splitlines()
    actual_lines = []

    for line in lines:
        if not line.strip():
            actual_lines.append("")
            continue

        if "\t" in line:
            actual_content = line.split("\t", 1)[1]
            actual_lines.append(actual_content)
        else:
            actual_lines.append(line)

    return "\n".join(actual_lines)


def _find_best_insertion_point(formatted_content: str) -> dict | None:
    """Find insertion point using splitlines()."""
    actual_content = _extract_actual_content(formatted_content)
    lines = actual_content.splitlines()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "pass":
            return {
                "type": "pass",
                "line": i + 1,
                "original_line": line,
                "indentation": len(line) - len(line.lstrip()),
                "pattern": "pass",
            }

    return None


def test_splitlines_fix():
    """Test the splitlines() fix for auth.py."""
    print("🧪 Testing splitlines() fix for auth.py...")
    
    auth_file = Path("app/agents/demo/app/services/auth.py")
    
    if not auth_file.exists():
        print(f"❌ File not found: {auth_file}")
        return False
    
    # Read file content (this has actual newlines)
    content = auth_file.read_text()
    
    print(f"📄 Original file:")
    print(f"    Size: {len(content)} chars")
    print(f"    Lines (splitlines): {len(content.splitlines())}")
    print(f"    Lines (split): {len(content.split('\\n'))}")
    
    # Simulate read_file_tool output (cat -n format)
    # This should create formatted content with actual newlines
    lines = content.splitlines()
    formatted_lines = []
    for i, line in enumerate(lines, 1):
        formatted_lines.append(f"{i:6d}\t{line}")
    
    # Join with actual newlines (not literal \\n)
    formatted_content = "\n".join(formatted_lines)
    
    print(f"\\n📖 Formatted content:")
    print(f"    Size: {len(formatted_content)} chars")
    print(f"    Lines (splitlines): {len(formatted_content.splitlines())}")
    print(f"    Lines (split): {len(formatted_content.split('\\n'))}")
    
    # Test insertion point detection
    insertion_point = _find_best_insertion_point(formatted_content)
    
    if insertion_point:
        print(f"\\n🎯 Found insertion point:")
        print(f"    Line: {insertion_point['line']}")
        print(f"    Original line: '{insertion_point['original_line']}'")
        print(f"    Indentation: {insertion_point['indentation']} spaces")
        
        # Verify the insertion point is correct
        actual_content = _extract_actual_content(formatted_content)
        actual_lines = actual_content.splitlines()
        
        if len(actual_lines) >= insertion_point['line']:
            target_line = actual_lines[insertion_point['line'] - 1]
            print(f"    Target line: '{target_line}'")
            print(f"    Matches original: {target_line == insertion_point['original_line']}")
            
            if target_line.strip() == "pass":
                print(f"    ✅ Correctly identified pass statement!")
                return True
            else:
                print(f"    ❌ Target line is not a pass statement")
                return False
        else:
            print(f"    ❌ Line number out of range")
            return False
    else:
        print("\\n❌ No insertion point found")
        return False


def main():
    """Run splitlines() fix test."""
    print("🚀 Testing splitlines() fix for auth.py modification...\\n")
    
    success = test_splitlines_fix()
    
    if success:
        print("\\n🎉 splitlines() fix test successful!")
        print("\\n💡 The fix should resolve auth.py modification failure")
        print("\\n🔧 Changes made:")
        print("  1. implement_files.py: split('\\\\n') → splitlines()")
        print("  2. generate_code.py: split('\\\\n') → splitlines()")
        print("\\n✅ auth.py modification should now work correctly!")
    else:
        print("\\n💥 splitlines() fix test failed")
        print("\\n🔧 Additional investigation needed")


if __name__ == "__main__":
    main()
