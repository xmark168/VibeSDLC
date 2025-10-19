"""
Simulate exact workflow conditions for auth.py modification
"""

import shutil
import tempfile
from pathlib import Path


def simulate_workflow_auth_modification():
    """Simulate the exact workflow conditions that might cause auth.py modification to fail."""
    print("🧪 Simulating workflow auth.py modification...")

    # Create temp directory to simulate working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        # Create directory structure like in workflow
        app_dir = temp_dir / "app" / "services"
        app_dir.mkdir(parents=True)

        # Copy actual auth.py to temp location
        source_auth = Path("app/agents/demo/app/services/auth.py")
        target_auth = app_dir / "auth.py"

        if source_auth.exists():
            shutil.copy2(source_auth, target_auth)
            print(f"📄 Copied auth.py to: {target_auth}")
        else:
            print(f"❌ Source file not found: {source_auth}")
            return False

        # Simulate different working directory scenarios
        test_scenarios = [
            {
                "name": "Workflow working directory (app/agents/demo)",
                "working_dir": str(temp_dir),
                "file_path": "app/services/auth.py",
            },
            {
                "name": "Absolute path",
                "working_dir": str(temp_dir),
                "file_path": str(target_auth),
            },
            {
                "name": "Relative from app directory",
                "working_dir": str(temp_dir / "app"),
                "file_path": "services/auth.py",
            },
        ]

        for scenario in test_scenarios:
            print(f"\\n🧪 Testing scenario: {scenario['name']}")
            print(f"    Working dir: {scenario['working_dir']}")
            print(f"    File path: {scenario['file_path']}")

            # Test file reading
            try:
                # Simulate read_file_tool
                working_dir = Path(scenario["working_dir"])
                file_path = scenario["file_path"]

                if file_path.startswith("/") or ":" in file_path:
                    # Absolute path
                    full_path = Path(file_path)
                else:
                    # Relative path
                    full_path = working_dir / file_path

                print(f"    Full path: {full_path}")
                print(f"    File exists: {full_path.exists()}")

                if not full_path.exists():
                    print("    ❌ File not found")
                    continue

                # Read file content
                content = full_path.read_text()
                print(f"    File size: {len(content)} chars")

                # Simulate formatted content (cat -n)
                lines = content.split("\\n")
                formatted_lines = []
                for i, line in enumerate(lines, 1):
                    formatted_lines.append(f"{i:6d}\\t{line}")
                formatted_content = "\\n".join(formatted_lines)

                # Find insertion point
                insertion_point = find_insertion_point(formatted_content)

                if insertion_point:
                    print(
                        f"    ✅ Found insertion point at line {insertion_point['line']}"
                    )

                    # Test different types of generated content that might cause issues
                    test_contents = [
                        {
                            "name": "Normal content",
                            "content": "# Email verification implementation\\n        # TODO: Add token blacklist logic",
                        },
                        {
                            "name": "Content with line numbers (corrupted from LLM)",
                            "content": "   123\\t# Email verification implementation\\n   124\\t        # TODO: Add token blacklist logic",
                        },
                        {"name": "Empty content", "content": ""},
                        {
                            "name": "Content with special characters",
                            "content": "# Email verification\\n        token_blacklist = set()\\n        if token in token_blacklist:\\n            raise Exception('Token already blacklisted')",
                        },
                    ]

                    for test_content in test_contents:
                        print(f"\\n      🧪 Testing content: {test_content['name']}")

                        # Reset file
                        full_path.write_text(content)

                        # Apply indentation
                        indentation = " " * insertion_point["indentation"]
                        content_lines = test_content["content"].split("\\n")

                        indented_lines = []
                        for line in content_lines:
                            if line.strip():  # Non-empty line
                                indented_lines.append(indentation + line)
                            else:  # Empty line
                                indented_lines.append("")

                        indented_content = "\\n".join(indented_lines)

                        # Simulate edit_file_tool
                        old_str = insertion_point["original_line"]
                        new_str = indented_content

                        try:
                            current_content = full_path.read_text()

                            # Check if old_str exists
                            if old_str not in current_content:
                                print(f"        ❌ old_str not found: {repr(old_str)}")
                                continue

                            # Count occurrences
                            count = current_content.count(old_str)
                            if count > 1:
                                print(f"        ❌ Multiple occurrences: {count}")
                                continue

                            # Replace
                            new_content = current_content.replace(old_str, new_str)
                            full_path.write_text(new_content)

                            # Verify
                            verify_content = full_path.read_text()

                            # Check for corruption
                            has_line_numbers = any(
                                "\\t" in line and line.split("\\t")[0].strip().isdigit()
                                for line in verify_content.split("\\n")
                                if "\\t" in line
                            )

                            if has_line_numbers:
                                print(
                                    "        ⚠️ WARNING: Line numbers detected in result"
                                )
                            else:
                                print("        ✅ Edit successful, no corruption")

                        except Exception as e:
                            print(f"        ❌ Edit failed: {e}")

                else:
                    print("    ❌ No insertion point found")

            except Exception as e:
                print(f"    ❌ Scenario failed: {e}")

        return True


def find_insertion_point(formatted_content: str) -> dict | None:
    """Find insertion point (simplified version)."""
    # Extract actual content
    lines = formatted_content.split("\\n")
    actual_lines = []

    for line in lines:
        if not line.strip():
            actual_lines.append("")
            continue
        if "\\t" in line:
            actual_content = line.split("\\t", 1)[1]
            actual_lines.append(actual_content)
        else:
            actual_lines.append(line)

    actual_content = "\\n".join(actual_lines)
    content_lines = actual_content.split("\\n")

    # Find "pass" statement
    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if stripped == "pass":
            return {
                "type": "pass",
                "line": i + 1,
                "original_line": line,
                "indentation": len(line) - len(line.lstrip()),
                "pattern": "pass",
            }

    return None


def main():
    """Run workflow simulation test."""
    print("🚀 Simulating auth.py modification workflow...\\n")

    success = simulate_workflow_auth_modification()

    if success:
        print("\\n🎉 Workflow simulation completed!")
        print("\\n💡 Potential issues identified:")
        print("  1. Working directory path resolution")
        print("  2. Generated content with line numbers")
        print("  3. File path handling in different scenarios")
        print("\\n🔧 Recommendations:")
        print("  1. Ensure working directory is correctly set")
        print("  2. Clean generated content before applying")
        print("  3. Add better error logging in implement_files.py")
    else:
        print("\\n💥 Workflow simulation failed")


if __name__ == "__main__":
    main()
