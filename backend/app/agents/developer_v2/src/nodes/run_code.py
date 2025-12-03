"""Run code node - Execute format, lint fix, build + tests."""
import json
import logging
from pathlib import Path
from typing import Tuple, Optional

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.shell_tools import execute_shell
from app.agents.developer_v2.src.tools.container_tools import (
    dev_container_manager, set_container_context,
)
from app.agents.developer_v2.src.nodes._helpers import (
    setup_tool_context, get_langfuse_span, write_test_log
)

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _run_shell(cmd: str, cwd: str, timeout: int = 120) -> dict:
    """Execute shell command and parse JSON result."""
    result = execute_shell.invoke({
        "command": cmd,
        "working_directory": cwd,
        "timeout": timeout
    })
    if isinstance(result, str):
        result = json.loads(result)
    return result


def _run_step(
    step_name: str,
    cmd: str,
    cwd: str,
    svc_name: str,
    timeout: int = 120,
    allow_fail: bool = False
) -> Tuple[bool, str, str]:
    """
    Run a build/test step with consistent logging.
    
    Returns:
        (success, stdout, stderr)
    """
    logger.info(f"[run_code] [{svc_name}] {step_name}: {cmd}")
    
    try:
        result = _run_shell(cmd, cwd, timeout)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code", 0)
        
        if exit_code != 0:
            if allow_fail:
                logger.warning(f"[run_code] [{svc_name}] {step_name} warning (exit={exit_code})")
                return True, stdout, stderr
            else:
                logger.error(f"[run_code] [{svc_name}] {step_name} FAILED (exit={exit_code})")
                return False, stdout, stderr
        
        logger.info(f"[run_code] [{svc_name}] {step_name} completed")
        return True, stdout, stderr
        
    except Exception as e:
        error_msg = str(e)
        if allow_fail:
            logger.warning(f"[run_code] [{svc_name}] {step_name} error (continuing): {error_msg}")
            return True, "", error_msg
        else:
            logger.error(f"[run_code] [{svc_name}] {step_name} error: {error_msg}")
            return False, "", error_msg


# =============================================================================
# SERVICE TEST RUNNER
# =============================================================================

async def _run_service_tests(
    svc_config: dict,
    workspace_path: str,
    branch_name: str,
    parent_span: Optional[object] = None
) -> dict:
    """
    Run tests for a single service.
    
    Flow: Install → DB Setup → Build → Test
    
    Returns:
        {"status": "PASS|FAIL|SKIP", "stdout": str, "stderr": str}
    """
    svc_name = svc_config.get("name", "app")
    svc_path = str(Path(workspace_path) / svc_config.get("path", "."))
    
    # Commands from config
    install_cmd = svc_config.get("install_cmd", "")
    build_cmd = svc_config.get("build_cmd", "")
    test_cmd = svc_config.get("test_cmd", "")
    needs_db = svc_config.get("needs_db", False)
    db_cmds = svc_config.get("db_cmds", [])
    
    # Skip if no test command
    if not test_cmd:
        logger.info(f"[run_code] [{svc_name}] Skipping - no test_cmd configured")
        return {"status": "SKIP", "stdout": "", "stderr": ""}
    
    # Create span for tracing
    svc_span = None
    if parent_span:
        svc_span = parent_span.span(name=f"service:{svc_name}", input={
            "path": svc_config.get("path", "."),
            "needs_db": needs_db,
        })
    
    all_stdout = f"\n{'='*40}\n SERVICE: {svc_name}\n{'='*40}\n"
    all_stderr = ""
    
    try:
        # Step 1: Install dependencies
        if install_cmd:
            success, stdout, stderr = _run_step(
                "Install", install_cmd, workspace_path, svc_name,
                timeout=300, allow_fail=False
            )
            all_stdout += f"\n$ {install_cmd}\n{stdout}"
            if not success:
                all_stderr += stderr
                if svc_span:
                    svc_span.end(output={"status": "INSTALL_FAIL"})
                return {"status": "FAIL", "stdout": all_stdout, "stderr": all_stderr}
        
        # Step 2: Typecheck (catch type errors early)
        typecheck_cmd = svc_config.get("typecheck_cmd", "bun run typecheck")
        if typecheck_cmd:
            success, stdout, stderr = _run_step(
                "Typecheck", typecheck_cmd, workspace_path, svc_name,
                timeout=120, allow_fail=False
            )
            all_stdout += f"\n$ {typecheck_cmd}\n{stdout}"
            if not success:
                all_stderr += f"\n[TYPECHECK FAILED]\n{stderr or stdout}"
                task_id = svc_config.get("task_id", "unknown")
                write_test_log(task_id, f"TYPECHECK ERROR:\n{stderr or stdout}", "FAIL")
                if svc_span:
                    svc_span.end(output={"status": "TYPECHECK_FAIL"})
                return {"status": "FAIL", "stdout": all_stdout, "stderr": all_stderr}
        
        # Step 3: Database setup (if needed)
        if needs_db:
            try:
                set_container_context(branch_name=branch_name, workspace_path=workspace_path)
                dev_container_manager.get_or_create(
                    branch_name=branch_name,
                    workspace_path=workspace_path,
                    project_type="node",
                )
                logger.info(f"[run_code] [{svc_name}] DB container ready")
            except Exception as e:
                logger.warning(f"[run_code] [{svc_name}] DB container error (continuing): {e}")
            
            # Run DB commands
            for db_cmd in db_cmds:
                success, stdout, stderr = _run_step(
                    "DB Setup", db_cmd, workspace_path, svc_name,
                    timeout=60, allow_fail=True
                )
                all_stdout += f"\n$ {db_cmd}\n{stdout}"
        
        # Step 4: Build
        if build_cmd:
            success, stdout, stderr = _run_step(
                "Build", build_cmd, workspace_path, svc_name,
                timeout=180, allow_fail=False
            )
            all_stdout += f"\n$ {build_cmd}\n{stdout}"
            if not success:
                all_stderr += f"\n[BUILD FAILED]\n{stderr or stdout}"
                task_id = svc_config.get("task_id", "unknown")
                write_test_log(task_id, f"BUILD ERROR:\n{stderr or stdout}", "FAIL")
                if svc_span:
                    svc_span.end(output={"status": "BUILD_FAIL"})
                return {"status": "FAIL", "stdout": all_stdout, "stderr": all_stderr}
        
        # Step 5: Run tests
        success, stdout, stderr = _run_step(
            "Test", test_cmd, workspace_path, svc_name,
            timeout=300, allow_fail=False
        )
        all_stdout += f"\n$ {test_cmd}\n{stdout}"
        
        if not success:
            test_output = stdout + stderr
            all_stderr += test_output
            task_id = svc_config.get("task_id", "unknown")
            write_test_log(task_id, test_output, "FAIL")
            if svc_span:
                svc_span.end(output={"status": "TEST_FAIL"})
            return {"status": "FAIL", "stdout": all_stdout, "stderr": all_stderr}
        
        # All steps passed
        if svc_span:
            svc_span.end(output={"status": "PASS"})
        
        return {"status": "PASS", "stdout": all_stdout, "stderr": ""}
        
    except Exception as e:
        logger.error(f"[run_code] [{svc_name}] Unexpected error: {e}")
        if svc_span:
            svc_span.end(output={"status": "ERROR", "error": str(e)})
        return {"status": "FAIL", "stdout": all_stdout, "stderr": str(e)}


# =============================================================================
# MAIN NODE
# =============================================================================

async def run_code(state: DeveloperState, agent=None) -> DeveloperState:
    """
    Execute format, lint fix + tests.
    
    Flow:
    1. Format all services (prettier)
    2. Lint fix all services (eslint)
    3. Run tests for all services (install → build → test)
    """
    print("[NODE] run_code")
    
    workspace_path = state.get("workspace_path", "")
    project_id = state.get("project_id", "default")
    task_id = state.get("task_id") or state.get("story_id", "")
    branch_name = state.get("branch_name") or task_id
    
    # Create tracing span
    run_code_span = get_langfuse_span(state, "run_code", {
        "workspace": workspace_path,
        "task_id": task_id,
    })
    
    try:
        # Check workspace exists
        if not workspace_path or not Path(workspace_path).exists():
            logger.warning("[run_code] No workspace path, skipping tests")
            if run_code_span:
                run_code_span.end(output={"status": "PASS", "reason": "No workspace"})
            return {
                **state,
                "run_status": "PASS",
                "run_result": {"status": "PASS", "summary": "No workspace to test"},
            }
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Get service configs
        project_config = state.get("project_config", {})
        tech_stack = project_config.get("tech_stack", {})
        services = tech_stack.get("service", []) if isinstance(tech_stack, dict) else []
        
        if not services:
            logger.error("[run_code] Missing project_config.tech_stack.service")
            if run_code_span:
                run_code_span.end(output={"status": "ERROR", "reason": "Missing config"})
            return {
                **state,
                "run_status": "ERROR",
                "run_result": {"status": "ERROR", "summary": "Missing project_config.tech_stack.service"},
            }
        
        svc_names = [s.get("name", "app") for s in services]
        logger.info(f"[run_code] Services: {svc_names}")
        
        # =================================================================
        # Phase 1: Format all services (prettier)
        # =================================================================
        for svc in services:
            svc_name = svc.get("name", "app")
            svc_path = str(Path(workspace_path) / svc.get("path", "."))
            format_cmd = svc.get("format_cmd")
            
            if format_cmd:
                _run_step("Format", format_cmd, svc_path, svc_name, timeout=60, allow_fail=True)
        
        # =================================================================
        # Phase 2: Lint fix all services (eslint)
        # =================================================================
        for svc in services:
            svc_name = svc.get("name", "app")
            svc_path = str(Path(workspace_path) / svc.get("path", "."))
            lint_fix_cmd = svc.get("lint_fix_cmd")
            
            if lint_fix_cmd:
                _run_step("Lint Fix", lint_fix_cmd, svc_path, svc_name, timeout=60, allow_fail=True)
        
        # =================================================================
        # Phase 3: Run tests for all services
        # =================================================================
        all_stdout = ""
        all_stderr = ""
        all_passed = True
        summaries = []
        
        for svc in services:
            # Add task_id for logging
            svc["task_id"] = task_id
            
            result = await _run_service_tests(svc, workspace_path, branch_name, run_code_span)
            
            svc_name = svc.get("name", "app")
            status = result["status"]
            
            all_stdout += result["stdout"]
            all_stderr += result["stderr"]
            
            if status == "SKIP":
                summaries.append(f"{svc_name}: SKIP")
            elif status == "PASS":
                summaries.append(f"{svc_name}: PASS")
            else:
                summaries.append(f"{svc_name}: FAIL")
                all_passed = False
        
        # =================================================================
        # Final result
        # =================================================================
        run_status = "PASS" if all_passed else "FAIL"
        summary = ", ".join(summaries)
        
        if run_status == "PASS":
            logger.info(f"[run_code] All tests passed ({summary})")
        else:
            logger.error(f"[run_code] Some tests failed ({summary})")
        
        if run_code_span:
            run_code_span.end(output={"status": run_status, "summary": summary})
        
        return {
            **state,
            "run_status": run_status,
            "run_stdout": all_stdout,
            "run_stderr": all_stderr,
            "run_result": {
                "status": run_status,
                "summary": summary,
                "services": summaries,
            },
        }
        
    except Exception as e:
        logger.error(f"[run_code] Error: {e}", exc_info=True)
        if run_code_span:
            run_code_span.end(output={"error": str(e)})
        return {
            **state,
            "run_status": "PASS",
            "run_result": {"status": "PASS", "summary": f"Test execution error: {str(e)}"},
        }
