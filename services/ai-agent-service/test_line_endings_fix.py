"""
Test line endings fix for auth.py modification
"""

from pathlib import Path


def _extract_actual_content_old(formatted_content: str) -> str:
    """Old version using split('\\n')."""
    lines = formatted_content.split("\\n")
    actual_lines = []

    for line in lines:
        if not line.strip():
            actual_lines.append("")
            continue

        if "\\t" in line:
            actual_content = line.split("\\t", 1)[1]
            actual_lines.append(actual_content)
        else:
            actual_lines.append(line)

    return "\\n".join(actual_lines)


def _extract_actual_content_new(formatted_content: str) -> str:
    """New version using splitlines()."""
    lines = formatted_content.splitlines()
    actual_lines = []

    for line in lines:
        if not line.strip():
            actual_lines.append("")
            continue

        if "\\t" in line:
            actual_content = line.split("\\t", 1)[1]
            actual_lines.append(actual_content)
        else:
            actual_lines.append(line)

    return "\\n".join(actual_lines)


def _find_best_insertion_point_old(formatted_content: str) -> dict | None:
    """Old version using split('\\n')."""
    actual_content = _extract_actual_content_old(formatted_content)
    lines = actual_content.split("\\n")

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


def _find_best_insertion_point_new(formatted_content: str) -> dict | None:
    """New version using splitlines()."""
    actual_content = _extract_actual_content_new(formatted_content)
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


def test_line_endings_fix():
    """Test the line endings fix for auth.py."""
    print("🧪 Testing line endings fix for auth.py...")
    
    auth_file = Path("app/agents/demo/app/services/auth.py")
    
    if not auth_file.exists():
        print(f"❌ File not found: {auth_file}")
        return False
    
    # Read file content
    content = auth_file.read_text()
    
    # Simulate formatted content (cat -n)
    lines = content.splitlines()
    formatted_lines = []
    for i, line in enumerate(lines, 1):
        formatted_lines.append(f"{i:6d}\\t{line}")
    formatted_content = "\\n".join(formatted_lines)
    
    print(f"📄 Original file lines: {len(lines)}")
    print(f"📄 Formatted content size: {len(formatted_content)}")
    
    # Test old version (should fail)
    print("\\n🧪 Testing OLD version (split('\\\\n')):")
    try:
        insertion_point_old = _find_best_insertion_point_old(formatted_content)
        if insertion_point_old:
            print(f"    ✅ Found insertion point: line {insertion_point_old['line']}")
            print(f"    Original line: '{insertion_point_old['original_line']}'")
        else:
            print("    ❌ No insertion point found")
    except Exception as e:
        print(f"    ❌ Error: {e}")
    
    # Test new version (should work)
    print("\\n🧪 Testing NEW version (splitlines()):")
    try:
        insertion_point_new = _find_best_insertion_point_new(formatted_content)
        if insertion_point_new:
            print(f"    ✅ Found insertion point: line {insertion_point_new['line']}")
            print(f"    Original line: '{insertion_point_new['original_line']}'")
            print(f"    Indentation: {insertion_point_new['indentation']} spaces")
        else:
            print("    ❌ No insertion point found")
    except Exception as e:
        print(f"    ❌ Error: {e}")
    
    # Compare results
    print("\\n📊 Comparison:")
    if insertion_point_old and insertion_point_new:
        print("    ✅ Both versions found insertion point")
        if insertion_point_old['line'] == insertion_point_new['line']:
            print("    ✅ Same line number")
        else:
            print(f"    ⚠️ Different line numbers: {insertion_point_old['line']} vs {insertion_point_new['line']}")
    elif insertion_point_new and not insertion_point_old:
        print("    🎉 NEW version fixed the issue!")
        print("    ✅ splitlines() successfully handles special line endings")
    elif insertion_point_old and not insertion_point_new:
        print("    ❌ NEW version broke something")
    else:
        print("    ❌ Both versions failed")
    
    return insertion_point_new is not None


def main():
    """Run line endings fix test."""
    print("🚀 Testing line endings fix for auth.py modification...\\n")
    
    success = test_line_endings_fix()
    
    if success:
        print("\\n🎉 Line endings fix test successful!")
        print("\\n💡 The fix should resolve auth.py modification failure")
        print("\\n🔧 Changes made:")
        print("  1. implement_files.py: split('\\\\n') → splitlines()")
        print("  2. generate_code.py: split('\\\\n') → splitlines()")
        print("\\n✅ auth.py modification should now work correctly!")
    else:
        print("\\n💥 Line endings fix test failed")
        print("\\n🔧 Additional investigation needed")


if __name__ == "__main__":
    main()
