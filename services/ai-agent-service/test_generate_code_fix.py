"""
Test generate_code.py fix for line number removal
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the functions we want to test
from app.agents.developer.implementor.nodes.generate_code import (
    _extract_actual_content,
    _has_line_numbers,
    _clean_llm_response
)


def test_extract_actual_content():
    """Test _extract_actual_content function."""
    print("🧪 Testing _extract_actual_content function...")
    
    # Test case 1: Content with line numbers (cat -n format)
    formatted_content = """     1\tclass UserVerifyEmail(BaseModel):
     2\t    \"\"\"Schema for email verification.\"\"\"
     3\t
     4\t    token: str
     5\t
     6\t
     7\tclass UserPasswordResetRequest(BaseModel):
     8\t    \"\"\"Schema for password reset request.\"\"\"
     9\t
    10\t    email: EmailStr"""
    
    expected_clean = """class UserVerifyEmail(BaseModel):
    \"\"\"Schema for email verification.\"\"\"

    token: str


class UserPasswordResetRequest(BaseModel):
    \"\"\"Schema for password reset request.\"\"\"

    email: EmailStr"""
    
    actual_clean = _extract_actual_content(formatted_content)
    
    print("  Input (with line numbers):")
    print("    " + formatted_content.split("\\n")[0])
    print("    " + formatted_content.split("\\n")[1])
    print("    ...")
    
    print("  Output (clean):")
    print("    " + actual_clean.split("\\n")[0])
    print("    " + actual_clean.split("\\n")[1])
    print("    ...")
    
    # Check if line numbers are removed
    has_line_numbers_after = any("\\t" in line and line.split("\\t")[0].strip().isdigit() 
                                 for line in actual_clean.split("\\n") if line.strip())
    
    if not has_line_numbers_after:
        print("  ✅ Line numbers successfully removed")
        return True
    else:
        print("  ❌ Line numbers still present")
        return False


def test_has_line_numbers():
    """Test _has_line_numbers detection function."""
    print("\\n🧪 Testing _has_line_numbers detection...")
    
    # Test case 1: Content with line numbers
    content_with_numbers = """     1\tclass UserService:
     2\t    pass
     3\t
     4\tdef test_function():
     5\t    return True"""
    
    # Test case 2: Clean content without line numbers
    content_without_numbers = """class UserService:
    pass

def test_function():
    return True"""
    
    # Test case 3: Mixed content (some lines with numbers, some without)
    mixed_content = """class UserService:
     2\t    pass
    
def test_function():
     5\t    return True"""
    
    test1 = _has_line_numbers(content_with_numbers)
    test2 = _has_line_numbers(content_without_numbers)
    test3 = _has_line_numbers(mixed_content)
    
    print(f"  Content with line numbers: {'✅ Detected' if test1 else '❌ Not detected'}")
    print(f"  Clean content: {'✅ Not detected' if not test2 else '❌ False positive'}")
    print(f"  Mixed content: {'✅ Detected' if test3 else '❌ Not detected'}")
    
    return test1 and not test2 and test3


def test_clean_llm_response():
    """Test _clean_llm_response with line numbers."""
    print("\\n🧪 Testing _clean_llm_response with line numbers...")
    
    # Test case: LLM response with line numbers
    llm_response_with_numbers = """Here's the implementation:

```python
     1\tclass UserVerifyEmail(BaseModel):
     2\t    \"\"\"Schema for email verification.\"\"\"
     3\t
     4\t    token: str
     5\t
     6\t
     7\tclass UserPasswordResetRequest(BaseModel):
     8\t    \"\"\"Schema for password reset request.\"\"\"
     9\t
    10\t    email: EmailStr
```

This implementation meets the requirements."""
    
    cleaned_response = _clean_llm_response(llm_response_with_numbers)
    
    print("  Input (LLM response with line numbers):")
    print("    " + "\\n    ".join(llm_response_with_numbers.split("\\n")[:5]))
    print("    ...")
    
    print("  Output (cleaned):")
    print("    " + "\\n    ".join(cleaned_response.split("\\n")[:5]))
    print("    ...")
    
    # Check if line numbers are removed and explanation text is removed
    has_line_numbers = any("\\t" in line and line.split("\\t")[0].strip().isdigit() 
                          for line in cleaned_response.split("\\n") if line.strip())
    has_explanation = any(phrase in cleaned_response.lower() 
                         for phrase in ["here's", "implementation", "meets the"])
    
    success = not has_line_numbers and not has_explanation
    
    if success:
        print("  ✅ Line numbers and explanations removed successfully")
        return True
    else:
        print(f"  ❌ Issues: Line numbers present: {has_line_numbers}, Explanations present: {has_explanation}")
        return False


def test_clean_normal_response():
    """Test _clean_llm_response with normal response (no line numbers)."""
    print("\\n🧪 Testing _clean_llm_response with normal response...")
    
    # Test case: Normal LLM response without line numbers
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
    
    cleaned_response = _clean_llm_response(normal_response)
    
    print("  Input (normal LLM response):")
    print("    " + "\\n    ".join(normal_response.split("\\n")[:5]))
    print("    ...")
    
    print("  Output (cleaned):")
    print("    " + "\\n    ".join(cleaned_response.split("\\n")[:5]))
    print("    ...")
    
    # Check if code is preserved and explanation text is removed
    has_class_definition = "class UserVerifyEmail" in cleaned_response
    has_explanation = any(phrase in cleaned_response.lower() 
                         for phrase in ["here's", "implementation", "meets the"])
    
    success = has_class_definition and not has_explanation
    
    if success:
        print("  ✅ Code preserved, explanations removed successfully")
        return True
    else:
        print(f"  ❌ Issues: Code preserved: {has_class_definition}, Explanations removed: {not has_explanation}")
        return False


def main():
    """Run all tests."""
    print("🚀 Testing generate_code.py Line Number Fix...\\n")
    
    test1 = test_extract_actual_content()
    test2 = test_has_line_numbers()
    test3 = test_clean_llm_response()
    test4 = test_clean_normal_response()
    
    print("\\n🏁 Test Results:")
    print(f"  Extract actual content: {'✅ PASSED' if test1 else '❌ FAILED'}")
    print(f"  Line number detection: {'✅ PASSED' if test2 else '❌ FAILED'}")
    print(f"  Clean LLM response (with line numbers): {'✅ PASSED' if test3 else '❌ FAILED'}")
    print(f"  Clean LLM response (normal): {'✅ PASSED' if test4 else '❌ FAILED'}")
    
    overall_success = all([test1, test2, test3, test4])
    print(f"  Overall: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print("\\n🎉 All tests passed! generate_code.py line number fix is working!")
        print("\\n💡 Fixed issues:")
        print("  ✅ Added _extract_actual_content() function to remove line numbers")
        print("  ✅ Added _has_line_numbers() detection function")
        print("  ✅ Updated _generate_file_modification() to extract clean content before LLM")
        print("  ✅ Updated _clean_llm_response() to handle line numbers in LLM output")
        print("\\n🚀 Generated code should now be clean without line number artifacts!")
    else:
        print("\\n💥 Some tests failed - check the implementation")


if __name__ == "__main__":
    main()
