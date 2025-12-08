"""Run Tests node - Execute tests and capture results."""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from uuid import UUID

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.core_nodes import send_message

logger = logging.getLogger(__name__)


def _get_workspace_path(state: dict) -> Path | None:
    """Get workspace path from state (worktree) or fallback to project path from DB."""
    # Prefer workspace_path (worktree) where files are actually written
    workspace_path = state.get("workspace_path")
    if workspace_path:
        return Path(workspace_path)
    
    # Fallback to project path from DB
    project_id = state.get("project_id")
    if not project_id:
        return None
        
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Project
    
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        if project and project.project_path:
            return Path(project.project_path)
    return None


def _detect_package_manager(project_path: Path) -> tuple[str, str]:
    """Detect package manager and run command. Default: pnpm."""
    if (project_path / "pnpm-lock.yaml").exists():
        return ("pnpm", "pnpm")
    if (project_path / "bun.lockb").exists() or (project_path / "bun.lock").exists():
        return ("bun", "bun run")
    if (project_path / "yarn.lock").exists():
        return ("yarn", "yarn")
    return ("pnpm", "pnpm")  # Default: pnpm


def _detect_test_commands(project_path: Path, test_files: list[str]) -> list[dict]:
    """Detect test commands based on test files.
    
    Always runs tests for specific files only (story's test files).
    Does NOT run entire test suite.
    Only integration tests supported (no e2e).
    
    Args:
        project_path: Path to workspace
        test_files: List of test file paths to run
    
    Returns list of {type, command, files} dicts.
    """
    commands = []
    
    # Filter valid integration test files only
    integration_files = []
    
    for file_path in test_files:
        if not file_path:
            continue
            
        # Check file exists
        if not (project_path / file_path).exists():
            logger.warning(f"[_detect_test_commands] File not found: {file_path}")
            continue
        
        # Only accept .test.ts files (integration tests)
        if file_path.endswith('.test.ts'):
            integration_files.append(file_path)
    
    pm, run_cmd = _detect_package_manager(project_path)
    
    # Integration tests command - always use specific files
    if integration_files:
        files_arg = " ".join(f'"{f}"' for f in integration_files)
        # Always run jest with specific files, not entire suite
        cmd = f"pnpm exec jest {files_arg} --passWithNoTests"
        
        commands.append({
            "type": "integration",
            "command": cmd,
            "files": integration_files,
        })
        logger.info(f"[_detect_test_commands] Integration: {cmd}")
    
    return commands


def _parse_test_output(stdout: str, stderr: str, test_type: str) -> dict:
    """Parse test output to extract results (Jest only - no e2e)."""
    combined = stdout + stderr
    result = {
        "passed": 0,
        "failed": 0,
        "failed_tests": [],
        "error_messages": [],
    }
    
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


def _run_typecheck(project_path: Path, test_files: list[str]) -> dict | None:
    """Run TypeScript type checking using Jest's compiler.
    
    Uses Jest with --passWithNoTests to leverage moduleNameMapper config
    which properly resolves @/* path aliases.
    
    Returns None if pass, or dict with error info if fail.
    """
    if not test_files:
        return None
    
    # Filter integration test files only (Jest handles these)
    integration_files = [
        f for f in test_files 
        if f and f.endswith('.test.ts') and (project_path / f).exists()
    ]
    
    if not integration_files:
        logger.info("[_run_typecheck] No integration test files to check")
        return None
    
    try:
        files_arg = " ".join(f'"{f}"' for f in integration_files)
        # Use Jest to compile - it has moduleNameMapper configured for @/* paths
        cmd = f"pnpm exec jest {files_arg} --passWithNoTests --no-coverage --testPathIgnorePatterns=[]"
        
        logger.info(f"[_run_typecheck] Running: {cmd}")
        
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        
        if result.returncode != 0:
            output = (result.stdout or "") + (result.stderr or "")
            
            # Check for TypeScript/compilation errors
            if "error TS" in output or "Cannot find module" in output or "SyntaxError" in output:
                error_lines = [
                    line for line in output.split("\n") 
                    if "error TS" in line or "Cannot find module" in line or "SyntaxError" in line
                ]
                logger.info(f"[_run_typecheck] Found {len(error_lines)} TypeScript errors")
                return {
                    "success": False,
                    "errors": error_lines[:20],
                    "raw_output": output[:3000],
                }
        
        return None  # Pass
        
    except subprocess.TimeoutExpired:
        logger.warning("[_run_typecheck] TypeCheck timeout")
        return None
    except Exception as e:
        logger.warning(f"[_run_typecheck] Error: {e}")
        return None


async def run_tests(state: TesterState, agent=None) -> dict:
    """Execute tests and capture results.
    
    This node:
    1. Runs TypeScript type checking first
    2. Detects test commands based on test_plan
    3. Executes integration tests
    4. Parses results
    
    Output:
    - run_status: "PASS" | "FAIL" | "ERROR"
    - run_result: Parsed test results
    - run_stdout: Raw stdout
    - run_stderr: Raw stderr
    """
    print("[NODE] run_tests")
    
    # Use workspace_path (worktree) where files are written, not project_path from DB
    project_path = _get_workspace_path(state)
    if not project_path:
        return {
            "run_status": "ERROR",
            "error": "Workspace path not configured",
            "message": "Lỗi: Không tìm thấy workspace path.",
        }
    
    logger.info(f"[run_tests] Using workspace: {project_path}")
    
    # Collect ALL test files from multiple sources:
    # 1. files_created - tracks all files created during this session
    # 2. files_modified - tracks all files modified during this session
    # 3. test_plan - current plan (may be incomplete after analyze_errors)
    # This ensures we don't lose track of test files after error fixing
    # Note: Only integration tests (.test.ts) supported - no e2e
    
    test_files_set = set()
    
    # From files_created/modified (primary source - always complete)
    for f in state.get("files_created", []) + state.get("files_modified", []):
        if f and f.endswith('.test.ts'):
            test_files_set.add(f)
    
    # From test_plan (backup source)
    for step in state.get("test_plan", []):
        file_path = step.get("file_path", "")
        if file_path and file_path.endswith('.test.ts'):
            test_files_set.add(file_path)
    
    all_test_files = list(test_files_set)
    
    if not all_test_files:
        logger.info("[run_tests] No test files to run")
        return {
            "run_status": "PASS",
            "run_result": {"message": "No tests to run"},
            "message": "Không có tests để chạy.",
        }
    
    logger.info(f"[run_tests] Found {len(all_test_files)} test files: {all_test_files}")
    
    # Step 1: Run TypeCheck first
    logger.info("[run_tests] Running TypeScript check...")
    typecheck_result = _run_typecheck(project_path, all_test_files)
    
    if typecheck_result:
        # TypeScript errors found
        error_summary = "\n".join(typecheck_result["errors"][:10])
        msg = f"❌ TypeScript errors found:\n```\n{error_summary}\n```"
        
        await send_message(state, agent, msg, "error")
        
        logger.info(f"[run_tests] TypeCheck FAILED: {len(typecheck_result['errors'])} errors")
        
        return {
            "run_status": "FAIL",
            "run_result": {
                "passed": 0,
                "failed": 0,
                "typecheck_errors": typecheck_result["errors"],
            },
            "run_stdout": "",
            "run_stderr": typecheck_result["raw_output"],
            "message": msg,
            "action": "ANALYZE",
        }
    
    logger.info("[run_tests] TypeCheck passed")
    
    # Step 2: Detect test commands using all collected test files
    test_commands = _detect_test_commands(project_path, all_test_files)
    
    if not test_commands:
        return {
            "run_status": "PASS",
            "run_result": {"message": "No test commands detected"},
            "message": "Không phát hiện test commands.",
        }
    
    # Notify via appropriate channel
    await send_message(state, agent, f"🧪 Đang chạy tests ({len(test_commands)} command)...", "progress")
    
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
    
    # Notify via appropriate channel
    message_type = "test_result" if run_status == "PASS" else "error"
    await send_message(state, agent, msg, message_type)
    
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
