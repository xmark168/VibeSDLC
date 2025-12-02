"""Run Tests node - Execute tests and capture results."""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from uuid import UUID

from app.agents.tester.src.state import TesterState

logger = logging.getLogger(__name__)


def _get_project_path(project_id: str) -> Path | None:
    """Get project path from database."""
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Project
    
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        if project and project.project_path:
            return Path(project.project_path)
    return None


def _detect_package_manager(project_path: Path) -> tuple[str, str]:
    """Detect package manager and run command."""
    if (project_path / "bun.lockb").exists() or (project_path / "bun.lock").exists():
        return ("bun", "bun run")
    if (project_path / "pnpm-lock.yaml").exists():
        return ("pnpm", "pnpm")
    if (project_path / "yarn.lock").exists():
        return ("yarn", "yarn")
    return ("npm", "npm run")


def _detect_test_commands(project_path: Path, test_plan: list[dict]) -> list[dict]:
    """Detect test commands based on test plan.
    
    Returns list of {type, command, files} dicts.
    """
    commands = []
    
    # Group by test type
    integration_files = []
    e2e_files = []
    
    for step in test_plan:
        test_type = step.get("type", "integration")
        file_path = step.get("file_path", "")
        
        if test_type == "e2e":
            e2e_files.append(file_path)
        else:
            integration_files.append(file_path)
    
    pm, run_cmd = _detect_package_manager(project_path)
    
    # Check package.json for scripts
    pkg_scripts = {}
    pkg_path = project_path / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            pkg_scripts = pkg.get("scripts", {})
        except Exception:
            pass
    
    # Integration tests command
    if integration_files:
        if "test:integration" in pkg_scripts:
            cmd = f"{run_cmd} test:integration"
        elif "test" in pkg_scripts:
            # Run with specific files
            files_arg = " ".join(integration_files)
            cmd = f"{run_cmd} test -- {files_arg}"
        else:
            files_arg = " ".join(integration_files)
            cmd = f"npx jest {files_arg}"
        
        commands.append({
            "type": "integration",
            "command": cmd,
            "files": integration_files,
        })
    
    # E2E tests command
    if e2e_files:
        if "test:e2e" in pkg_scripts:
            cmd = f"{run_cmd} test:e2e"
        elif "e2e" in pkg_scripts:
            cmd = f"{run_cmd} e2e"
        else:
            # Default Playwright command
            files_arg = " ".join(e2e_files)
            cmd = f"npx playwright test {files_arg}"
        
        commands.append({
            "type": "e2e",
            "command": cmd,
            "files": e2e_files,
        })
    
    return commands


def _parse_test_output(stdout: str, stderr: str, test_type: str) -> dict:
    """Parse test output to extract results."""
    combined = stdout + stderr
    result = {
        "passed": 0,
        "failed": 0,
        "failed_tests": [],
        "error_messages": [],
    }
    
    if test_type == "e2e":
        # Playwright output parsing
        # Pattern: "X passed, Y failed"
        match = re.search(r"(\d+)\s*passed", combined)
        if match:
            result["passed"] = int(match.group(1))
        
        match = re.search(r"(\d+)\s*failed", combined)
        if match:
            result["failed"] = int(match.group(1))
        
        # Failed test names
        # Pattern: "[chromium] › file.spec.ts:10 › test name"
        failed_matches = re.findall(r"✘\s*\[.*?\]\s*›\s*\S+\s*›\s*(.+)", combined)
        result["failed_tests"] = failed_matches[:10]
        
    else:
        # Jest output parsing
        # Pattern: "Tests: X failed, Y passed, Z total"
        match = re.search(r"Tests:\s*(?:(\d+)\s*failed,\s*)?(\d+)\s*passed", combined)
        if match:
            result["failed"] = int(match.group(1) or 0)
            result["passed"] = int(match.group(2) or 0)
        
        # Failed test names
        # Pattern: "✕ test name (123ms)"
        failed_matches = re.findall(r"[✕✖]\s+(.+?)\s*\(\d+\s*ms\)", combined)
        result["failed_tests"] = failed_matches[:10]
        
        # Error messages
        error_matches = re.findall(r"Error:\s*(.+?)(?:\n|$)", combined)
        result["error_messages"] = error_matches[:5]
    
    return result


async def run_tests(state: TesterState, agent=None) -> dict:
    """Execute tests and capture results.
    
    This node:
    1. Detects test commands based on test_plan
    2. Executes integration tests (if any)
    3. Executes e2e tests (if any)
    4. Parses results
    
    Output:
    - run_status: "PASS" | "FAIL" | "ERROR"
    - run_result: Parsed test results
    - run_stdout: Raw stdout
    - run_stderr: Raw stderr
    """
    print("[NODE] run_tests")
    
    project_id = state.get("project_id", "")
    test_plan = state.get("test_plan", [])
    
    if not test_plan:
        logger.info("[run_tests] No test plan, skipping")
        return {
            "run_status": "PASS",
            "run_result": {"message": "No tests to run"},
            "message": "Không có tests để chạy.",
        }
    
    project_path = _get_project_path(project_id)
    if not project_path:
        return {
            "run_status": "ERROR",
            "error": "Project path not configured",
            "message": "Lỗi: Không tìm thấy project path.",
        }
    
    # Detect test commands
    test_commands = _detect_test_commands(project_path, test_plan)
    
    if not test_commands:
        return {
            "run_status": "PASS",
            "run_result": {"message": "No test commands detected"},
            "message": "Không phát hiện test commands.",
        }
    
    # Notify user
    if agent:
        await agent.message_user("response", f"🧪 Đang chạy tests ({len(test_commands)} command)...")
    
    all_stdout = []
    all_stderr = []
    all_results = []
    overall_passed = 0
    overall_failed = 0
    
    for cmd_info in test_commands:
        test_type = cmd_info["type"]
        command = cmd_info["command"]
        files = cmd_info["files"]
        
        logger.info(f"[run_tests] Running {test_type}: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
                env={**os.environ, "CI": "true", "FORCE_COLOR": "0"},
                encoding="utf-8",
                errors="replace",
            )
            
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            
            all_stdout.append(f"=== {test_type.upper()} ===\n{stdout}")
            all_stderr.append(stderr)
            
            # Parse results
            parsed = _parse_test_output(stdout, stderr, test_type)
            parsed["type"] = test_type
            parsed["command"] = command
            parsed["success"] = result.returncode == 0
            
            all_results.append(parsed)
            overall_passed += parsed["passed"]
            overall_failed += parsed["failed"]
            
        except subprocess.TimeoutExpired:
            all_stderr.append(f"[{test_type}] Timeout (300s)")
            all_results.append({
                "type": test_type,
                "success": False,
                "error": "Timeout",
            })
        except Exception as e:
            all_stderr.append(f"[{test_type}] Error: {str(e)}")
            all_results.append({
                "type": test_type,
                "success": False,
                "error": str(e),
            })
    
    # Determine overall status
    has_failures = overall_failed > 0 or any(not r.get("success", True) for r in all_results)
    run_status = "FAIL" if has_failures else "PASS"
    
    # Build result message
    if run_status == "PASS":
        msg = f"✅ Tests passed! ({overall_passed} passed)"
    else:
        msg = f"❌ Tests failed! ({overall_passed} passed, {overall_failed} failed)"
        
        # Add failed test names
        for res in all_results:
            if res.get("failed_tests"):
                msg += f"\n\nFailed in {res['type']}:"
                for test_name in res["failed_tests"][:5]:
                    msg += f"\n  • {test_name}"
    
    if agent:
        await agent.message_user("response", msg)
    
    logger.info(f"[run_tests] Status: {run_status}, Passed: {overall_passed}, Failed: {overall_failed}")
    
    return {
        "run_status": run_status,
        "run_result": {
            "passed": overall_passed,
            "failed": overall_failed,
            "results": all_results,
        },
        "run_stdout": "\n".join(s for s in all_stdout if s),
        "run_stderr": "\n".join(s for s in all_stderr if s),
        "message": msg,
        "action": "ANALYZE" if run_status == "FAIL" else "RESPOND",
    }
