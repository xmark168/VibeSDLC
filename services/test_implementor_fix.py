#!/usr/bin/env python3
"""
Test script để validate implementor agent improvements.
Kiểm tra rằng enhanced validation và file content verification hoạt động correctly.
"""


def test_basic_validation_logic():
    """Test basic validation logic without imports."""
    print("🧪 Testing basic validation logic...")

    # Sample User.js content (Mongoose model)
    user_model_content = """const mongoose = require('mongoose');

const UserSchema = new mongoose.Schema({
  email: {
    type: String,
    required: true,
    unique: true,
    trim: true,
    lowercase: true,
  },
  password: {
    type: String,
    required: true,
  },
  created_at: {
    type: Date,
    default: Date.now,
  },
});

const User = mongoose.model('User', UserSchema);

module.exports = User;"""

    # Test: Check if OLD_CODE exists in content
    old_code_to_find = "const { name, email, password } = req.body;"

    print(f"🔍 Looking for: {repr(old_code_to_find)}")
    print(f"📄 In file content ({len(user_model_content)} chars)")

    # Basic check
    found = old_code_to_find in user_model_content
    print(f"✅ Found in content: {found}")

    if not found:
        print("❌ OLD_CODE not found - this is the root cause of the error!")
        print("💡 This confirms the issue: agent is trying to modify wrong file")

        # Analyze file content
        if (
            "mongoose" in user_model_content.lower()
            and "schema" in user_model_content.lower()
        ):
            print("📋 File analysis: This is a Mongoose model file")
            print("💡 Suggestion: Route handler code should be in controller files")

        # Show file preview
        lines = user_model_content.splitlines()
        print("\n📄 File content preview:")
        for i, line in enumerate(lines[:10], 1):
            print(f"  {i:2}: {line}")
        if len(lines) > 10:
            print("  ...")

    return not found  # Return True if we detected the issue correctly


def test_file_type_detection():
    """Test file type detection logic."""
    print("\n🧪 Testing file type detection...")

    # Test cases
    test_cases = [
        {
            "content": "const mongoose = require('mongoose');\nconst UserSchema = new mongoose.Schema({",
            "expected_type": "mongoose_model",
            "description": "Mongoose model file",
        },
        {
            "content": "const registerUser = async (req, res) => {\n  const { email } = req.body;",
            "expected_type": "controller",
            "description": "Controller file with req.body",
        },
        {
            "content": "app.get('/users', (req, res) => {\n  res.json(users);",
            "expected_type": "express_routes",
            "description": "Express routes file",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"  Test {i}: {test_case['description']}")

        content = test_case["content"]
        expected = test_case["expected_type"]

        # Simple detection logic
        detected_type = "unknown"
        if "mongoose" in content.lower() and "schema" in content.lower():
            detected_type = "mongoose_model"
        elif "req.body" in content and "res." in content:
            detected_type = "controller"
        elif "app.get" in content or "app.post" in content:
            detected_type = "express_routes"

        print(f"    Expected: {expected}")
        print(f"    Detected: {detected_type}")
        print(f"    ✅ Match: {detected_type == expected}")

    return True


def test_enhanced_validation():
    """Test enhanced validation với better error messages."""
    print("🧪 Testing enhanced validation...")

    # Sample User.js content (Mongoose model)
    user_model_content = """const mongoose = require('mongoose');

const UserSchema = new mongoose.Schema({
  email: {
    type: String,
    required: true,
    unique: true,
    trim: true,
    lowercase: true,
  },
  password: {
    type: String,
    required: true,
  },
  created_at: {
    type: Date,
    default: Date.now,
  },
});

const User = mongoose.model('User', UserSchema);

module.exports = User;"""

    # Test case: OLD_CODE không tồn tại (case gốc)
    validator = IncrementalModificationValidator(user_model_content)

    # Tạo modification với OLD_CODE không tồn tại
    modification = CodeModification(
        file_path="src/models/User.js",
        old_code="const { name, email, password } = req.body;",
        new_code="const { name, email, password } = req.body;\n// Enhanced validation",
        description="Add validation logic",
    )

    is_valid, error_message = validator.validate_modification(modification)

    print(f"✅ Validation result: {is_valid}")
    print("📝 Error message preview:")
    print(error_message[:200] + "..." if len(error_message) > 200 else error_message)

    # Verify enhanced error message contains helpful info
    assert not is_valid, "Should detect OLD_CODE not found"
    assert "❌ OLD_CODE not found in target file" in error_message
    assert "🔍 Looking for:" in error_message
    assert "📄 File content preview:" in error_message
    assert "💡 Hint:" in error_message

    print("✅ Enhanced validation test passed!")


def test_file_content_verification():
    """Test file content verification mechanism."""
    print("\n🧪 Testing file content verification...")

    # Sample User.js content (Mongoose model)
    user_model_content = """const mongoose = require('mongoose');

const UserSchema = new mongoose.Schema({
  email: { type: String, required: true },
  password: { type: String, required: true }
});

module.exports = mongoose.model('User', UserSchema);"""

    # Sample authController.js content
    auth_controller_content = """const User = require('../models/User');

const registerUser = async (req, res) => {
  const { name, email, password } = req.body;
  // Registration logic here
};

module.exports = { registerUser };"""

    # Test 1: Trying to modify model file with route handler code (should fail)
    print("  Test 1: Route handler code in model file...")

    modification_wrong_file = CodeModification(
        file_path="src/models/User.js",
        old_code="const { name, email, password } = req.body;",
        new_code="const { name, email, password } = req.body;\n// Enhanced validation",
        description="Add validation",
    )

    result = _verify_file_content_for_modifications(
        "src/models/User.js", user_model_content, [modification_wrong_file]
    )

    print(f"    Result: {result['valid']}")
    print(f"    Reason: {result['reason']}")
    if "suggestions" in result:
        print(f"    Suggestions: {len(result['suggestions'])} items")

    assert not result["valid"], "Should detect wrong file type modification"
    assert "OLD_CODE not found" in result["reason"]

    # Test 2: Correct modification in controller file (should pass)
    print("  Test 2: Correct modification in controller file...")

    modification_correct_file = CodeModification(
        file_path="src/controllers/authController.js",
        old_code="const { name, email, password } = req.body;",
        new_code="const { name, email, password } = req.body;\n  // Enhanced validation",
        description="Add validation",
    )

    result = _verify_file_content_for_modifications(
        "src/controllers/authController.js",
        auth_controller_content,
        [modification_correct_file],
    )

    print(f"    Result: {result['valid']}")
    print(f"    Reason: {result['reason']}")

    assert result["valid"], "Should allow correct modification"

    print("✅ File content verification test passed!")


def test_file_analysis():
    """Test file type analysis."""
    print("\n🧪 Testing file analysis...")

    # Test Mongoose model detection
    model_content = "const mongoose = require('mongoose');\nconst UserSchema = new mongoose.Schema({"
    analysis = _analyze_file_type_and_content("src/models/User.js", model_content)

    print(f"  Model file analysis: {analysis['content_type']}")
    assert analysis["content_type"] == "mongoose_model"

    # Test controller detection
    controller_content = (
        "const registerUser = async (req, res) => {\n  const { email } = req.body;"
    )
    analysis = _analyze_file_type_and_content(
        "src/controllers/auth.js", controller_content
    )

    print(f"  Controller file analysis: {analysis['content_type']}")
    assert analysis["content_type"] == "controller"

    print("✅ File analysis test passed!")


def test_suggestions():
    """Test suggestion generation."""
    print("\n🧪 Testing suggestion generation...")

    model_content = "const mongoose = require('mongoose');\nconst UserSchema = new mongoose.Schema({"
    file_analysis = _analyze_file_type_and_content("src/models/User.js", model_content)

    suggestions = _suggest_alternatives_for_missing_code(
        "const { name, email, password } = req.body;", model_content, file_analysis
    )

    print(f"  Generated {len(suggestions)} suggestions")
    for i, suggestion in enumerate(suggestions):
        print(f"    {i + 1}. {suggestion}")

    # Verify suggestions contain helpful guidance
    suggestion_text = " ".join(suggestions)
    assert "controller" in suggestion_text.lower() or "route" in suggestion_text.lower()

    print("✅ Suggestion generation test passed!")


def main():
    """Run all tests."""
    print("🚀 Starting implementor agent fix validation tests...\n")

    try:
        test_enhanced_validation()
        test_file_content_verification()
        test_file_analysis()
        test_suggestions()

        print(
            "\n🎉 All tests passed! Implementor agent improvements are working correctly."
        )
        print("\n📋 Summary of improvements:")
        print("  ✅ Enhanced validation với detailed error messages")
        print("  ✅ File content verification để detect wrong file modifications")
        print("  ✅ File type analysis để understand content purpose")
        print("  ✅ Intelligent suggestions để guide developers")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
