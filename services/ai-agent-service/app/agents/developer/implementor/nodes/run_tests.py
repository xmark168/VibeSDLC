"""
Run Tests Node

Chạy tests để verify implementation nếu có test commands available.
"""

import subprocess
import time
from pathlib import Path

from langchain_core.messages import AIMessage

from ..state import ImplementorState, TestExecution
from ..utils.validators import validate_test_execution


def run_tests(state: ImplementorState) -> ImplementorState:
    """
    Chạy tests để verify implementation.

    Args:
        state: ImplementorState với implementation completed

    Returns:
        Updated ImplementorState với test results
    """
    try:
        print("🧪 Running tests...")

        # Determine working directory
        working_dir = state.codebase_path or "."
        working_path = Path(working_dir).resolve()

        # Detect test commands based on project type
        test_commands = _detect_test_commands(working_path, state.tech_stack)

        if not test_commands:
            print("⏭️  No test commands detected - skipping tests")
            state.current_phase = "commit_changes"
            state.tests_passed = True  # Assume OK if no tests

            message = AIMessage(
                content="⏭️  No test commands found - proceeding to commit"
            )
            state.messages.append(message)
            return state

        # Run the first available test command
        test_command = test_commands[0]
        print(f"  🏃 Running: {test_command}")

        # Execute test command
        start_time = time.time()
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=working_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            duration = time.time() - start_time

            # Create test execution record
            test_execution = TestExecution(
                test_command=test_command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration,
                passed=result.returncode == 0,
            )

            # Parse failed tests from output if available
            if result.returncode != 0:
                failed_tests = _parse_failed_tests(result.stdout, result.stderr)
                test_execution.failed_tests = failed_tests

            state.test_execution = test_execution
            state.tests_passed = result.returncode == 0

            # Validate test execution
            test_valid, test_issues = validate_test_execution(
                test_command, result.returncode, duration
            )
            if not test_valid:
                print(f"⚠️  Test validation issues: {'; '.join(test_issues)}")

            # Store result
            state.tools_output["test_execution"] = {
                "command": test_command,
                "exit_code": result.returncode,
                "duration": duration,
                "passed": result.returncode == 0,
                "failed_tests": test_execution.failed_tests,
            }

            if result.returncode == 0:
                print(f"  ✅ Tests passed ({duration:.1f}s)")
                message = AIMessage(
                    content=f"✅ Tests passed successfully\n"
                    f"- Command: {test_command}\n"
                    f"- Duration: {duration:.1f}s\n"
                    f"- Next: Commit changes"
                )
            else:
                print(f"  ❌ Tests failed ({duration:.1f}s)")
                message = AIMessage(
                    content=f"⚠️  Tests failed but proceeding\n"
                    f"- Command: {test_command}\n"
                    f"- Exit code: {result.returncode}\n"
                    f"- Failed tests: {len(test_execution.failed_tests)}\n"
                    f"- Next: Commit changes (tests can be fixed later)"
                )

            state.messages.append(message)

        except subprocess.TimeoutExpired:
            print("  ⏰ Tests timed out after 5 minutes")
            test_execution = TestExecution(
                test_command=test_command,
                exit_code=-1,
                stderr="Test execution timed out after 5 minutes",
                duration=300.0,
                passed=False,
            )
            state.test_execution = test_execution
            state.tests_passed = False

            message = AIMessage(content="⏰ Tests timed out - proceeding to commit")
            state.messages.append(message)

        except Exception as e:
            print(f"  ❌ Test execution error: {e}")
            test_execution = TestExecution(
                test_command=test_command,
                exit_code=-1,
                stderr=f"Test execution error: {str(e)}",
                duration=0.0,
                passed=False,
            )
            state.test_execution = test_execution
            state.tests_passed = False

            message = AIMessage(content=f"❌ Test execution error: {str(e)}")
            state.messages.append(message)

        # Always proceed to commit regardless of test results
        state.current_phase = "commit_changes"
        state.status = "tests_completed"

        return state

    except Exception as e:
        state.error_message = f"Test execution failed: {str(e)}"
        state.status = "error"

        message = AIMessage(content=f"❌ Test execution error: {str(e)}")
        state.messages.append(message)

        print(f"❌ Test execution failed: {e}")
        return state


def _detect_test_commands(working_path: Path, tech_stack: str) -> list[str]:
    """
    Detect available test commands based on project structure.

    Args:
        working_path: Path to project directory
        tech_stack: Technology stack

    Returns:
        List of test commands to try
    """
    commands = []

    # Python projects
    if tech_stack in ["python", "fastapi"] or any(working_path.glob("*.py")):
        if (working_path / "pyproject.toml").exists():
            commands.append("python -m pytest")
        elif (working_path / "requirements.txt").exists():
            commands.append("python -m pytest")
        elif (working_path / "setup.py").exists():
            commands.append("python -m pytest")
        else:
            commands.append("python -m pytest")  # Try anyway

    # Node.js projects
    if (
        tech_stack in ["nodejs", "nextjs", "react-vite", "express"]
        or (working_path / "package.json").exists()
    ):
        if (working_path / "package.json").exists():
            try:
                import json

                with open(working_path / "package.json") as f:
                    package_data = json.load(f)
                    scripts = package_data.get("scripts", {})
                    if "test" in scripts:
                        commands.append("npm test")
                    elif "test:unit" in scripts:
                        commands.append("npm run test:unit")
            except:
                pass
        commands.append("npm test")  # Fallback

    return commands


def _parse_failed_tests(stdout: str, stderr: str) -> list[str]:
    """
    Parse failed test names from test output.

    Args:
        stdout: Standard output from test command
        stderr: Standard error from test command

    Returns:
        List of failed test names
    """
    failed_tests = []

    # Combine output
    output = stdout + "\n" + stderr

    # Common patterns for failed tests
    patterns = [
        "FAILED ",
        "FAIL ",
        "✗ ",
        "× ",
        "ERROR ",
    ]

    for line in output.split("\n"):
        for pattern in patterns:
            if pattern in line:
                # Extract test name (basic parsing)
                test_name = line.strip()
                if test_name and test_name not in failed_tests:
                    failed_tests.append(test_name)
                break

    return failed_tests[:10]  # Limit to first 10 failed tests
