#!/usr/bin/env python3
"""
Test script để verify file modification fix
"""

import sys
import os


def test_modification_prompts_enhanced():
    """Test modification prompts có enhanced instructions"""

    print("🧪 Testing Modification Prompts Enhancement")
    print("=" * 60)

    try:
        # Read prompts file
        prompts_file = (
            "ai-agent-service/app/agents/developer/implementor/utils/prompts.py"
        )

        if os.path.exists(prompts_file):
            with open(prompts_file, "r") as f:
                content = f.read()

            print("✅ Successfully read prompts.py")

            # Check for code placement requirements
            placement_checks = [
                (
                    "Code placement section",
                    "CRITICAL CODE PLACEMENT REQUIREMENTS" in content,
                ),
                (
                    "Never append warning",
                    "NEVER append new code to the end of the file" in content,
                ),
                (
                    "Insert instruction",
                    "INSERT code at the appropriate logical location" in content,
                ),
                ("Routes placement", "For new routes: Insert in the" in content),
                ("Imports placement", "For new imports: Insert at the top" in content),
                (
                    "Complete file output",
                    "Return ONLY the COMPLETE modified file content" in content,
                ),
                (
                    "Include all existing",
                    "Include ALL existing code with your modifications" in content,
                ),
                ("Logical flow maintenance", "MAINTAIN the logical flow" in content),
            ]

            passed = 0
            for check_name, check_result in placement_checks:
                status = "✅" if check_result else "❌"
                print(f"   {status} {check_name}")
                if check_result:
                    passed += 1

            print(f"\n📊 Overall: {passed}/{len(placement_checks)} checks passed")
            return passed == len(placement_checks)
        else:
            print(f"❌ File not found: {prompts_file}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_backend_modification_prompt():
    """Test BACKEND_FILE_MODIFICATION_PROMPT specifically"""

    print("\n🧪 Testing Backend Modification Prompt")
    print("=" * 60)

    try:
        prompts_file = (
            "ai-agent-service/app/agents/developer/implementor/utils/prompts.py"
        )

        if os.path.exists(prompts_file):
            with open(prompts_file, "r") as f:
                content = f.read()

            # Extract BACKEND_FILE_MODIFICATION_PROMPT
            start_marker = 'BACKEND_FILE_MODIFICATION_PROMPT = """'
            end_marker = '"""\n\n# Frontend File Modification Prompt'

            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker, start_idx)

            if start_idx != -1 and end_idx != -1:
                backend_prompt = content[start_idx:end_idx]
                print("✅ Successfully extracted BACKEND_FILE_MODIFICATION_PROMPT")

                # Check specific backend requirements
                backend_checks = [
                    (
                        "Express.js routing structure",
                        "Express.js: Preserve middleware chain, maintain routing structure"
                        in backend_prompt,
                    ),
                    (
                        "Code placement requirements",
                        "CRITICAL CODE PLACEMENT REQUIREMENTS" in backend_prompt,
                    ),
                    (
                        "Routes insertion",
                        "For new routes: Insert in the" in backend_prompt,
                    ),
                    (
                        "Middleware insertion",
                        "For new middleware: Insert in the middleware section"
                        in backend_prompt,
                    ),
                    (
                        "Complete file return",
                        "Return ONLY the COMPLETE modified file content"
                        in backend_prompt,
                    ),
                    (
                        "Logical flow",
                        "MAINTAIN the logical flow:" in backend_prompt
                        and "imports" in backend_prompt
                        and "routes" in backend_prompt,
                    ),
                ]

                passed = 0
                for check_name, check_result in backend_checks:
                    status = "✅" if check_result else "❌"
                    print(f"   {status} {check_name}")
                    if check_result:
                        passed += 1

                print(
                    f"\n📊 Backend prompt: {passed}/{len(backend_checks)} checks passed"
                )
                return passed == len(backend_checks)
            else:
                print("❌ Could not extract BACKEND_FILE_MODIFICATION_PROMPT")
                return False
        else:
            print(f"❌ File not found: {prompts_file}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_frontend_modification_prompt():
    """Test FRONTEND_FILE_MODIFICATION_PROMPT specifically"""

    print("\n🧪 Testing Frontend Modification Prompt")
    print("=" * 60)

    try:
        prompts_file = (
            "ai-agent-service/app/agents/developer/implementor/utils/prompts.py"
        )

        if os.path.exists(prompts_file):
            with open(prompts_file, "r") as f:
                content = f.read()

            # Extract FRONTEND_FILE_MODIFICATION_PROMPT
            start_marker = 'FRONTEND_FILE_MODIFICATION_PROMPT = """'
            end_marker = '"""\n\n# Generic File Modification Prompt'

            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker, start_idx)

            if start_idx != -1 and end_idx != -1:
                frontend_prompt = content[start_idx:end_idx]
                print("✅ Successfully extracted FRONTEND_FILE_MODIFICATION_PROMPT")

                # Check specific frontend requirements
                frontend_checks = [
                    (
                        "Code placement requirements",
                        "CRITICAL CODE PLACEMENT REQUIREMENTS" in frontend_prompt,
                    ),
                    (
                        "Component insertion",
                        "For new components: Insert in appropriate component section"
                        in frontend_prompt,
                    ),
                    (
                        "Hooks insertion",
                        "For new hooks: Insert in hooks section" in frontend_prompt,
                    ),
                    (
                        "Complete file return",
                        "Return ONLY the COMPLETE modified file content"
                        in frontend_prompt,
                    ),
                    (
                        "Logical flow",
                        "MAINTAIN the logical flow:" in frontend_prompt
                        and "imports" in frontend_prompt
                        and "components" in frontend_prompt,
                    ),
                ]

                passed = 0
                for check_name, check_result in frontend_checks:
                    status = "✅" if check_result else "❌"
                    print(f"   {status} {check_name}")
                    if check_result:
                        passed += 1

                print(
                    f"\n📊 Frontend prompt: {passed}/{len(frontend_checks)} checks passed"
                )
                return passed == len(frontend_checks)
            else:
                print("❌ Could not extract FRONTEND_FILE_MODIFICATION_PROMPT")
                return False
        else:
            print(f"❌ File not found: {prompts_file}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_generic_modification_prompt():
    """Test GENERIC_FILE_MODIFICATION_PROMPT specifically"""

    print("\n🧪 Testing Generic Modification Prompt")
    print("=" * 60)

    try:
        prompts_file = (
            "ai-agent-service/app/agents/developer/implementor/utils/prompts.py"
        )

        if os.path.exists(prompts_file):
            with open(prompts_file, "r") as f:
                content = f.read()

            # Extract GENERIC_FILE_MODIFICATION_PROMPT
            start_marker = 'GENERIC_FILE_MODIFICATION_PROMPT = """'
            end_marker = '"""\n\n# Git Commit Message Prompt'

            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker, start_idx)

            if start_idx != -1 and end_idx != -1:
                generic_prompt = content[start_idx:end_idx]
                print("✅ Successfully extracted GENERIC_FILE_MODIFICATION_PROMPT")

                # Check specific generic requirements
                generic_checks = [
                    (
                        "Code placement requirements",
                        "CRITICAL CODE PLACEMENT REQUIREMENTS" in generic_prompt,
                    ),
                    (
                        "Complete file return",
                        "Return ONLY the COMPLETE modified file content"
                        in generic_prompt,
                    ),
                    (
                        "Logical flow maintenance",
                        "MAINTAIN the logical flow and structure" in generic_prompt,
                    ),
                ]

                passed = 0
                for check_name, check_result in generic_checks:
                    status = "✅" if check_result else "❌"
                    print(f"   {status} {check_name}")
                    if check_result:
                        passed += 1

                print(
                    f"\n📊 Generic prompt: {passed}/{len(generic_checks)} checks passed"
                )
                return passed == len(generic_checks)
            else:
                print("❌ Could not extract GENERIC_FILE_MODIFICATION_PROMPT")
                return False
        else:
            print(f"❌ File not found: {prompts_file}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main test function"""

    print("🚀 File Modification Fix Verification")
    print("=" * 80)

    tests = [
        ("Modification prompts enhanced", test_modification_prompts_enhanced),
        ("Backend modification prompt", test_backend_modification_prompt),
        ("Frontend modification prompt", test_frontend_modification_prompt),
        ("Generic modification prompt", test_generic_modification_prompt),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("📊 FILE MODIFICATION FIX SUMMARY")
    print("=" * 80)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 File Modification Fix Successfully Applied!")
        print("\n✅ Key Improvements:")
        print(
            "   - Added CRITICAL CODE PLACEMENT REQUIREMENTS to all modification prompts"
        )
        print("   - Added 'NEVER append new code to the end of the file' warning")
        print("   - Added specific insertion instructions for different code types")
        print("   - Changed output format to return COMPLETE modified file content")
        print("   - Added logical flow maintenance requirements")

        print("\n🚀 Expected Behavior After Fix:")
        print("   - New routes → Insert in routes section (not append to end)")
        print("   - New middleware → Insert in middleware section")
        print("   - New imports → Insert at top with similar imports")
        print("   - New functions → Insert near related functions")
        print("   - Maintain existing code organization and structure")

        print("\n📋 LLM will now:")
        print("   - Return COMPLETE file with modifications properly placed")
        print("   - Respect existing code structure and organization")
        print("   - Insert code at logical locations, not append to end")
        print("   - Maintain imports → config → middleware → routes → exports flow")

    else:
        print("⚠️ Some tests failed. Please check the issues above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
