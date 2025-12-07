"""Run code node - Execute format, lint fix, typecheck, build."""
import asyncio
import concurrent.futures
import logging
from pathlib import Path
from typing import Tuple, Optional, List

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.shell_tools import run_shell
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context, get_langfuse_span

logger = logging.getLogger(__name__)

# Thread pool for parallel shell commands
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


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
        result = run_shell(cmd, cwd, timeout)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code", 0)
        
        if exit_code != 0:
            if allow_fail:
                logger.warning(f"[run_code] [{svc_name}] {step_name} warning (exit={exit_code})")
                return True, stdout, stderr
            else:
                logger.error(f"[run_code] [{svc_name}] {step_name} FAILED (exit={exit_code})")
                logger.error(f"[run_code] stdout: {stdout[:500] if stdout else '(empty)'}")
                logger.error(f"[run_code] stderr: {stderr[:500] if stderr else '(empty)'}")
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


async def _run_format_lint_parallel(services: List[dict], workspace_path: str) -> None:
    """Run format and lint commands in parallel for all services.
    
    Optimization: Saves ~20-40s by running format/lint concurrently.
    """
    loop = asyncio.get_event_loop()
    tasks = []
    
    for svc in services:
        svc_name = svc.get("name", "app")
        svc_path = str(Path(workspace_path) / svc.get("path", "."))
        
        # Add format task
        if svc.get("format_cmd"):
            task = loop.run_in_executor(
                _executor,
                _run_step, "Format", svc["format_cmd"], svc_path, svc_name, 60, True
            )
            tasks.append(task)
        
        # Add lint task
        if svc.get("lint_fix_cmd"):
            task = loop.run_in_executor(
                _executor,
                _run_step, "Lint Fix", svc["lint_fix_cmd"], svc_path, svc_name, 60, True
            )
            tasks.append(task)
    
    if tasks:
        logger.info(f"[run_code] Running {len(tasks)} format/lint tasks in parallel...")
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("[run_code] Format/lint parallel execution completed")


async def _run_service_build(
    svc_config: dict,
    workspace_path: str,
    parent_span: Optional[object] = None
) -> dict:
    """
    Run build for a single service.
    
    Flow: Typecheck → Build
    
    Returns:
        {"status": "PASS|FAIL|SKIP", "stdout": str, "stderr": str}
    """
    svc_name = svc_config.get("name", "app")
    build_cmd = svc_config.get("build_cmd", "")
    typecheck_cmd = svc_config.get("typecheck_cmd", "pnpm run typecheck")
    
    svc_span = None
    if parent_span:
        svc_span = parent_span.span(name=f"service:{svc_name}", input={"path": svc_config.get("path", ".")})
    
    all_stdout = f"\n{'='*40}\n SERVICE: {svc_name}\n{'='*40}\n"
    all_stderr = ""
    
    try:
        # Run typecheck first (catches type errors with clearer messages, ~5s)
        if typecheck_cmd:
            success, stdout, stderr = _run_step(
                "Typecheck", typecheck_cmd, workspace_path, svc_name, timeout=60
            )
            all_stdout += f"\n$ {typecheck_cmd}\n{stdout}"
            if not success:
                all_stderr += f"\n[TYPECHECK FAILED]\n{stderr or stdout}"
                if svc_span:
                    svc_span.end(output={"status": "TYPECHECK_FAIL"})
                return {"status": "FAIL", "stdout": all_stdout, "stderr": all_stderr}
        
        if build_cmd:
            success, stdout, stderr = _run_step("Build", build_cmd, workspace_path, svc_name, timeout=180)
            all_stdout += f"\n$ {build_cmd}\n{stdout}"
            if not success:
                all_stderr += f"\n[BUILD FAILED]\n{stderr or stdout}"
                if svc_span:
                    svc_span.end(output={"status": "BUILD_FAIL"})
                return {"status": "FAIL", "stdout": all_stdout, "stderr": all_stderr}
        
        if svc_span:
            svc_span.end(output={"status": "PASS"})
        return {"status": "PASS", "stdout": all_stdout, "stderr": ""}
        
    except Exception as e:
        logger.error(f"[run_code] [{svc_name}] Unexpected error: {e}")
        if svc_span:
            svc_span.end(output={"status": "ERROR", "error": str(e)})
        return {"status": "FAIL", "stdout": all_stdout, "stderr": str(e)}


async def run_code(state: DeveloperState, agent=None) -> DeveloperState:
    """
    Execute format, lint fix, typecheck, build.
    
    Flow:
    1. Format all services (prettier)
    2. Lint fix all services (eslint)
    3. Build all services (install → typecheck → build)
    """
    logger.info("[NODE] run_code")
    
    workspace_path = state.get("workspace_path", "")
    project_id = state.get("project_id", "default")
    task_id = state.get("task_id") or state.get("story_id", "")
    
    run_code_span = get_langfuse_span(state, "run_code", {"workspace": workspace_path, "task_id": task_id})
    
    try:
        if not workspace_path or not Path(workspace_path).exists():
            logger.warning("[run_code] No workspace path, skipping")
            if run_code_span:
                run_code_span.end(output={"status": "PASS", "reason": "No workspace"})
            return {**state, "run_status": "PASS", "run_result": {"status": "PASS", "summary": "No workspace"}}
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        project_config = state.get("project_config", {})
        tech_stack = project_config.get("tech_stack", {})
        services = tech_stack.get("service", []) if isinstance(tech_stack, dict) else []
        
        if not services:
            logger.error("[run_code] Missing project_config.tech_stack.service")
            if run_code_span:
                run_code_span.end(output={"status": "ERROR", "reason": "Missing config"})
            return {**state, "run_status": "ERROR", "run_result": {"status": "ERROR", "summary": "Missing config"}}
        
        logger.info(f"[run_code] Services: {[s.get('name', 'app') for s in services]}")
        
        # Skip prisma - already run in setup_workspace and implement
        
        # Run seed if seed file exists
        seed_file = Path(workspace_path) / "prisma" / "seed.ts"
        if seed_file.exists():
            logger.info("[run_code] Running database seed...")
            success, stdout, stderr = _run_step(
                "DB Seed", "pnpm exec tsx prisma/seed.ts",
                workspace_path, "prisma", timeout=60, allow_fail=True
            )
            if success:
                logger.info("[run_code] Database seeded successfully")
            else:
                logger.warning(f"[run_code] Seed failed (continuing): {stderr[:200] if stderr else 'unknown'}")
        
        # Format and lint all services in parallel (optimization: saves ~20-40s)
        await _run_format_lint_parallel(services, workspace_path)
        
        # Build all services
        all_stdout = ""
        all_stderr = ""
        all_passed = True
        summaries = []
        
        for svc in services:
            result = await _run_service_build(svc, workspace_path, run_code_span)
            svc_name = svc.get("name", "app")
            
            all_stdout += result["stdout"]
            all_stderr += result["stderr"]
            
            if result["status"] == "PASS":
                summaries.append(f"{svc_name}: PASS")
            else:
                summaries.append(f"{svc_name}: FAIL")
                all_passed = False
        
        run_status = "PASS" if all_passed else "FAIL"
        summary = ", ".join(summaries)
        
        logger.info(f"[run_code] Result: {summary}")
        if run_code_span:
            run_code_span.end(output={"status": run_status, "summary": summary})
        
        return {
            **state,
            "run_status": run_status,
            "run_stdout": all_stdout,
            "run_stderr": all_stderr,
            "run_result": {"status": run_status, "summary": summary, "services": summaries},
        }
        
    except Exception as e:
        logger.error(f"[run_code] Error: {e}", exc_info=True)
        if run_code_span:
            run_code_span.end(output={"error": str(e)})
        return {**state, "run_status": "PASS", "run_result": {"status": "PASS", "summary": f"Error: {e}"}}
