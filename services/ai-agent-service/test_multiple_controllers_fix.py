"""
Test script to verify Multiple Controllers fix in prompt templates.

This script tests that prompt templates include proper guidance for routes files
that need to import and use multiple controllers.
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


def test_backend_file_creation_routes_guidance():
    """Test BACKEND_FILE_CREATION_PROMPT has routes-specific guidance."""
    print("=" * 80)
    print("TEST 1: BACKEND_FILE_CREATION_PROMPT - Routes Guidance")
    print("=" * 80)
    
    content = load_prompts_file()
    prompt = extract_prompt(content, "BACKEND_FILE_CREATION_PROMPT")
    
    if not prompt:
        print("❌ FAIL: Could not extract BACKEND_FILE_CREATION_PROMPT")
        return False
    
    checks = {
        "Has <routes_specific_guidance> tag": "<routes_specific_guidance>" in prompt,
        "Has </routes_specific_guidance> tag": "</routes_specific_guidance>" in prompt,
        "Mentions MULTIPLE CONTROLLERS": "MULTIPLE CONTROLLERS" in prompt,
        "Mentions authController AND tokenController": "authController AND tokenController" in prompt,
        "Has example with tokenController import": "const tokenController = require" in prompt,
        "Warns about wrong controller assumption": "WRONG: Assuming all auth routes use authController" in prompt,
        "Has verification checklist for routes": "VERIFICATION CHECKLIST FOR ROUTES FILES" in prompt or "VERIFICATION:" in prompt,
        "Shows correct vs incorrect example": "✅ CORRECT" in prompt and "❌ WRONG" in prompt,
        "Mentions checking DEPENDENCY FILES": "DEPENDENCY FILES" in prompt,
        "Mentions refreshToken example": "refreshToken" in prompt,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All BACKEND_FILE_CREATION_PROMPT routes guidance checks passed!")
    else:
        print("❌ Some BACKEND_FILE_CREATION_PROMPT routes guidance checks failed!")
    
    return all_passed


def test_backend_file_modification_routes_guidance():
    """Test BACKEND_FILE_MODIFICATION_PROMPT has routes-specific guidance."""
    print("\n" + "=" * 80)
    print("TEST 2: BACKEND_FILE_MODIFICATION_PROMPT - Routes Guidance")
    print("=" * 80)
    
    content = load_prompts_file()
    prompt = extract_prompt(content, "BACKEND_FILE_MODIFICATION_PROMPT")
    
    if not prompt:
        print("❌ FAIL: Could not extract BACKEND_FILE_MODIFICATION_PROMPT")
        return False
    
    checks = {
        "Has <routes_specific_guidance> tag": "<routes_specific_guidance>" in prompt,
        "Has </routes_specific_guidance> tag": "</routes_specific_guidance>" in prompt,
        "Mentions MULTIPLE CONTROLLERS": "MULTIPLE CONTROLLERS" in prompt,
        "Has example showing import addition": "ADD new import" in prompt or "ADD the import" in prompt,
        "Shows preserving existing routes": "PRESERVE" in prompt,
        "Has correct vs incorrect example": "✅ CORRECT" in prompt and "❌ WRONG" in prompt,
        "Mentions checking DEPENDENCY FILES": "DEPENDENCY FILES" in prompt,
        "Shows tokenController example": "tokenController" in prompt,
        "Warns about missing imports": "Missing tokenController import" in prompt or "missing" in prompt.lower(),
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All BACKEND_FILE_MODIFICATION_PROMPT routes guidance checks passed!")
    else:
        print("❌ Some BACKEND_FILE_MODIFICATION_PROMPT routes guidance checks failed!")
    
    return all_passed


def test_routes_guidance_content_quality():
    """Test the quality and completeness of routes guidance content."""
    print("\n" + "=" * 80)
    print("TEST 3: Routes Guidance Content Quality")
    print("=" * 80)
    
    content = load_prompts_file()
    
    # Extract routes_specific_guidance sections
    creation_prompt = extract_prompt(content, "BACKEND_FILE_CREATION_PROMPT")
    modification_prompt = extract_prompt(content, "BACKEND_FILE_MODIFICATION_PROMPT")
    
    if not creation_prompt or not modification_prompt:
        print("❌ FAIL: Could not extract prompts")
        return False
    
    checks = {
        "Creation prompt has concrete code example": "```javascript" in creation_prompt,
        "Modification prompt has concrete code example": "```javascript" in modification_prompt,
        "Creation prompt mentions auth.js scenario": "auth.js" in creation_prompt,
        "Modification prompt mentions auth.js scenario": "auth.js" in modification_prompt,
        "Creation prompt has step-by-step verification": "[ ]" in creation_prompt,
        "Modification prompt has step-by-step verification": "[ ]" in modification_prompt,
        "Both prompts mention integration points": "INTEGRATION" in creation_prompt.upper() or "INTEGRATION" in modification_prompt.upper(),
        "Both prompts emphasize checking dependencies": creation_prompt.count("DEPENDENCY FILES") >= 2 and modification_prompt.count("DEPENDENCY FILES") >= 2,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All routes guidance content quality checks passed!")
    else:
        print("❌ Some routes guidance content quality checks failed!")
    
    return all_passed


def test_xml_tags_balance():
    """Test that routes_specific_guidance tags are properly balanced."""
    print("\n" + "=" * 80)
    print("TEST 4: XML Tags Balance for Routes Guidance")
    print("=" * 80)
    
    content = load_prompts_file()
    
    open_tag = "<routes_specific_guidance>"
    close_tag = "</routes_specific_guidance>"
    
    open_count = content.count(open_tag)
    close_count = content.count(close_tag)
    
    checks = {
        f"Has {open_tag} tags": open_count > 0,
        f"Has {close_tag} tags": close_count > 0,
        "Tags are balanced": open_count == close_count,
        "Has at least 2 occurrences (creation + modification)": open_count >= 2,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        if "balanced" in check_name:
            print(f"{status}: {check_name} ({open_count} open, {close_count} close)")
        else:
            print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All XML tags balance checks passed!")
    else:
        print("❌ Some XML tags balance checks failed!")
    
    return all_passed


def test_integration_with_dependency_context_fix():
    """Test that routes guidance integrates well with dependency context fix."""
    print("\n" + "=" * 80)
    print("TEST 5: Integration with Dependency Context Fix")
    print("=" * 80)
    
    content = load_prompts_file()
    creation_prompt = extract_prompt(content, "BACKEND_FILE_CREATION_PROMPT")
    
    if not creation_prompt:
        print("❌ FAIL: Could not extract BACKEND_FILE_CREATION_PROMPT")
        return False
    
    # Check that both dependency context fix and routes guidance exist
    checks = {
        "Has <examples> tag (from dependency fix)": "<examples>" in creation_prompt,
        "Has <routes_specific_guidance> tag (new)": "<routes_specific_guidance>" in creation_prompt,
        "Routes guidance comes after examples": creation_prompt.find("<routes_specific_guidance>") > creation_prompt.find("</examples>"),
        "Both mention DEPENDENCY FILES": creation_prompt.count("DEPENDENCY FILES") >= 3,
        "Both use ✅ CORRECT and ❌ WRONG pattern": creation_prompt.count("✅ CORRECT") >= 2 and creation_prompt.count("❌ WRONG") >= 2,
        "Both have concrete code examples": creation_prompt.count("```javascript") >= 2,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ All integration checks passed!")
    else:
        print("❌ Some integration checks failed!")
    
    return all_passed


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("MULTIPLE CONTROLLERS FIX - VERIFICATION TESTS")
    print("=" * 80)
    print()
    
    results = []
    
    # Run all tests
    results.append(("BACKEND_FILE_CREATION_PROMPT Routes Guidance", test_backend_file_creation_routes_guidance()))
    results.append(("BACKEND_FILE_MODIFICATION_PROMPT Routes Guidance", test_backend_file_modification_routes_guidance()))
    results.append(("Routes Guidance Content Quality", test_routes_guidance_content_quality()))
    results.append(("XML Tags Balance", test_xml_tags_balance()))
    results.append(("Integration with Dependency Context Fix", test_integration_with_dependency_context_fix()))
    
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
        print("\n🎉 All tests passed! Routes-specific guidance is properly implemented.")
        return 0
    else:
        print(f"\n⚠️ {total_tests - passed_tests} test(s) failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

