"""
Test script to check FRONTEND_PROMPT formatting and output
"""

from implementor.utils.prompts import FRONTEND_PROMPT

# Test data
test_agent_md = "# Architecture Guidelines\nUse React with TypeScript"
test_step_info = "Step 1: Create login page"
test_substep_info = "Sub-step 1.1: Create LoginForm component"

# Format the prompt
try:
    formatted_prompt = FRONTEND_PROMPT.format(
        agent_md=test_agent_md,
        step_info=test_step_info,
        substep_info=test_substep_info
    )

    print("=" * 80)
    print("FRONTEND_PROMPT FORMATTING TEST")
    print("=" * 80)
    print("\n✅ Prompt formatted successfully!\n")

    # Check for common issues
    issues = []

    if "\\n" in formatted_prompt:
        issues.append("⚠️ Found escaped newlines (\\n) in prompt")
        # Count occurrences
        count = formatted_prompt.count("\\n")
        issues.append(f"   Found {count} occurrences of \\n")

    if "{agent_md}" in formatted_prompt:
        issues.append("❌ Placeholder {agent_md} not replaced")

    if "{step_info}" in formatted_prompt:
        issues.append("❌ Placeholder {step_info} not replaced")

    if "{substep_info}" in formatted_prompt:
        issues.append("❌ Placeholder {substep_info} not replaced")

    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(issue)
    else:
        print("✅ No issues found!")

    # Show sample of formatted prompt
    print("\n" + "=" * 80)
    print("SAMPLE OUTPUT (first 1000 chars):")
    print("=" * 80)
    print(formatted_prompt[:1000])
    print("...")

    # Show examples section specifically
    print("\n" + "=" * 80)
    print("CHECKING EXAMPLES SECTION:")
    print("=" * 80)

    # Find str_replace_tool examples
    if "str_replace_tool" in formatted_prompt:
        start = formatted_prompt.find("str_replace_tool")
        sample = formatted_prompt[start:start+500]
        print(sample)

        if "\\n" in sample:
            print("\n⚠️ WARNING: Found \\n in str_replace_tool example!")
        else:
            print("\n✅ No \\n found in str_replace_tool example")

except KeyError as e:
    print(f"❌ KeyError: Missing placeholder {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
