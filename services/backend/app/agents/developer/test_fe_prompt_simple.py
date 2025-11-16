"""
Simple test script to check FRONTEND_PROMPT formatting
"""

# Read the prompts.py file directly
with open("implementor/utils/prompts.py", "r", encoding="utf-8") as f:
    content = f.read()

# Extract FRONTEND_PROMPT
start = content.find('FRONTEND_PROMPT = r"""')
end = content.find('"""', start + 25)
frontend_prompt = content[start+22:end]

print("=" * 80)
print("FRONTEND_PROMPT ANALYSIS")
print("=" * 80)

# Test formatting
test_agent_md = "# Architecture Guidelines\nUse React with TypeScript"
test_step_info = "Step 1: Create login page"
test_substep_info = "Sub-step 1.1: Create LoginForm component"

try:
    formatted_prompt = frontend_prompt.format(
        agent_md=test_agent_md,
        step_info=test_step_info,
        substep_info=test_substep_info
    )

    print("\n✅ Prompt formatted successfully!\n")

    # Check for issues
    issues = []

    # Check for escaped newlines in examples
    if "\\n" in formatted_prompt:
        count = formatted_prompt.count("\\n")
        issues.append(f"⚠️ Found {count} escaped newlines (\\n) in formatted prompt")

        # Find where they are
        lines = formatted_prompt.split("\n")
        for i, line in enumerate(lines):
            if "\\n" in line and ("str_replace_tool" in line or "write_file_tool" in line):
                issues.append(f"   Line {i}: {line[:80]}...")

    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(issue)
    else:
        print("✅ No \\n issues found!")

    # Show str_replace_tool examples
    print("\n" + "=" * 80)
    print("STR_REPLACE_TOOL EXAMPLES:")
    print("=" * 80)

    lines = formatted_prompt.split("\n")
    in_example = False
    example_lines = []

    for line in lines:
        if "str_replace_tool(" in line:
            in_example = True
            example_lines = [line]
        elif in_example:
            example_lines.append(line)
            if ")" in line and len(example_lines) > 3:
                # Print this example
                example_text = "\n".join(example_lines)
                print(example_text)
                print()

                if "\\n" in example_text:
                    print("⚠️ WARNING: This example contains \\n")
                else:
                    print("✅ This example looks good")
                print("-" * 40)

                in_example = False
                example_lines = []

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
