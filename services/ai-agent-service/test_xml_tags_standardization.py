"""
Test script to verify XML-style tags standardization in prompt templates.

This script tests that all major prompt templates use consistent XML-style tags
for structuring their content.
"""

import os


def load_prompts_file():
    """Load prompts.py file content."""
    prompts_file = os.path.join(
        os.path.dirname(__file__),
        "app", "agents", "developer", "implementor", "utils", "prompts.py"
    )
    
    with open(prompts_file, encoding="utf-8") as f:
        return f.read()


def extract_prompt(content, prompt_name):
    """Extract a specific prompt from the file content."""
    start_marker = f'{prompt_name} = """'
    
    # Find the next prompt or end of file
    start_idx = content.find(start_marker)
    if start_idx == -1:
        return None
    
    # Find the closing triple quotes
    start_idx += len(start_marker)
    end_idx = content.find('"""', start_idx)
    
    if end_idx == -1:
        return None
    
    return content[start_idx:end_idx]


def test_backend_file_creation_prompt():
    """Test BACKEND_FILE_CREATION_PROMPT has proper XML tags."""
    print("=" * 80)
    print("TEST 1: BACKEND_FILE_CREATION_PROMPT XML Tags")
    print("=" * 80)
    
    content = load_prompts_file()
    prompt = extract_prompt(content, "BACKEND_FILE_CREATION_PROMPT")
    
    if not prompt:
        print("❌ FAIL: Could not extract BACKEND_FILE_CREATION_PROMPT")
        return False
    
    checks = {
        "Has <critical_rules> tag": "<critical_rules>" in prompt,
        "Has </critical_rules> tag": "</critical_rules>" in prompt,
        "Has <api_contract> tag": "<api_contract>" in prompt,
        "Has </api_contract> tag": "</api_contract>" in prompt,
        "Has <examples> tag": "<examples>" in prompt,
        "Has </examples> tag": "</examples>" in prompt,
        "Has <best_practices> tag": "<best_practices>" in prompt,
        "Has </best_practices> tag": "</best_practices>" in prompt,
        "Has <output_format> tag": "<output_format>" in prompt,
        "Has </output_format> tag": "</output_format>" in prompt,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All BACKEND_FILE_CREATION_PROMPT XML tag checks passed!")
    else:
        print("❌ Some BACKEND_FILE_CREATION_PROMPT XML tag checks failed!")
    
    return all_passed


def test_frontend_file_creation_prompt():
    """Test FRONTEND_FILE_CREATION_PROMPT has proper XML tags."""
    print("\n" + "=" * 80)
    print("TEST 2: FRONTEND_FILE_CREATION_PROMPT XML Tags")
    print("=" * 80)
    
    content = load_prompts_file()
    prompt = extract_prompt(content, "FRONTEND_FILE_CREATION_PROMPT")
    
    if not prompt:
        print("❌ FAIL: Could not extract FRONTEND_FILE_CREATION_PROMPT")
        return False
    
    checks = {
        "Has <critical_rules> tag": "<critical_rules>" in prompt,
        "Has </critical_rules> tag": "</critical_rules>" in prompt,
        "Has <best_practices> tag": "<best_practices>" in prompt,
        "Has </best_practices> tag": "</best_practices>" in prompt,
        "Has <output_format> tag": "<output_format>" in prompt,
        "Has </output_format> tag": "</output_format>" in prompt,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All FRONTEND_FILE_CREATION_PROMPT XML tag checks passed!")
    else:
        print("❌ Some FRONTEND_FILE_CREATION_PROMPT XML tag checks failed!")
    
    return all_passed


def test_generic_file_creation_prompt():
    """Test GENERIC_FILE_CREATION_PROMPT has proper XML tags."""
    print("\n" + "=" * 80)
    print("TEST 3: GENERIC_FILE_CREATION_PROMPT XML Tags")
    print("=" * 80)
    
    content = load_prompts_file()
    prompt = extract_prompt(content, "GENERIC_FILE_CREATION_PROMPT")
    
    if not prompt:
        print("❌ FAIL: Could not extract GENERIC_FILE_CREATION_PROMPT")
        return False
    
    checks = {
        "Has <critical_rules> tag": "<critical_rules>" in prompt,
        "Has </critical_rules> tag": "</critical_rules>" in prompt,
        "Has <best_practices> tag": "<best_practices>" in prompt,
        "Has </best_practices> tag": "</best_practices>" in prompt,
        "Has <output_format> tag": "<output_format>" in prompt,
        "Has </output_format> tag": "</output_format>" in prompt,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All GENERIC_FILE_CREATION_PROMPT XML tag checks passed!")
    else:
        print("❌ Some GENERIC_FILE_CREATION_PROMPT XML tag checks failed!")
    
    return all_passed


def test_backend_file_modification_prompt():
    """Test BACKEND_FILE_MODIFICATION_PROMPT has proper XML tags."""
    print("\n" + "=" * 80)
    print("TEST 4: BACKEND_FILE_MODIFICATION_PROMPT XML Tags")
    print("=" * 80)
    
    content = load_prompts_file()
    prompt = extract_prompt(content, "BACKEND_FILE_MODIFICATION_PROMPT")
    
    if not prompt:
        print("❌ FAIL: Could not extract BACKEND_FILE_MODIFICATION_PROMPT")
        return False
    
    checks = {
        "Has <critical_rules> tag": "<critical_rules>" in prompt,
        "Has </critical_rules> tag": "</critical_rules>" in prompt,
        "Has <backend_specific_guidelines> tag": "<backend_specific_guidelines>" in prompt,
        "Has </backend_specific_guidelines> tag": "</backend_specific_guidelines>" in prompt,
        "Has <output_format> tag": "<output_format>" in prompt,
        "Has </output_format> tag": "</output_format>" in prompt,
        "Has <verification_checklist> tag": "<verification_checklist>" in prompt,
        "Has </verification_checklist> tag": "</verification_checklist>" in prompt,
        "Has <backend_examples> tag": "<backend_examples>" in prompt,
        "Has </backend_examples> tag": "</backend_examples>" in prompt,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All BACKEND_FILE_MODIFICATION_PROMPT XML tag checks passed!")
    else:
        print("❌ Some BACKEND_FILE_MODIFICATION_PROMPT XML tag checks failed!")
    
    return all_passed


def test_generic_file_modification_prompt():
    """Test GENERIC_FILE_MODIFICATION_PROMPT has proper XML tags."""
    print("\n" + "=" * 80)
    print("TEST 5: GENERIC_FILE_MODIFICATION_PROMPT XML Tags")
    print("=" * 80)
    
    content = load_prompts_file()
    prompt = extract_prompt(content, "GENERIC_FILE_MODIFICATION_PROMPT")
    
    if not prompt:
        print("❌ FAIL: Could not extract GENERIC_FILE_MODIFICATION_PROMPT")
        return False
    
    checks = {
        "Has <best_practices> tag": "<best_practices>" in prompt,
        "Has </best_practices> tag": "</best_practices>" in prompt,
        "Has <output_format> tag": "<output_format>" in prompt,
        "Has </output_format> tag": "</output_format>" in prompt,
        "Has <critical_requirements> tag": "<critical_requirements>" in prompt,
        "Has </critical_requirements> tag": "</critical_requirements>" in prompt,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All GENERIC_FILE_MODIFICATION_PROMPT XML tag checks passed!")
    else:
        print("❌ Some GENERIC_FILE_MODIFICATION_PROMPT XML tag checks failed!")
    
    return all_passed


def test_tag_consistency():
    """Test that XML tags are properly nested and closed."""
    print("\n" + "=" * 80)
    print("TEST 6: XML Tag Consistency")
    print("=" * 80)
    
    content = load_prompts_file()
    
    # Common tags to check
    tags_to_check = [
        "critical_rules",
        "api_contract",
        "examples",
        "best_practices",
        "output_format",
        "verification_checklist",
        "backend_specific_guidelines",
        "frontend_specific_guidelines",
        "critical_requirements",
    ]
    
    all_passed = True
    for tag in tags_to_check:
        open_tag = f"<{tag}>"
        close_tag = f"</{tag}>"
        
        open_count = content.count(open_tag)
        close_count = content.count(close_tag)
        
        if open_count > 0:
            if open_count == close_count:
                print(f"✅ PASS: <{tag}> tags are balanced ({open_count} open, {close_count} close)")
            else:
                print(f"❌ FAIL: <{tag}> tags are NOT balanced ({open_count} open, {close_count} close)")
                all_passed = False
    
    print()
    if all_passed:
        print("✅ All XML tags are properly balanced!")
    else:
        print("❌ Some XML tags are not properly balanced!")
    
    return all_passed


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("XML TAGS STANDARDIZATION - VERIFICATION TESTS")
    print("=" * 80)
    print()
    
    results = []
    
    # Run all tests
    results.append(("BACKEND_FILE_CREATION_PROMPT", test_backend_file_creation_prompt()))
    results.append(("FRONTEND_FILE_CREATION_PROMPT", test_frontend_file_creation_prompt()))
    results.append(("GENERIC_FILE_CREATION_PROMPT", test_generic_file_creation_prompt()))
    results.append(("BACKEND_FILE_MODIFICATION_PROMPT", test_backend_file_modification_prompt()))
    results.append(("GENERIC_FILE_MODIFICATION_PROMPT", test_generic_file_modification_prompt()))
    results.append(("XML Tag Consistency", test_tag_consistency()))
    
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
        print("\n🎉 All tests passed! XML tags are properly standardized across all prompts.")
        return 0
    else:
        print(f"\n⚠️ {total_tests - passed_tests} test(s) failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

