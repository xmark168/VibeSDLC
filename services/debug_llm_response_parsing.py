#!/usr/bin/env python3
"""
Debug script để analyze LLM response parsing issues trong Developer Agent
"""

import sys
import re

# Add the path to import modules
sys.path.append("ai-agent-service/app/agents/developer/implementor/utils")

from incremental_modifications import parse_structured_modifications


def test_llm_response_parsing():
    """Test parsing với different LLM response formats"""

    print("🔍 Testing LLM Response Parsing Issues")
    print("=" * 60)

    # Test case 1: Valid structured format
    print("\n🧪 Test 1: Valid structured format")
    valid_response = """
MODIFICATION #1:
FILE: src/routes/authRoutes.js
DESCRIPTION: Add login endpoint

OLD_CODE:
```javascript
export default router;
```

NEW_CODE:
```javascript
router.post('/login', async (req, res) => {
    // login logic here
});

export default router;
```
"""

    try:
        modifications = parse_structured_modifications(valid_response)
        print(f"   ✅ Parsed {len(modifications)} modifications")
        if modifications:
            print(f"   📄 File: {modifications[0].file_path}")
            print(f"   📝 Description: {modifications[0].description}")
            print(f"   🔍 OLD_CODE: {repr(modifications[0].old_code[:50])}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test case 2: Invalid OLD_CODE format (likely cause of error)
    print("\n🧪 Test 2: Invalid OLD_CODE format")
    invalid_response = """
MODIFICATION #1:
FILE: src/routes/authRoutes.js
DESCRIPTION: Add login endpoint

OLD_CODE:
  // existing register logic

NEW_CODE:
```javascript
router.post('/login', async (req, res) => {
    // login logic here
});
```
"""

    try:
        modifications = parse_structured_modifications(invalid_response)
        print(f"   ✅ Parsed {len(modifications)} modifications")
        if modifications:
            print(f"   📄 File: {modifications[0].file_path}")
            print(f"   🔍 OLD_CODE: {repr(modifications[0].old_code[:50])}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test case 3: Missing code blocks
    print("\n🧪 Test 3: Missing code blocks")
    missing_blocks_response = """
MODIFICATION #1:
FILE: src/routes/authRoutes.js
DESCRIPTION: Add login endpoint

OLD_CODE:
export default router;

NEW_CODE:
router.post('/login', async (req, res) => {
    // login logic here
});

export default router;
"""

    try:
        modifications = parse_structured_modifications(missing_blocks_response)
        print(f"   ✅ Parsed {len(modifications)} modifications")
        if modifications:
            print(f"   📄 File: {modifications[0].file_path}")
            print(f"   🔍 OLD_CODE: {repr(modifications[0].old_code[:50])}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test case 4: Mixed format (some valid, some invalid)
    print("\n🧪 Test 4: Mixed format")
    mixed_response = """
MODIFICATION #1:
FILE: src/routes/authRoutes.js
DESCRIPTION: Add login endpoint

OLD_CODE:
```javascript
export default router;
```

NEW_CODE:
```javascript
router.post('/login', async (req, res) => {
    // login logic here
});

export default router;
```

MODIFICATION #2:
FILE: src/controllers/authController.js
DESCRIPTION: Add helper function

OLD_CODE:
  // existing register logic

NEW_CODE:
```javascript
function validateInput(data) {
    return true;
}
```
"""

    try:
        modifications = parse_structured_modifications(mixed_response)
        print(f"   ✅ Parsed {len(modifications)} modifications")
        for i, mod in enumerate(modifications):
            print(f"   📄 Modification {i + 1}: {mod.file_path}")
            print(f"      🔍 OLD_CODE: {repr(mod.old_code[:30])}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_regex_patterns():
    """Test regex patterns used in parsing"""

    print("\n🔍 Testing Regex Patterns")
    print("=" * 60)

    # Test OLD_CODE regex
    old_code_pattern = r"OLD_CODE:\s*```\w*\n(.*?)\n```"

    test_cases = [
        (
            "Valid with language",
            "OLD_CODE:\n```javascript\nexport default router;\n```",
        ),
        ("Valid without language", "OLD_CODE:\n```\nexport default router;\n```"),
        ("Invalid - no code blocks", "OLD_CODE:\nexport default router;"),
        (
            "Invalid - missing newlines",
            "OLD_CODE:```javascript\nexport default router;\n```",
        ),
    ]

    for test_name, test_input in test_cases:
        print(f"\n🧪 {test_name}")
        print(f"   Input: {repr(test_input)}")

        match = re.search(old_code_pattern, test_input, re.DOTALL)
        if match:
            print(f"   ✅ Match found: {repr(match.group(1))}")
        else:
            print("   ❌ No match found")


def test_actual_error_case():
    """Test the actual error case from logs"""

    print("\n🔍 Testing Actual Error Case")
    print("=" * 60)

    # This is likely what LLM generated based on error message
    error_case_response = """
MODIFICATION #1:
FILE: src/routes/authRoutes.js
DESCRIPTION: Add login endpoint

OLD_CODE:
  // existing register logic

NEW_CODE:
```javascript
router.post('/login', async (req, res) => {
    const { email, password } = req.body;

    if (!email || !password) {
        return res.status(400).json({ message: 'Email and password are required.' });
    }

    try {
        const user = await User.findOne({ email });
        if (!user) {
            return res.status(401).json({ message: 'Invalid email or password.' });
        }

        const isMatch = await bcrypt.compare(password, user.password);
        if (!isMatch) {
            return res.status(401).json({ message: 'Invalid email or password.' });
        }

        const token = jwt.sign(
            { id: user._id, email: user.email },
            process.env.JWT_SECRET,
            { expiresIn: '1h' }
        );

        res.status(200).json({ token });
    } catch (error) {
        console.error(error);
        res.status(500).json({ message: 'Internal server error.' });
    }
});

  // existing register logic
```
"""

    print("🧪 Testing error case response (WITH ENHANCED DEBUG)")
    print(f"   Response length: {len(error_case_response)} chars")

    try:
        modifications = parse_structured_modifications(error_case_response)
        print(f"   ✅ Parsed {len(modifications)} modifications")

        if modifications:
            mod = modifications[0]
            print(f"   📄 File: {mod.file_path}")
            print(f"   📝 Description: {mod.description}")
            print(f"   🔍 OLD_CODE length: {len(mod.old_code)} chars")
            print(f"   🔍 OLD_CODE content: {repr(mod.old_code)}")
            print(f"   🔍 NEW_CODE length: {len(mod.new_code)} chars")
        else:
            print("   ⚠️ No modifications parsed - likely rejected as placeholder")

    except Exception as e:
        print(f"   ❌ Error parsing: {e}")
        import traceback

        traceback.print_exc()


def test_debug_actual_error_string():
    """Test với exact error string từ logs"""

    print("\n🔍 Testing Debug Actual Error String")
    print("=" * 60)

    # Exact error string từ logs
    error_string = "\n  // existing register logic\n"

    print(f"🧪 Testing exact error string: {repr(error_string)}")

    # Test placeholder detection
    from incremental_modifications import _is_placeholder_code

    is_placeholder = _is_placeholder_code(error_string)
    print(f"   🔍 Is placeholder: {is_placeholder}")

    # Test if this would be extracted by any pattern
    test_block = f"""
FILE: src/app.js
DESCRIPTION: Add something

OLD_CODE:{error_string}

NEW_CODE:
```javascript
// some new code
```
"""

    print("   🧪 Testing extraction from block:")
    print(f"   📄 Block: {repr(test_block[:200])}")

    # Test pattern 2 (without code blocks)
    import re

    old_code_match = re.search(
        r"OLD_CODE:\s*\n(.*?)(?=\n\s*NEW_CODE:)", test_block, re.DOTALL
    )
    if old_code_match:
        extracted = old_code_match.group(1).strip()
        print(f"   ✅ Pattern 2 extracted: {repr(extracted)}")
        print(f"   🔍 Is placeholder: {_is_placeholder_code(extracted)}")
    else:
        print("   ❌ Pattern 2 failed to extract")

    # Test pattern 3 (single line)
    old_code_match = re.search(r"OLD_CODE:\s*(.+)", test_block)
    if old_code_match:
        extracted = old_code_match.group(1).strip()
        print(f"   ✅ Pattern 3 extracted: {repr(extracted)}")
        print(f"   🔍 Is placeholder: {_is_placeholder_code(extracted)}")
    else:
        print("   ❌ Pattern 3 failed to extract")


def test_enhanced_parsing():
    """Test enhanced parsing với various formats"""

    print("\n🔍 Testing Enhanced Parsing Logic")
    print("=" * 60)

    test_cases = [
        {
            "name": "Valid with code blocks",
            "response": """
MODIFICATION #1:
FILE: src/routes/authRoutes.js
DESCRIPTION: Add login endpoint

OLD_CODE:
```javascript
export default router;
```

NEW_CODE:
```javascript
router.post('/login', async (req, res) => {
    // login logic
});

export default router;
```
""",
        },
        {
            "name": "Missing code blocks (should work now)",
            "response": """
MODIFICATION #1:
FILE: src/routes/authRoutes.js
DESCRIPTION: Add login endpoint

OLD_CODE:
export default router;

NEW_CODE:
router.post('/login', async (req, res) => {
    // login logic
});

export default router;
""",
        },
        {
            "name": "Placeholder OLD_CODE (should be rejected)",
            "response": """
MODIFICATION #1:
FILE: src/routes/authRoutes.js
DESCRIPTION: Add login endpoint

OLD_CODE:
  // existing register logic

NEW_CODE:
```javascript
router.post('/login', async (req, res) => {
    // login logic
});
```
""",
        },
        {
            "name": "Mixed valid and placeholder",
            "response": """
MODIFICATION #1:
FILE: src/routes/authRoutes.js
DESCRIPTION: Add login endpoint

OLD_CODE:
export default router;

NEW_CODE:
router.post('/login', async (req, res) => {
    // login logic
});

export default router;

MODIFICATION #2:
FILE: src/controllers/authController.js
DESCRIPTION: Add helper

OLD_CODE:
  // existing code

NEW_CODE:
function helper() {
    return true;
}
""",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")

        try:
            modifications = parse_structured_modifications(test_case["response"])
            print(f"   ✅ Parsed {len(modifications)} modifications")

            for j, mod in enumerate(modifications):
                print(f"   📄 Modification {j + 1}: {mod.file_path}")
                print(f"      🔍 OLD_CODE: {repr(mod.old_code[:30])}")
                print(f"      📝 Description: {mod.description}")

        except Exception as e:
            print(f"   ❌ Error: {e}")


def main():
    """Main debug function"""

    print("🚀 LLM Response Parsing Debug")
    print("=" * 80)

    tests = [
        test_llm_response_parsing,
        test_regex_patterns,
        test_actual_error_case,
        test_debug_actual_error_string,
        test_enhanced_parsing,
    ]

    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("📊 DEBUG SUMMARY")
    print("=" * 80)

    print("\n🎯 Likely Root Causes:")
    print("1. 🔍 LLM generates OLD_CODE without proper code block formatting")
    print("2. 🔍 OLD_CODE contains comments that don't exist in actual file")
    print(
        "3. 🔍 Regex pattern requires ```language``` blocks but LLM doesn't provide them"
    )
    print("4. 🔍 LLM generates placeholder comments instead of actual code")

    print("\n💡 Potential Solutions:")
    print("1. 🔧 Enhance regex patterns để handle missing code blocks")
    print("2. 🔧 Add fallback parsing for non-structured format")
    print("3. 🔧 Improve prompt engineering để ensure proper code block formatting")
    print("4. 🔧 Add validation để reject placeholder comments as OLD_CODE")

    print("\n🚀 Next Steps:")
    print("1. 📊 Run this debug script để identify exact parsing issues")
    print("2. 🔧 Fix regex patterns hoặc parsing logic")
    print("3. 🧪 Test với actual LLM responses")
    print("4. ✅ Verify file modification workflow completes")


if __name__ == "__main__":
    main()
