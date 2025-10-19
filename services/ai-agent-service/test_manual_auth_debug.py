"""
Manual debug of auth.py insertion point
"""

from pathlib import Path


def _extract_actual_content(formatted_content: str) -> str:
    """Extract actual content from read_file_tool output."""
    lines = formatted_content.split("\n")
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


def simulate_read_file_tool(file_path):
    """Simulate read_file_tool output with line numbers."""
    content = file_path.read_text()
    lines = content.split("\n")
    formatted_lines = []
    
    for i, line in enumerate(lines, 1):
        formatted_lines.append(f"{i:6d}\t{line}")
    
    return "\n".join(formatted_lines)


def _find_best_insertion_point(formatted_content: str) -> dict | None:
    """Find insertion point in auth.py content."""
    actual_content = _extract_actual_content(formatted_content)
    lines = actual_content.split("\n")

    insertion_patterns = [
        {"pattern": "pass", "type": "pass"},
        {"pattern": "# TODO: Implement", "type": "todo_implement"},
        {"pattern": "# TODO", "type": "todo"},
        {"pattern": "...", "type": "ellipsis"},
    ]

    for i, line in enumerate(lines):
        stripped = line.strip()

        for pattern_info in insertion_patterns:
            pattern = pattern_info["pattern"]
            
            if pattern == "pass":
                # Check if line is exactly "pass" (standalone)
                if stripped == "pass" or (
                    stripped.startswith("pass ") and "#" in stripped
                ):
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern,
                    }

    return None


def test_manual_auth_debug():
    """Manually debug auth.py insertion point."""
    print("🧪 Manual debug of auth.py insertion point...")
    
    # Read actual auth.py file
    auth_file = Path("app/agents/demo/app/services/auth.py")
    
    if not auth_file.exists():
        print(f"❌ File not found: {auth_file}")
        return False
    
    print(f"📄 Reading file: {auth_file}")
    print(f"📄 File size: {auth_file.stat().st_size} bytes")
    
    # Simulate read_file_tool output
    formatted_content = simulate_read_file_tool(auth_file)
    
    print(f"📖 Formatted content length: {len(formatted_content)}")
    print("📖 First 10 lines of formatted content:")
    for line in formatted_content.split("\\n")[:10]:
        print(f"    {line}")
    print("    ...")
    
    # Extract actual content
    actual_content = _extract_actual_content(formatted_content)
    
    print(f"\\n📄 Actual content length: {len(actual_content)}")
    print("📄 Lines containing 'pass':")
    
    lines = actual_content.split("\\n")
    pass_lines = []
    
    for i, line in enumerate(lines):
        if "pass" in line:
            pass_lines.append((i + 1, line))
            print(f"    Line {i+1:3d}: '{line}' (stripped: '{line.strip()}')")
    
    print(f"\\n🔍 Found {len(pass_lines)} lines containing 'pass'")
    
    # Find insertion point
    insertion_point = _find_best_insertion_point(formatted_content)
    
    if insertion_point:
        print(f"\\n🎯 Found insertion point:")
        print(f"    Type: {insertion_point['type']}")
        print(f"    Line: {insertion_point['line']}")
        print(f"    Original line: '{insertion_point['original_line']}'")
        print(f"    Original line repr: {repr(insertion_point['original_line'])}")
        print(f"    Indentation: {insertion_point['indentation']} spaces")
        print(f"    Pattern: '{insertion_point['pattern']}'")
        
        # Check if this line exists exactly in actual content
        old_str = insertion_point["original_line"]
        count = actual_content.count(old_str)
        
        print(f"\\n🔍 Checking old_str in actual content:")
        print(f"    old_str: '{old_str}'")
        print(f"    old_str repr: {repr(old_str)}")
        print(f"    Occurrences: {count}")
        
        if count == 0:
            print("    ❌ old_str not found in actual content!")
            
            # Find similar lines
            print("    🔍 Looking for similar lines:")
            for i, line in enumerate(lines):
                if line.strip() == "pass":
                    print(f"        Line {i+1}: '{line}' (repr: {repr(line)})")
                    
        elif count > 1:
            print("    ⚠️ Multiple occurrences found!")
            
            # Show all matches
            start = 0
            for _ in range(count):
                pos = actual_content.find(old_str, start)
                if pos != -1:
                    line_num = actual_content[:pos].count("\\n") + 1
                    print(f"        Match at position {pos}, line ~{line_num}")
                    start = pos + 1
        else:
            print("    ✅ Exactly one occurrence found - this should work!")
            
        return True
        
    else:
        print("\\n❌ No insertion point found")
        
        # Check why no insertion point was found
        print("\\n🔍 Debugging insertion point detection:")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "pass":
                print(f"    Line {i+1} has stripped == 'pass': '{line}'")
                print(f"    Line repr: {repr(line)}")
                
        return False


def main():
    """Run manual auth.py debug."""
    print("🚀 Manual debugging of auth.py insertion point...\\n")
    
    success = test_manual_auth_debug()
    
    if success:
        print("\\n🎉 Manual debug completed!")
        print("\\n💡 Insertion point detection should work correctly")
    else:
        print("\\n💥 Manual debug found issues!")
        print("\\n🔧 Check insertion point detection logic")


if __name__ == "__main__":
    main()
