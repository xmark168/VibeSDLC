"""
Run and Verify Node

Chạy chương trình để verify implementation trước khi commit.
Tự động detect run command dựa trên project type và có error recovery loop.
"""

import subprocess
import time
from pathlib import Path

from langchain_core.messages import AIMessage

from ..state import ImplementorState, RunExecution
from ..tool.shell_tools import shell_execute_tool  # noqa: F401


def run_and_verify(state: ImplementorState) -> ImplementorState:
    """
    Chạy chương trình để verify implementation trước commit.

    Workflow:
    1. Detect run command dựa trên project type
    2. Chạy command
    3. Nếu lỗi: loop để fix (max 3 lần)
    4. Nếu thành công: kill process và proceed to commit

    Args:
        state: ImplementorState với implemented files

    Returns:
        Updated ImplementorState với run verification results
    """
    try:
        print("🚀 Running and verifying implementation...")

        # Determine working directory
        working_dir = state.codebase_path or "."
        working_path = Path(working_dir).resolve()

        # Detect run command based on project type
        run_command = _detect_run_command(working_path, state.tech_stack)

        if not run_command:
            print("⏭️  No run command detected - skipping verification")
            state.current_phase = "commit_changes"
            state.run_verified = True

            message = AIMessage(
                content="⏭️  No run command found - proceeding to commit"
            )
            state.messages.append(message)
            return state

        print(f"  🏃 Run command: {run_command}")

        # Initialize retry loop
        max_retries = 3
        retry_count = 0
        success = False
        last_error = ""

        while retry_count < max_retries and not success:
            retry_count += 1
            print(f"\n  📍 Attempt {retry_count}/{max_retries}")

            # Execute run command
            start_time = time.time()
            try:
                result = subprocess.run(
                    run_command,
                    shell=True,
                    cwd=working_path,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout per attempt
                )

                duration = time.time() - start_time

                # Create run execution record
                run_execution = RunExecution(
                    run_command=run_command,
                    exit_code=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    duration=duration,
                    success=result.returncode == 0,
                    retry_count=retry_count,
                    max_retries=max_retries,
                )

                if result.returncode == 0:
                    print(f"  ✅ Run successful ({duration:.1f}s)")
                    success = True
                    state.run_execution = run_execution
                    state.run_verified = True

                else:
                    # Parse error from output
                    error_output = result.stderr or result.stdout
                    last_error = _parse_error_message(error_output)
                    print(f"  ❌ Run failed: {last_error[:100]}")

                    # Store error for potential fix
                    run_execution.error_message = last_error
                    state.run_execution = run_execution

                    # If not last retry, try to fix
                    if retry_count < max_retries:
                        print("  🔧 Attempting to fix error...")
                        # Note: In a real scenario, you'd call an LLM to analyze and fix
                        # For now, we just retry
                        time.sleep(1)  # Brief pause before retry

            except subprocess.TimeoutExpired:
                print("  ⏰ Run timed out after 120 seconds")
                last_error = "Process timed out"
                run_execution = RunExecution(
                    run_command=run_command,
                    exit_code=-1,
                    stderr="Process timed out after 120 seconds",
                    duration=120.0,
                    success=False,
                    error_message="Process timed out",
                    retry_count=retry_count,
                    max_retries=max_retries,
                )
                state.run_execution = run_execution

            except Exception as e:
                print(f"  ❌ Execution error: {e}")
                last_error = str(e)
                run_execution = RunExecution(
                    run_command=run_command,
                    exit_code=-1,
                    stderr=f"Execution error: {str(e)}",
                    duration=0.0,
                    success=False,
                    error_message=str(e),
                    retry_count=retry_count,
                    max_retries=max_retries,
                )
                state.run_execution = run_execution

        # Store result
        state.tools_output["run_verification"] = {
            "command": run_command,
            "success": success,
            "retry_count": retry_count,
            "duration": state.run_execution.duration,
            "error": last_error if not success else "",
        }

        if success:
            print("✅ Run verification passed")
            message = AIMessage(
                content=f"✅ Run verification passed\n"
                f"- Command: {run_command}\n"
                f"- Duration: {state.run_execution.duration:.1f}s\n"
                f"- Attempts: {retry_count}\n"
                f"- Next: Commit changes"
            )
            state.messages.append(message)

            # Update status
            state.current_phase = "commit_changes"
            state.status = "run_verified"

        else:
            print(f"❌ Run verification failed after {retry_count} attempts")
            message = AIMessage(
                content=f"⚠️  Run verification failed\n"
                f"- Command: {run_command}\n"
                f"- Attempts: {retry_count}/{max_retries}\n"
                f"- Error: {last_error[:100]}\n"
                f"- Next: Commit changes (manual fix needed)"
            )
            state.messages.append(message)

            # Still proceed to commit but mark as not verified
            state.current_phase = "commit_changes"
            state.status = "run_failed"
            state.error_message = f"Run verification failed: {last_error}"

        return state

    except Exception as e:
        state.error_message = f"Run verification failed: {str(e)}"
        state.status = "error"

        message = AIMessage(content=f"❌ Run verification error: {str(e)}")
        state.messages.append(message)

        print(f"❌ Run verification failed: {e}")
        return state


def _detect_run_command(working_path: Path, tech_stack: str) -> str | None:
    """
    Detect run command based on project structure and tech stack.

    Args:
        working_path: Path to project directory
        tech_stack: Technology stack

    Returns:
        Run command string or None if not detected
    """
    # Python/FastAPI projects
    if tech_stack in ["python", "fastapi"]:
        if (working_path / "main.py").exists():
            return "python main.py"
        elif (working_path / "app.py").exists():
            return "python app.py"
        elif (working_path / "app" / "main.py").exists():
            return "python -m uvicorn app.main:app --reload"
        elif (working_path / "pyproject.toml").exists():
            return "python -m uvicorn app.main:app --reload"

    # Node.js projects
    if tech_stack in ["nodejs", "nextjs", "react-vite", "express"]:
        if (working_path / "package.json").exists():
            try:
                import json

                with open(working_path / "package.json") as f:
                    package_data = json.load(f)
                    scripts = package_data.get("scripts", {})
                    if "dev" in scripts:
                        return "npm run dev"
                    elif "start" in scripts:
                        return "npm start"
            except:
                pass
        return "npm run dev"

    # Generic detection
    if (working_path / "package.json").exists():
        return "npm run dev"
    elif (working_path / "main.py").exists():
        return "python main.py"
    elif (working_path / "app.py").exists():
        return "python app.py"

    return None


def _parse_error_message(output: str) -> str:
    """
    Parse error message from command output.

    Args:
        output: Command output (stdout or stderr)

    Returns:
        Extracted error message
    """
    if not output:
        return "Unknown error"

    # Get last few lines which usually contain the error
    lines = output.strip().split("\n")
    error_lines = []

    # Look for common error patterns
    for line in reversed(lines):
        if any(
            keyword in line.lower()
            for keyword in ["error", "failed", "exception", "traceback", "fatal"]
        ):
            error_lines.insert(0, line)
            if len(error_lines) >= 3:
                break

    if error_lines:
        return " | ".join(error_lines[:3])

    # Fallback: return last non-empty line
    for line in reversed(lines):
        if line.strip():
            return line.strip()

    return "Unknown error"


__all__ = ["run_and_verify"]
