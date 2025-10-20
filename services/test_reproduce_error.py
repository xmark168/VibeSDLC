#!/usr/bin/env python3
"""
Test script để reproduce exact error từ logs
"""

import os
import sys

# Add the path to import modules
sys.path.append("ai-agent-service/app/agents/developer/implementor/utils")
sys.path.append("ai-agent-service/app/agents/developer/implementor/nodes")
sys.path.append("ai-agent-service/app/agents/developer/implementor")

from incremental_modifications import (
    parse_structured_modifications,
    IncrementalModificationValidator,
)


# Create simple FileChange class for testing
class FileChange:
    def __init__(self, file_path, change_type, description):
        self.file_path = file_path
        self.change_type = change_type
        self.description = description
        self.structured_modifications = None


def test_reproduce_exact_error():
    """Reproduce exact error scenario từ logs"""

    print("🔍 Testing Exact Error Reproduction")
    print("=" * 60)

    # Simulate exact scenario từ logs
    print("\n🧪 Test Case: LLM generates placeholder OLD_CODE")

    # This is likely what LLM generated
    llm_response = """
MODIFICATION #1:
FILE: src/app.js
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

    print(f"   📄 LLM Response length: {len(llm_response)} chars")

    # Test 1: Parse structured modifications
    print("\n   🧪 Step 1: Parse structured modifications")
    try:
        modifications = parse_structured_modifications(llm_response)
        print(f"      ✅ Parsed {len(modifications)} modifications")

        if not modifications:
            print(
                "      💡 No modifications parsed (expected due to placeholder rejection)"
            )
            return "NO_MODIFICATIONS_PARSED"

    except Exception as e:
        print(f"      ❌ Error in parsing: {e}")
        print(f"      🔍 Error type: {type(e)}")
        print(f"      🔍 Error string: {repr(str(e))}")

        # Check if error string matches logs
        if str(e) == "\n  // existing register logic\n":
            print("      🎯 FOUND EXACT ERROR MATCH!")
            return "EXACT_ERROR_MATCH"

        import traceback

        traceback.print_exc()
        return "PARSING_ERROR"

    # Test 2: Apply modifications (if any)
    if modifications:
        print("\n   🧪 Step 2: Apply modifications")

        # Read actual file content
        app_js_path = (
            "ai-agent-service/app/agents/demo/be/nodejs/express-basic/src/app.js"
        )
        if os.path.exists(app_js_path):
            with open(app_js_path, "r", encoding="utf-8") as f:
                file_content = f.read()

            print(f"      📄 File content length: {len(file_content)} chars")

            try:
                validator = IncrementalModificationValidator(file_content)
                result = validator.apply_multiple_modifications(modifications)

                if result.success:
                    print(
                        f"      ✅ Applied {result.modifications_applied} modifications"
                    )
                    return "MODIFICATIONS_APPLIED"
                else:
                    print("      ❌ Modifications failed:")
                    for error in result.errors:
                        print(f"         {error}")
                    return "MODIFICATIONS_FAILED"

            except Exception as e:
                print(f"      ❌ Error in validation: {e}")
                print(f"      🔍 Error type: {type(e)}")
                print(f"      🔍 Error string: {repr(str(e))}")

                # Check if error string matches logs
                if str(e) == "\n  // existing register logic\n":
                    print("      🎯 FOUND EXACT ERROR MATCH IN VALIDATION!")
                    return "VALIDATION_ERROR_MATCH"

                import traceback

                traceback.print_exc()
                return "VALIDATION_ERROR"
        else:
            print(f"      ❌ File not found: {app_js_path}")
            return "FILE_NOT_FOUND"

    return "SUCCESS"


def test_simulate_generate_code_flow():
    """Simulate exact flow trong generate_code.py"""

    print("\n🔍 Testing Generate Code Flow Simulation")
    print("=" * 60)

    # Simulate FileChange object
    file_change = FileChange(
        file_path="src/app.js",
        change_type="incremental",
        description="Add login endpoint",
    )

    # Simulate LLM response với placeholder OLD_CODE
    llm_response = """
MODIFICATION #1:
FILE: src/app.js
DESCRIPTION: Add login endpoint

OLD_CODE:
  // existing register logic

NEW_CODE:
```javascript
// some new code here
```
"""

    print("🧪 Simulating generate_code.py flow:")

    try:
        # Step 1: Check if structured format
        if "MODIFICATION #" in llm_response and "OLD_CODE:" in llm_response:
            print("   ✅ Structured format detected")

            # Step 2: Store in file_change
            file_change.structured_modifications = llm_response
            print("   ✅ Stored structured modifications")

            # Step 3: Return signal
            result = "STRUCTURED_MODIFICATIONS"
            print(f"   ✅ Returned: {result}")

            return result
        else:
            print("   ❌ Non-structured format")
            return "NON_STRUCTURED"

    except Exception as e:
        print(f"   ❌ Error in generate_code flow: {e}")
        print(f"   🔍 Error type: {type(e)}")
        print(f"   🔍 Error string: {repr(str(e))}")

        # Check if error string matches logs
        if str(e) == "\n  // existing register logic\n":
            print("   🎯 FOUND EXACT ERROR MATCH IN GENERATE_CODE!")
            return "GENERATE_CODE_ERROR_MATCH"

        import traceback

        traceback.print_exc()
        return "GENERATE_CODE_ERROR"


def test_check_exception_sources():
    """Check possible sources của exception string"""

    print("\n🔍 Testing Exception Sources")
    print("=" * 60)

    error_string = "\n  // existing register logic\n"

    print(f"🧪 Looking for sources of error string: {repr(error_string)}")

    # Test 1: Direct string comparison
    test_strings = [
        "  // existing register logic",
        "\n  // existing register logic\n",
        "// existing register logic",
        "existing register logic",
    ]

    for test_str in test_strings:
        if test_str == error_string.strip():
            print(f"   ✅ Match found: {repr(test_str)}")
        else:
            print(f"   ❌ No match: {repr(test_str)}")

    # Test 2: Check if error could come from regex extraction
    import re

    test_block = f"""
FILE: src/app.js
DESCRIPTION: Add something

OLD_CODE:{error_string}

NEW_CODE:
```javascript
// some code
```
"""

    print("\n   🧪 Testing regex extraction:")

    # Pattern 2 (without code blocks)
    old_code_match = re.search(
        r"OLD_CODE:\s*\n(.*?)(?=\n\s*NEW_CODE:)", test_block, re.DOTALL
    )
    if old_code_match:
        extracted = old_code_match.group(1)
        print(f"      Pattern 2 extracted: {repr(extracted)}")
        if extracted == error_string.strip():
            print("      🎯 EXACT MATCH - This could be the source!")

    # Pattern 3 (single line)
    old_code_match = re.search(r"OLD_CODE:\s*(.+)", test_block)
    if old_code_match:
        extracted = old_code_match.group(1)
        print(f"      Pattern 3 extracted: {repr(extracted)}")
        if extracted == error_string.strip():
            print("      🎯 EXACT MATCH - This could be the source!")


def main():
    """Main test function"""

    print("🚀 Error Reproduction Test")
    print("=" * 80)

    tests = [
        test_reproduce_exact_error,
        test_simulate_generate_code_flow,
        test_check_exception_sources,
    ]

    results = {}

    for test_func in tests:
        try:
            result = test_func()
            results[test_func.__name__] = result
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
            results[test_func.__name__] = f"FAILED: {e}"

            # Check if this is the exact error
            if str(e) == "\n  // existing register logic\n":
                print("🎯 FOUND EXACT ERROR MATCH IN TEST!")
                results[test_func.__name__] = "EXACT_ERROR_MATCH"

    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)

    for test_name, result in results.items():
        print(f"   {test_name}: {result}")

    print("\n🎯 Analysis:")
    if any("EXACT_ERROR_MATCH" in str(result) for result in results.values()):
        print("   ✅ Found exact error match - identified source!")
    else:
        print("   ❌ No exact error match found - need more investigation")

    print("\n💡 Next Steps:")
    print("   1. Run actual Developer Agent với enhanced debug logging")
    print("   2. Capture full LLM response và processing flow")
    print("   3. Identify exact line where exception is thrown")
    print("   4. Fix root cause based on findings")


if __name__ == "__main__":
    main()
