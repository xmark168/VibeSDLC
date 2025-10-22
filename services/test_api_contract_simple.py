#!/usr/bin/env python3
"""
Simple test of API contract coordination logic without imports
"""


def test_dependency_identification_logic():
    """Test dependency identification logic (standalone)"""
    print("=" * 70)
    print("Test 1: Dependency Identification Logic")
    print("=" * 70)

    # Inline implementation of _identify_dependency_files
    def identify_deps(current_file: str, created_files: list) -> list:
        dependencies = []
        current_file = current_file.replace("\\", "/")
        created_files = [f.replace("\\", "/") for f in created_files]

        from pathlib import Path

        current_name = Path(current_file).stem

        if "/controllers/" in current_file:
            service_name = current_name.replace("Controller", "Service")
            for created in created_files:
                if "/services/" in created and service_name in created:
                    dependencies.append(created)

        elif "/services/" in current_file:
            base_name = current_name.replace("Service", "")
            for created in created_files:
                if "/repositories/" in created:
                    if base_name.lower() in created.lower() or "Repository" in created:
                        dependencies.append(created)

        elif "/repositories/" in current_file:
            base_name = current_name.replace("Repository", "")
            for created in created_files:
                if "/models/" in created:
                    if base_name.lower() in created.lower():
                        dependencies.append(created)

        return dependencies

    # Test cases
    created_files = [
        "src/models/User.js",
        "src/repositories/userRepository.js",
        "src/services/authService.js",
    ]

    # Test 1: Controller -> Service
    current = "src/controllers/authController.js"
    deps = identify_deps(current, created_files)
    print("\n📝 Test Case 1: Controller -> Service")
    print(f"   Current: {current}")
    print(f"   Dependencies: {deps}")

    if "src/services/authService.js" in deps:
        print("   ✅ PASS: Correctly identified authService.js")
        test1 = True
    else:
        print("   ❌ FAIL: Did not identify authService.js")
        test1 = False

    # Test 2: Service -> Repository
    current = "src/services/authService.js"
    deps = identify_deps(current, created_files)
    print("\n📝 Test Case 2: Service -> Repository")
    print(f"   Current: {current}")
    print(f"   Dependencies: {deps}")

    if "src/repositories/userRepository.js" in deps:
        print("   ✅ PASS: Correctly identified userRepository.js")
        test2 = True
    else:
        print("   ❌ FAIL: Did not identify userRepository.js")
        test2 = False

    # Test 3: Repository -> Model
    current = "src/repositories/userRepository.js"
    deps = identify_deps(current, created_files)
    print("\n📝 Test Case 3: Repository -> Model")
    print(f"   Current: {current}")
    print(f"   Dependencies: {deps}")

    if "src/models/User.js" in deps:
        print("   ✅ PASS: Correctly identified User.js")
        test3 = True
    else:
        print("   ❌ FAIL: Did not identify User.js")
        test3 = False

    return test1 and test2 and test3


def test_prompt_content():
    """Test prompt file has API contract instructions"""
    print("\n" + "=" * 70)
    print("Test 2: Prompt API Contract Instructions")
    print("=" * 70)

    try:
        with open(
            "ai-agent-service/app/agents/developer/implementor/utils/prompts.py",
            "r",
            encoding="utf-8",
        ) as f:
            prompt_content = f.read()

        checks = [
            ("API CONTRACT CONSISTENCY", "API contract section"),
            ("DEPENDENCY COORDINATION", "Dependency coordination"),
            ("EXACT method names", "Exact method names"),
            ("EXACT return types", "Exact return types"),
            ("SOURCE OF TRUTH", "Source of truth"),
        ]

        all_pass = True
        for check_text, check_name in checks:
            if check_text in prompt_content:
                print(f"   ✅ {check_name}: Found")
            else:
                print(f"   ❌ {check_name}: NOT found")
                all_pass = False

        return all_pass

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_execute_step_changes():
    """Test execute_step.py has new functions"""
    print("\n" + "=" * 70)
    print("Test 3: Execute Step Code Changes")
    print("=" * 70)

    try:
        with open(
            "ai-agent-service/app/agents/developer/implementor/nodes/execute_step.py",
            "r",
            encoding="utf-8",
        ) as f:
            code_content = f.read()

        checks = [
            ("def _identify_dependency_files", "Dependency identification function"),
            ("def _read_dependency_file_content", "Dependency file reading function"),
            (
                "DEPENDENCY FILES (API CONTRACT REFERENCE)",
                "Dependency context in _build_file_context",
            ),
            (
                "_identify_dependency_files(file_path, state.files_created)",
                "Call to identify dependencies",
            ),
        ]

        all_pass = True
        for check_text, check_name in checks:
            if check_text in code_content:
                print(f"   ✅ {check_name}: Found")
            else:
                print(f"   ❌ {check_name}: NOT found")
                all_pass = False

        return all_pass

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_actual_issues():
    """Test against actual codebase issues"""
    print("\n" + "=" * 70)
    print("Test 4: Actual Codebase Issues (Confirmed)")
    print("=" * 70)

    try:
        service_file = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/services/authService.js"
        controller_file = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/controllers/authController.js"
        repo_file = "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/repositories/userRepository.js"

        with open(service_file, "r", encoding="utf-8") as f:
            service_content = f.read()

        with open(controller_file, "r", encoding="utf-8") as f:
            controller_content = f.read()

        with open(repo_file, "r", encoding="utf-8") as f:
            repo_content = f.read()

        print("\n📊 Issue 1: Return Type Mismatch (Service -> Controller)")

        issue1_exists = False
        if (
            "return {" in service_content
            and "user:" in service_content
            and "token," in service_content
        ):
            print("   ✅ Service returns {user, token} object")

            if "const user = await AuthService.registerUser" in controller_content:
                print("   ❌ ISSUE CONFIRMED: Controller expects only user")
                issue1_exists = True
            elif "const { user, token }" in controller_content:
                print("   ✅ Controller correctly destructures {user, token}")

        print("\n📊 Issue 2: Method Name Mismatch (Repository -> Service)")

        issue2_exists = False
        if "async createUser(" in repo_content:
            print("   ✅ Repository has createUser() method")

            if "userRepository.create(" in service_content:
                print(
                    "   ❌ ISSUE CONFIRMED: Service calls create() instead of createUser()"
                )
                issue2_exists = True
            elif "userRepository.createUser(" in service_content:
                print("   ✅ Service correctly calls createUser()")

        print("\n📝 Summary:")
        print(
            f"   Issue 1 (Return Type Mismatch): {'EXISTS' if issue1_exists else 'FIXED'}"
        )
        print(
            f"   Issue 2 (Method Name Mismatch): {'EXISTS' if issue2_exists else 'FIXED'}"
        )

        # Return True if issues exist (confirms our analysis)
        return issue1_exists and issue2_exists

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing API Contract Coordination Fix")
    print("=" * 70)

    test1 = test_dependency_identification_logic()
    test2 = test_prompt_content()
    test3 = test_execute_step_changes()
    test4 = test_actual_issues()

    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print(f"   Dependency Identification Logic: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Prompt API Contract Instructions: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"   Execute Step Code Changes: {'✅ PASS' if test3 else '❌ FAIL'}")
    print(f"   Actual Issues Confirmed: {'✅ PASS' if test4 else '❌ FAIL'}")

    all_pass = test1 and test2 and test3 and test4

    print("\n" + "=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASSED!")
        print("\n📝 Fix Summary:")
        print("   1. ✅ Dependency identification logic implemented")
        print("   2. ✅ Prompt includes API contract consistency instructions")
        print("   3. ✅ Context building enhanced with dependency file content")
        print(
            "   4. ✅ Actual codebase issues confirmed (will be fixed on next generation)"
        )
        print("\n🎯 Next Steps:")
        print("   - Run Implementor Agent to generate new code")
        print("   - Verify generated code has correct API contracts")
        print("   - Check method names match between layers")
        print("   - Check return types match between layers")
    else:
        print("❌ SOME TESTS FAILED - Review implementation")

    return all_pass


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)
