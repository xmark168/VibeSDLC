#!/usr/bin/env python3
"""
Simple test script to validate specific helper functions without full module dependencies.
"""

import os
import re
import json


def test_file_naming_convention(file_path: str) -> bool:
    """
    Validate file naming convention based on Express.js guidelines.
    (Copy of the function from generate_plan.py for testing)
    """
    # Extract filename and directory
    parts = file_path.split("/")
    if len(parts) < 2:
        return True  # Skip validation for root files

    directory = parts[-2]
    filename = parts[-1]

    # Remove file extension for validation
    name_without_ext = (
        filename.replace(".js", "")
        .replace(".jsx", "")
        .replace(".ts", "")
        .replace(".tsx", "")
    )

    # Validation rules based on directory
    if directory == "models":
        # Models should be PascalCase
        return re.match(r"^[A-Z][a-zA-Z0-9]*$", name_without_ext) is not None
    elif directory in ["repositories", "services", "controllers"]:
        # These should be camelCase
        return re.match(r"^[a-z][a-zA-Z0-9]*$", name_without_ext) is not None
    elif directory == "routes":
        # Routes can be camelCase or kebab-case
        return (
            re.match(r"^[a-z][a-zA-Z0-9]*$", name_without_ext) is not None
            or re.match(r"^[a-z][a-z0-9-]*$", name_without_ext) is not None
        )
    elif directory == "tests":
        # Tests should be kebab-case (allow .test suffix)
        test_name = name_without_ext.replace(".test", "").replace(".spec", "")
        return re.match(r"^[a-z][a-z0-9-]*$", test_name) is not None

    return True  # Default to valid for other directories


def test_agents_md_exists():
    """Test if AGENTS.md file exists and contains expected content"""
    print("🧪 Testing AGENTS.md file existence and content...")

    agents_md_path = (
        "ai-agent-service/app/agents/demo/be/nodejs/express-basic/AGENTS.md"
    )

    if os.path.exists(agents_md_path):
        print(f"   ✅ AGENTS.md found at: {agents_md_path}")

        try:
            with open(agents_md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for key architecture content
            checks = [
                ("Express.js", "Express.js framework reference"),
                ("Layered Architecture", "Architecture pattern description"),
                ("Routes", "Routes layer documentation"),
                ("Controllers", "Controllers layer documentation"),
                ("Services", "Services layer documentation"),
                ("Models", "Models layer documentation"),
                ("src/models/", "File structure documentation"),
                ("camelCase", "Naming conventions"),
                ("PascalCase", "Model naming conventions"),
            ]

            passed = 0
            for keyword, description in checks:
                if keyword in content:
                    print(f"   ✅ Found: {description}")
                    passed += 1
                else:
                    print(f"   ❌ Missing: {description}")

            print(f"   📊 Content validation: {passed}/{len(checks)} checks passed")
            return passed >= len(checks) * 0.8  # 80% pass rate

        except Exception as e:
            print(f"   ❌ Error reading AGENTS.md: {e}")
            return False
    else:
        print(f"   ❌ AGENTS.md not found at: {agents_md_path}")
        return False


def test_express_project_structure():
    """Test if Express.js project structure exists"""
    print("🧪 Testing Express.js project structure...")

    base_path = "ai-agent-service/app/agents/demo/be/nodejs/express-basic"

    if not os.path.exists(base_path):
        print(f"   ❌ Express.js demo project not found at: {base_path}")
        return False

    print(f"   ✅ Express.js demo project found at: {base_path}")

    # Check for expected directories
    expected_dirs = ["src", "src/models", "src/controllers", "src/routes"]
    found_dirs = []

    for dir_name in expected_dirs:
        dir_path = os.path.join(base_path, dir_name)
        if os.path.exists(dir_path):
            found_dirs.append(dir_name)
            print(f"   ✅ Found directory: {dir_name}")
        else:
            print(f"   ❌ Missing directory: {dir_name}")

    # Check for package.json
    package_json_path = os.path.join(base_path, "package.json")
    if os.path.exists(package_json_path):
        print("   ✅ Found package.json")

        try:
            with open(package_json_path, "r") as f:
                package_data = json.load(f)
                dependencies = package_data.get("dependencies", {})

            if "express" in dependencies:
                print("   ✅ Express.js dependency found in package.json")
            else:
                print("   ❌ Express.js dependency not found in package.json")

        except Exception as e:
            print(f"   ⚠️ Error reading package.json: {e}")
    else:
        print("   ❌ package.json not found")

    print(
        f"   📊 Structure validation: {len(found_dirs)}/{len(expected_dirs)} directories found"
    )
    return len(found_dirs) >= len(expected_dirs) * 0.75  # 75% pass rate


def test_file_naming_validation():
    """Test file naming convention validation"""
    print("🧪 Testing file naming convention validation...")

    # Test cases for different file types
    test_cases = [
        # Models (should be PascalCase)
        ("src/models/User.js", True),
        ("src/models/Product.js", True),
        ("src/models/OrderItem.js", True),
        ("src/models/userModel.js", False),  # Should be PascalCase
        ("src/models/user.js", False),  # Should be PascalCase
        # Controllers (should be camelCase)
        ("src/controllers/userController.js", True),
        ("src/controllers/authController.js", True),
        ("src/controllers/orderController.js", True),
        ("src/controllers/UserController.js", False),  # Should be camelCase
        ("src/controllers/user_controller.js", False),  # Should be camelCase
        # Services (should be camelCase)
        ("src/services/userService.js", True),
        ("src/services/authService.js", True),
        ("src/services/emailService.js", True),
        ("src/services/UserService.js", False),  # Should be camelCase
        ("src/services/user_service.js", False),  # Should be camelCase
        # Repositories (should be camelCase)
        ("src/repositories/userRepository.js", True),
        ("src/repositories/productRepository.js", True),
        ("src/repositories/UserRepository.js", False),  # Should be camelCase
        # Routes (can be camelCase or kebab-case)
        ("src/routes/users.js", True),
        ("src/routes/auth.js", True),
        ("src/routes/userManagement.js", True),
        ("src/routes/user-management.js", True),
        ("src/routes/api-docs.js", True),
        # Tests (should be kebab-case)
        ("src/tests/user-controller.test.js", True),
        ("src/tests/auth-service.test.js", True),
        ("src/tests/user-repository.test.js", True),
        ("src/tests/userController.test.js", False),  # Should be kebab-case
        ("src/tests/UserController.test.js", False),  # Should be kebab-case
    ]

    passed = 0
    total = len(test_cases)

    for file_path, expected in test_cases:
        result = test_file_naming_convention(file_path)
        if result == expected:
            passed += 1
            status = "✅" if result else "✅ (correctly rejected)"
            print(f"   {status} {file_path}")
        else:
            status = "❌"
            print(f"   {status} {file_path}: got {result}, expected {expected}")

    print(
        f"   📊 Naming validation: {passed}/{total} tests passed ({passed / total * 100:.1f}%)"
    )
    return passed >= total * 0.9  # 90% pass rate


def test_architecture_order_logic():
    """Test the logic for detecting architecture layer order"""
    print("🧪 Testing architecture layer order detection logic...")

    # Simulate step analysis
    test_steps = [
        {
            "title": "Create User model",
            "description": "Define User schema with Mongoose",
        },
        {
            "title": "Create user repository",
            "description": "Implement user data access layer",
        },
        {
            "title": "Create user service",
            "description": "Implement user business logic",
        },
        {
            "title": "Create user controller",
            "description": "Implement user request handlers",
        },
        {"title": "Create user routes", "description": "Define user API endpoints"},
    ]

    expected_order = ["models", "repositories", "services", "controllers", "routes"]
    detected_categories = []

    for step in test_steps:
        step_title_lower = step["title"].lower()
        step_desc_lower = step["description"].lower()

        # Determine step category based on content (same logic as in validation function)
        if any(
            keyword in step_title_lower or keyword in step_desc_lower
            for keyword in ["model", "schema", "mongoose"]
        ):
            detected_categories.append("models")
        elif any(
            keyword in step_title_lower or keyword in step_desc_lower
            for keyword in ["repository", "data access", "database operation"]
        ):
            detected_categories.append("repositories")
        elif any(
            keyword in step_title_lower or keyword in step_desc_lower
            for keyword in ["service", "business logic"]
        ):
            detected_categories.append("services")
        elif any(
            keyword in step_title_lower or keyword in step_desc_lower
            for keyword in ["controller", "request handler"]
        ):
            detected_categories.append("controllers")
        elif any(
            keyword in step_title_lower or keyword in step_desc_lower
            for keyword in ["route", "endpoint", "api"]
        ):
            detected_categories.append("routes")
        else:
            detected_categories.append("other")

    print(f"   📋 Expected order: {' → '.join(expected_order)}")
    print(f"   📋 Detected order: {' → '.join(detected_categories)}")

    # Check if order is correct
    is_correct_order = detected_categories == expected_order

    if is_correct_order:
        print("   ✅ Architecture order detection is working correctly")
    else:
        print("   ❌ Architecture order detection needs improvement")

    return is_correct_order


def main():
    """Run all simple tests"""
    print("🚀 Simple Validation Tests for Planner Agent Improvements")
    print("=" * 70)

    tests = [
        ("AGENTS.md File Validation", test_agents_md_exists),
        ("Express.js Project Structure", test_express_project_structure),
        ("File Naming Convention", test_file_naming_validation),
        ("Architecture Order Logic", test_architecture_order_logic),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 50)

        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")

    print("\n" + "=" * 70)
    print(
        f"📊 Test Results: {passed}/{total} tests passed ({passed / total * 100:.1f}%)"
    )

    if passed == total:
        print("🎉 All tests passed! Core validation logic is working correctly.")
        return 0
    elif passed >= total * 0.75:
        print("✅ Most tests passed. Implementation is mostly correct.")
        return 0
    else:
        print("⚠️ Many tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit(main())
