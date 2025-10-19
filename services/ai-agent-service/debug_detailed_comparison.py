"""
Detailed debug comparison between split() and splitlines()
"""

from pathlib import Path


def debug_detailed_comparison():
    """Debug detailed comparison between split() and splitlines()."""
    print("🧪 Detailed debug comparison...")
    
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
    
    # Test split("\\n") vs splitlines() on formatted content
    print("\\n🔍 Testing formatted content parsing:")
    
    lines_split = formatted_content.split("\\n")
    lines_splitlines = formatted_content.splitlines()
    
    print(f"    split('\\\\n'): {len(lines_split)} lines")
    print(f"    splitlines(): {len(lines_splitlines)} lines")
    
    # Check if they're the same
    if lines_split == lines_splitlines:
        print("    ✅ Both methods produce identical results")
    else:
        print("    ⚠️ Different results!")
        
        # Show differences
        max_lines = max(len(lines_split), len(lines_splitlines))
        for i in range(min(10, max_lines)):  # Show first 10 differences
            split_line = lines_split[i] if i < len(lines_split) else "<MISSING>"
            splitlines_line = lines_splitlines[i] if i < len(lines_splitlines) else "<MISSING>"
            
            if split_line != splitlines_line:
                print(f"    Line {i+1}:")
                print(f"        split(): '{split_line[:50]}{'...' if len(split_line) > 50 else ''}'")
                print(f"        splitlines(): '{splitlines_line[:50]}{'...' if len(splitlines_line) > 50 else ''}'")
    
    # Test actual content extraction
    print("\\n🔍 Testing actual content extraction:")
    
    def extract_old(formatted_content):
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
    
    def extract_new(formatted_content):
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
    
    actual_old = extract_old(formatted_content)
    actual_new = extract_new(formatted_content)
    
    print(f"    Old method lines: {len(actual_old.split('\\n'))}")
    print(f"    New method lines: {len(actual_new.splitlines())}")
    
    # Check around line 169
    old_lines = actual_old.split("\\n")
    new_lines = actual_new.splitlines()
    
    print("\\n🔍 Checking around line 169:")
    
    if len(old_lines) >= 169:
        print(f"    Old method line 169: '{old_lines[168]}' (stripped: '{old_lines[168].strip()}')")
        print(f"    Is pass: {old_lines[168].strip() == 'pass'}")
    else:
        print(f"    Old method: Only {len(old_lines)} lines")
    
    if len(new_lines) >= 169:
        print(f"    New method line 169: '{new_lines[168]}' (stripped: '{new_lines[168].strip()}')")
        print(f"    Is pass: {new_lines[168].strip() == 'pass'}")
    else:
        print(f"    New method: Only {len(new_lines)} lines")
    
    # Find all pass statements
    print("\\n🔍 Finding all pass statements:")
    
    print("    Old method:")
    for i, line in enumerate(old_lines):
        if line.strip() == "pass":
            print(f"        Line {i+1}: '{line}'")
    
    print("    New method:")
    for i, line in enumerate(new_lines):
        if line.strip() == "pass":
            print(f"        Line {i+1}: '{line}'")
    
    return True


def main():
    """Run detailed debug comparison."""
    print("🚀 Detailed debug comparison between split() and splitlines()...\\n")
    
    success = debug_detailed_comparison()
    
    if success:
        print("\\n🎉 Detailed debug completed!")
    else:
        print("\\n💥 Detailed debug failed")


if __name__ == "__main__":
    main()
