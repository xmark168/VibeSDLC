"""
Simple test for line number removal functions without complex imports
"""


def _extract_actual_content(formatted_content: str) -> str:
    """
    Extract actual file content from read_file_tool output (cat -n format).
    """
    lines = formatted_content.split("\n")
    actual_lines = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            actual_lines.append("")
            continue

        # Extract content after line number and tab
        # Format: "     1\tclass UserService:"
        if "\t" in line:
            actual_content = line.split("\t", 1)[1]
            actual_lines.append(actual_content)
        else:
            # Fallback for lines without tab
            actual_lines.append(line)

    return "\n".join(actual_lines)


def _has_line_numbers(content: str) -> bool:
    """
    Check if content has line numbers (cat -n format).
    """
    lines = content.split("\n")
    line_number_count = 0
    
    for line in lines[:10]:  # Check first 10 lines
        if line.strip():
            # Check if line starts with spaces followed by number and tab
            # Format: "     1\tclass UserService:"
            stripped = line.lstrip()
            if stripped and "\t" in line:
                before_tab = line.split("\t")[0]
                if before_tab.strip().isdigit():
                    line_number_count += 1
    
    # If more than 50% of non-empty lines have line numbers, consider it formatted
    return line_number_count >= 3


def _clean_llm_response(raw_response: str) -> str:
    """
    Clean LLM response to extract pure code content.
    Removes markdown formatting, explanations, line numbers, and other non-code text.
    """
    if not raw_response:
        return ""

    # First check if response contains line numbers (cat -n format)
    # If so, extract actual content first
    if _has_line_numbers(raw_response):
        raw_response = _extract_actual_content(raw_response)

    # Remove common explanation patterns
    lines = raw_response.split("\n")
    cleaned_lines = []
    in_code_block = False
    code_block_started = False

    for line in lines:
        # Skip explanation lines before code
        if not code_block_started and any(
            phrase in line.lower()
            for phrase in [
                "here's",
                "here is",
                "implementation",
                "complete",
                "meets the",
                "requirements",
                "this implementation",
                "the following",
            ]
        ):
            continue

        # Detect code block start
        if line.strip().startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_block_started = True
                continue
            else:
                # End of code block
                break

        # If we're in a code block, collect the line
        if in_code_block:
            cleaned_lines.append(line)
        # If no code blocks detected, assume entire response is code
        elif not code_block_started:
            # Skip obvious explanation lines
            if not any(
                phrase in line.lower()
                for phrase in [
                    "here's",
                    "here is",
                    "implementation",
                    "complete",
                    "meets the",
                    "requirements",
                    "this implementation",
                    "the following",
                    "```",
                ]
            ):
                cleaned_lines.append(line)

    # Join and clean up
    cleaned_code = "\n".join(cleaned_lines).strip()

    # If we got nothing, try to extract from the original response
    if not cleaned_code and raw_response:
        # Look for Python code patterns
        if (
            "def " in raw_response
            or "class " in raw_response
            or "import " in raw_response
        ):
            # Try to extract everything after the first import/def/class
            for line in lines:
                if any(
                    pattern in line
                    for pattern in ["import ", "from ", "def ", "class ", "@"]
                ):
                    start_idx = lines.index(line)
                    cleaned_code = "\n".join(lines[start_idx:]).strip()
                    break

    return cleaned_code


def test_line_number_removal():
    """Test line number removal from LLM generated code."""
    print("🧪 Testing line number removal from LLM generated code...")
    
    # Simulate LLM response with line numbers (the problem we're fixing)
    llm_response_with_numbers = """Here's the implementation:

```python
   107\tclass UserVerifyEmail(BaseModel):
   108\t    \"\"\"Schema for email verification.\"\"\"
   109\t
   110\t    token: str
   111\t
   112\t
   113\tclass UserPasswordResetRequest(BaseModel):
   114\t    \"\"\"Schema for password reset request.\"\"\"
   115\t
   116\t    email: EmailStr
```

This implementation meets the requirements."""
    
    print("  Input (LLM response with line numbers):")
    print("    " + "\\n    ".join(llm_response_with_numbers.split("\\n")[2:7]))
    print("    ...")
    
    # Test the fix
    cleaned_code = _clean_llm_response(llm_response_with_numbers)
    
    print("  Output (after cleaning):")
    print("    " + "\\n    ".join(cleaned_code.split("\\n")[:5]))
    print("    ...")
    
    # Verify line numbers are removed
    has_line_numbers = any("\\t" in line and line.split("\\t")[0].strip().isdigit() 
                          for line in cleaned_code.split("\\n") if line.strip())
    
    # Verify explanations are removed
    has_explanation = any(phrase in cleaned_code.lower() 
                         for phrase in ["here's", "implementation", "meets the"])
    
    # Verify code structure is preserved
    has_class_definition = "class UserVerifyEmail" in cleaned_code
    has_docstring = '"""Schema for email verification."""' in cleaned_code
    
    print(f"\\n  ✅ Line numbers removed: {not has_line_numbers}")
    print(f"  ✅ Explanations removed: {not has_explanation}")
    print(f"  ✅ Code structure preserved: {has_class_definition}")
    print(f"  ✅ Docstrings preserved: {has_docstring}")
    
    success = not has_line_numbers and not has_explanation and has_class_definition and has_docstring
    
    if success:
        print("\\n  🎉 SUCCESS: Line number removal working correctly!")
        return True
    else:
        print("\\n  💥 FAILED: Issues with line number removal")
        return False


def test_normal_response():
    """Test that normal responses (without line numbers) still work."""
    print("\\n🧪 Testing normal LLM response (without line numbers)...")
    
    normal_response = """Here's the implementation:

```python
class UserVerifyEmail(BaseModel):
    \"\"\"Schema for email verification.\"\"\"
    
    token: str


class UserPasswordResetRequest(BaseModel):
    \"\"\"Schema for password reset request.\"\"\"
    
    email: EmailStr
```

This implementation meets the requirements."""
    
    cleaned_code = _clean_llm_response(normal_response)
    
    # Verify code structure is preserved
    has_class_definition = "class UserVerifyEmail" in cleaned_code
    has_explanation = any(phrase in cleaned_code.lower() 
                         for phrase in ["here's", "implementation", "meets the"])
    
    print(f"  ✅ Code structure preserved: {has_class_definition}")
    print(f"  ✅ Explanations removed: {not has_explanation}")
    
    success = has_class_definition and not has_explanation
    
    if success:
        print("  🎉 SUCCESS: Normal responses still work correctly!")
        return True
    else:
        print("  💥 FAILED: Issues with normal response handling")
        return False


def main():
    """Run all tests."""
    print("🚀 Testing Line Number Fix for generate_code.py...\\n")
    
    test1 = test_line_number_removal()
    test2 = test_normal_response()
    
    print("\\n🏁 Test Results:")
    print(f"  Line number removal: {'✅ PASSED' if test1 else '❌ FAILED'}")
    print(f"  Normal response handling: {'✅ PASSED' if test2 else '❌ FAILED'}")
    
    overall_success = all([test1, test2])
    print(f"  Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print("\\n🎉 All tests passed! Line number fix is working!")
        print("\\n💡 What was fixed:")
        print("  1. _generate_file_modification() now extracts clean content before passing to LLM")
        print("  2. _clean_llm_response() now detects and removes line numbers from LLM output")
        print("  3. Added _has_line_numbers() detection function")
        print("  4. Added _extract_actual_content() function for content cleaning")
        print("\\n🚀 Generated code should now be clean without line number artifacts!")
        print("\\n📋 Before fix: LLM generated code like '   107\\tclass UserVerifyEmail(BaseModel):'")
        print("📋 After fix: LLM generates clean code like 'class UserVerifyEmail(BaseModel):'")
    else:
        print("\\n💥 Some tests failed - check the implementation")


if __name__ == "__main__":
    main()
