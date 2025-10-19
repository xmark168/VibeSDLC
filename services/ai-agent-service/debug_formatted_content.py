"""
Debug formatted content creation
"""


def debug_formatted_content():
    """Debug how formatted content is created."""
    print("🧪 Debugging formatted content creation...")
    
    test_content = '''class TestService:
    """Test service."""
    
    def test_method(self):
        pass'''
    
    print(f"📄 Original content:")
    print(f"    Length: {len(test_content)} chars")
    print(f"    Lines: {len(test_content.split('\\n'))}")
    print(f"    Content: {repr(test_content)}")
    
    # Method 1: Using split("\\n") and join("\\n")
    lines = test_content.split("\\n")
    formatted_lines = []
    for i, line in enumerate(lines, 1):
        formatted_lines.append(f"{i:6d}\\t{line}")
    formatted_content_1 = "\\n".join(formatted_lines)
    
    print(f"\\n📖 Method 1 (split + join with \\\\n):")
    print(f"    Original lines: {len(lines)}")
    print(f"    Formatted lines: {len(formatted_lines)}")
    print(f"    Formatted content length: {len(formatted_content_1)}")
    print(f"    Formatted content repr: {repr(formatted_content_1[:100])}...")
    
    # Test parsing back
    parsed_lines_1 = formatted_content_1.split("\\n")
    print(f"    Parsed back lines: {len(parsed_lines_1)}")
    
    # Method 2: Using splitlines() and join with actual newlines
    lines_2 = test_content.splitlines()
    formatted_lines_2 = []
    for i, line in enumerate(lines_2, 1):
        formatted_lines_2.append(f"{i:6d}\\t{line}")
    formatted_content_2 = "\\n".join(formatted_lines_2)
    
    print(f"\\n📖 Method 2 (splitlines + join with \\\\n):")
    print(f"    Original lines: {len(lines_2)}")
    print(f"    Formatted lines: {len(formatted_lines_2)}")
    print(f"    Formatted content length: {len(formatted_content_2)}")
    print(f"    Formatted content repr: {repr(formatted_content_2[:100])}...")
    
    # Test parsing back
    parsed_lines_2 = formatted_content_2.split("\\n")
    print(f"    Parsed back lines: {len(parsed_lines_2)}")
    
    # Method 3: Using actual newline characters
    lines_3 = test_content.split("\\n")
    formatted_lines_3 = []
    for i, line in enumerate(lines_3, 1):
        formatted_lines_3.append(f"{i:6d}\\t{line}")
    formatted_content_3 = "\\n".join(formatted_lines_3)  # This creates actual newlines
    
    print(f"\\n📖 Method 3 (actual newlines):")
    print(f"    Original lines: {len(lines_3)}")
    print(f"    Formatted lines: {len(formatted_lines_3)}")
    print(f"    Formatted content length: {len(formatted_content_3)}")
    print(f"    Formatted content repr: {repr(formatted_content_3[:100])}...")
    
    # Test parsing back with split
    parsed_lines_3a = formatted_content_3.split("\\n")
    print(f"    Parsed back with split('\\\\n'): {len(parsed_lines_3a)}")
    
    # Test parsing back with splitlines
    parsed_lines_3b = formatted_content_3.splitlines()
    print(f"    Parsed back with splitlines(): {len(parsed_lines_3b)}")
    
    # Show the difference
    print(f"\\n🔍 Comparison:")
    print(f"    Method 1 == Method 2: {formatted_content_1 == formatted_content_2}")
    print(f"    Method 1 == Method 3: {formatted_content_1 == formatted_content_3}")
    print(f"    Method 2 == Method 3: {formatted_content_2 == formatted_content_3}")
    
    # Check what's actually in the strings
    print(f"\\n🔍 Character analysis:")
    print(f"    Method 1 contains \\\\n: {'\\\\n' in formatted_content_1}")
    print(f"    Method 1 contains actual newline: {'\\n' in formatted_content_1}")
    print(f"    Method 3 contains \\\\n: {'\\\\n' in formatted_content_3}")
    print(f"    Method 3 contains actual newline: {'\\n' in formatted_content_3}")


def main():
    """Run formatted content debug."""
    print("🚀 Debugging formatted content creation...\\n")
    
    debug_formatted_content()
    
    print("\\n🎉 Debug completed!")


if __name__ == "__main__":
    main()
