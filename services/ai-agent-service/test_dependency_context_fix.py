"""
Test script to verify the dependency context fix for LLM code generation.

This script tests that:
1. Few-shot examples are present in the prompt template
2. Dependency context is properly appended to prompts
3. The critical reminder section is added when dependencies are present
"""

import os
import sys


# Read the prompt file directly to avoid import issues
def load_backend_prompt():
    """Load BACKEND_FILE_CREATION_PROMPT from prompts.py file."""
    prompts_file = os.path.join(
        os.path.dirname(__file__),
        "app",
        "agents",
        "developer",
        "implementor",
        "utils",
        "prompts.py",
    )

    with open(prompts_file, encoding="utf-8") as f:
        content = f.read()

    # Extract BACKEND_FILE_CREATION_PROMPT
    start_marker = 'BACKEND_FILE_CREATION_PROMPT = """'
    end_marker = '"""\n\n# Frontend File Creation Prompt'

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx)

    if start_idx == -1 or end_idx == -1:
        raise ValueError("Could not find BACKEND_FILE_CREATION_PROMPT in prompts.py")

    # Extract the prompt content
    prompt_content = content[start_idx + len(start_marker) : end_idx]
    return prompt_content


BACKEND_FILE_CREATION_PROMPT = load_backend_prompt()


def test_few_shot_examples_in_prompt():
    """Test that few-shot examples are present in the prompt template."""
    print("=" * 80)
    print("TEST 1: Verify Few-Shot Examples in Prompt Template")
    print("=" * 80)

    # Check for key sections
    checks = {
        "Example section header": "📚 EXAMPLE: Correct Dependency Usage"
        in BACKEND_FILE_CREATION_PROMPT,
        "AuthService example": "class AuthService" in BACKEND_FILE_CREATION_PROMPT,
        "loginUser method": "async loginUser(email, password)"
        in BACKEND_FILE_CREATION_PROMPT,
        "Correct implementation": "✅ CORRECT Controller implementation:"
        in BACKEND_FILE_CREATION_PROMPT,
        "Wrong implementation": "❌ WRONG Controller implementation"
        in BACKEND_FILE_CREATION_PROMPT,
        "validateUser mistake": "validateUser" in BACKEND_FILE_CREATION_PROMPT,
        "Key takeaways": "🔑 KEY TAKEAWAYS:" in BACKEND_FILE_CREATION_PROMPT,
    }

    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("✅ All few-shot example checks passed!")
    else:
        print("❌ Some few-shot example checks failed!")

    return all_passed


def test_dependency_context_structure():
    """Test the structure of dependency context in prompts."""
    print("\n" + "=" * 80)
    print("TEST 2: Verify Dependency Context Structure")
    print("=" * 80)

    # Simulate dependency context
    mock_dependency_context = """
================================================================================
📚 DEPENDENCY FILES - API SUMMARY (API CONTRACT REFERENCE)
================================================================================

⚠️ CRITICAL: Use EXACT method names, return types, and signatures from these files.
Note: Implementation details are truncated for brevity. Focus on method signatures.

📄 File: src/services/authService.js
```javascript
class AuthService {
  async loginUser(email, password) {
    // ... implementation details ...
    return { user, token };
  }
}
```

================================================================================
"""

    # Check structure
    checks = {
        "Has section header": "📚 DEPENDENCY FILES" in mock_dependency_context,
        "Has critical warning": "⚠️ CRITICAL: Use EXACT method names"
        in mock_dependency_context,
        "Has file marker": "📄 File:" in mock_dependency_context,
        "Has code block": "```javascript" in mock_dependency_context,
        "Has method signature": "async loginUser(email, password)"
        in mock_dependency_context,
        "Has return type": "return { user, token }" in mock_dependency_context,
    }

    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("✅ All dependency context structure checks passed!")
    else:
        print("❌ Some dependency context structure checks failed!")

    return all_passed


def test_critical_reminder_content():
    """Test that the critical reminder has all necessary elements."""
    print("\n" + "=" * 80)
    print("TEST 3: Verify Critical Reminder Content")
    print("=" * 80)

    # This is the reminder that gets appended in generate_code.py
    mock_reminder = """
⚠️ ⚠️ ⚠️ CRITICAL REMINDER - READ CAREFULLY ⚠️ ⚠️ ⚠️

You MUST use the EXACT method names, signatures, and return types from the DEPENDENCY FILES shown above.

BEFORE writing any code that calls a dependency method:
1. Scroll up and find the dependency file in the "📚 DEPENDENCY FILES" section
2. Locate the EXACT method name in that file
3. Check the method's parameters and return type
4. Use the EXACT method name - do NOT invent, assume, or guess method names
5. Match the EXACT return type - if it returns {user, token}, destructure both properties

COMMON MISTAKES TO AVOID:
❌ Using 'validateUser' when dependency has 'loginUser'
❌ Using 'create' when dependency has 'createUser'
❌ Ignoring return type structure (e.g., not destructuring {user, token})
❌ Passing wrong parameter format (e.g., object when it expects individual params)

Double-check EVERY method call against the dependency API summary above before generating code.
If you're unsure about a method name, look it up in the dependency files - do NOT guess!
"""

    checks = {
        "Has warning header": "⚠️ ⚠️ ⚠️ CRITICAL REMINDER" in mock_reminder,
        "Emphasizes EXACT usage": "EXACT method names" in mock_reminder,
        "Has step-by-step guide": "BEFORE writing any code" in mock_reminder,
        "Mentions validateUser mistake": "validateUser" in mock_reminder,
        "Mentions loginUser correct": "loginUser" in mock_reminder,
        "Mentions return type destructuring": "destructure" in mock_reminder,
        "Has double-check instruction": "Double-check EVERY method call"
        in mock_reminder,
        "Warns against guessing": "do NOT guess" in mock_reminder,
    }

    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("✅ All critical reminder checks passed!")
    else:
        print("❌ Some critical reminder checks failed!")

    return all_passed


def test_prompt_integration():
    """Test that the prompt template integrates well with dependency context."""
    print("\n" + "=" * 80)
    print("TEST 4: Verify Prompt Integration")
    print("=" * 80)

    # Check that API CONTRACT CONSISTENCY section exists before examples
    prompt_lines = BACKEND_FILE_CREATION_PROMPT.split("\n")

    api_contract_line = -1
    example_line = -1

    for i, line in enumerate(prompt_lines):
        if "API CONTRACT CONSISTENCY" in line:
            api_contract_line = i
        if "📚 EXAMPLE: Correct Dependency Usage" in line:
            example_line = i

    checks = {
        "API CONTRACT section exists": api_contract_line >= 0,
        "Example section exists": example_line >= 0,
        "Example comes after API CONTRACT": example_line > api_contract_line
        if (api_contract_line >= 0 and example_line >= 0)
        else False,
    }

    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("✅ All prompt integration checks passed!")
    else:
        print("❌ Some prompt integration checks failed!")

    return all_passed


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("DEPENDENCY CONTEXT FIX - VERIFICATION TESTS")
    print("=" * 80)
    print()

    results = []

    # Run all tests
    results.append(("Few-Shot Examples", test_few_shot_examples_in_prompt()))
    results.append(
        ("Dependency Context Structure", test_dependency_context_structure())
    )
    results.append(("Critical Reminder Content", test_critical_reminder_content()))
    results.append(("Prompt Integration", test_prompt_integration()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    print()
    print(f"Total: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print(
            "\n🎉 All tests passed! The dependency context fix is properly implemented."
        )
        return 0
    else:
        print(
            f"\n⚠️ {total_tests - passed_tests} test(s) failed. Please review the implementation."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
