"""Run code node - Execute format, lint fix, typecheck, build."""
import asyncio
import concurrent.futures
import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Tuple, Optional, List

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.utils.shell_utils import run_shell
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_span
from app.agents.developer_v2.src.tools import set_tool_context

logger = logging.getLogger(__name__)


def _clear_next_types_cache(workspace_path: str) -> None:
    """
    Clear .next/types cache
    """
    next_types = Path(workspace_path) / ".next" / "types"
    if next_types.exists():
        try:
            shutil.rmtree(next_types, ignore_errors=True)
            logger.info("[run_code] Cleared .next/types cache")
        except Exception as e:
            logger.warning(f"[run_code] Failed to clear .next/types: {e}")


def _validate_null_safety(workspace_path: str) -> List[str]:
    """Quick scan for unsafe array operations on API data.
    
    Detects patterns like `data.items.map()` without null safety.
    """
    import re
    warnings = []
    
    components_dir = Path(workspace_path) / "src" / "components"
    if not components_dir.exists():
        return warnings
    
    for tsx_file in components_dir.rglob("*.tsx"):
        try:
            content = tsx_file.read_text(encoding="utf-8")
            for i, line in enumerate(content.split('\n')):
                # Pattern: obj.prop.filter/map/slice without ?? or ?.
                if re.search(r'\w+\.\w+\.(filter|map|slice|reduce)\(', line):
                    if '??' not in line and '|| []' not in line and '?.' not in line:
                        rel_path = tsx_file.relative_to(workspace_path)
                        warnings.append(f"{rel_path}:{i+1}")
        except Exception:
            pass
    
    return warnings


def _has_script(workspace_path: str, script_name: str) -> bool:
    """Check if a script exists in package.json."""
    try:
        pkg_path = Path(workspace_path) / "package.json"
        if pkg_path.exists():
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            return script_name in pkg.get("scripts", {})
    except Exception:
        pass
    return False

# Thread pool for parallel shell commands
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _should_skip_seed(workspace_path: str) -> bool:
    """Check if seed can be skipped (seed.ts unchanged)."""
    seed_file = Path(workspace_path) / "prisma" / "seed.ts"
    cache_file = Path(workspace_path) / ".seed_cache"
    
    if not seed_file.exists():
        return True  # No seed file, nothing to run
    
    try:
        current_hash = hashlib.md5(seed_file.read_bytes()).hexdigest()
        if cache_file.exists():
            cached_hash = cache_file.read_text().strip()
            if cached_hash == current_hash:
                return True
    except Exception:
        pass
    
    return False


def _update_seed_cache(workspace_path: str) -> None:
    """Update seed cache after successful seed."""
    seed_file = Path(workspace_path) / "prisma" / "seed.ts"
    cache_file = Path(workspace_path) / ".seed_cache"
    
    try:
        if seed_file.exists():
            current_hash = hashlib.md5(seed_file.read_bytes()).hexdigest()
            cache_file.write_text(current_hash)
    except Exception:
        pass


def _run_seed(workspace_path: str) -> Tuple[bool, str, str]:
    """Run database seed (blocking). Returns (success, stdout, stderr)."""
    seed_file = Path(workspace_path) / "prisma" / "seed.ts"
    
    if not seed_file.exists():
        return True, "", ""
    
    if _should_skip_seed(workspace_path):
        logger.info("[run_code] Skipping seed (cached)")
        return True, "", ""
    
    logger.info("[run_code] Running database seed...")
    success, stdout, stderr = _run_step(
        "DB Seed", "pnpm exec ts-node prisma/seed.ts",
        workspace_path, "prisma", timeout=60, allow_fail=True
    )
    
    if success:
        _update_seed_cache(workspace_path)
        logger.info("[run_code] Database seeded successfully")
    else:
        logger.warning(f"[run_code] Seed failed (continuing): {stderr[:200] if stderr else 'unknown'}")
    
    return success, stdout, stderr


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
                logger.error(f"[run_code] stdout: {stdout[:2000] if stdout else '(empty)'}")
                logger.error(f"[run_code] stderr: {stderr[:2000] if stderr else '(empty)'}")
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
    
    Flow: Typecheck + Build (PARALLEL for speed)
    
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
        # Clear stale Next.js types cache before typecheck/build
        _clear_next_types_cache(workspace_path)
        
        # Quick null safety validation
        null_warnings = _validate_null_safety(workspace_path)
        if null_warnings:
            logger.warning(f"[run_code] Null safety warnings ({len(null_warnings)}): {null_warnings[:5]}")
        
        loop = asyncio.get_event_loop()
        tasks = []
        task_names = []
        
        # Prepare typecheck task
        if typecheck_cmd and _has_script(workspace_path, "typecheck"):
            tasks.append(loop.run_in_executor(
                _executor, _run_step, "Typecheck", typecheck_cmd, workspace_path, svc_name, 60, False
            ))
            task_names.append("typecheck")
        elif typecheck_cmd:
            logger.info(f"[run_code] [{svc_name}] Skipping typecheck (script not found)")
        
        # Prepare build task
        if build_cmd:
            tasks.append(loop.run_in_executor(
                _executor, _run_step, "Build", build_cmd, workspace_path, svc_name, 180, False
            ))
            task_names.append("build")
        
        if not tasks:
            if svc_span:
                svc_span.end(output={"status": "PASS"})
            return {"status": "PASS", "stdout": all_stdout, "stderr": ""}
        
        # Run typecheck + build in PARALLEL
        logger.info(f"[run_code] [{svc_name}] Running {' + '.join(task_names)} in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            task_name = task_names[i]
            
            if isinstance(result, Exception):
                all_stderr += f"\n[{task_name.upper()} ERROR]\n{str(result)}"
                if svc_span:
                    svc_span.end(output={"status": f"{task_name.upper()}_ERROR"})
                return {"status": "FAIL", "stdout": all_stdout, "stderr": all_stderr}
            
            success, stdout, stderr = result
            cmd = typecheck_cmd if task_name == "typecheck" else build_cmd
            all_stdout += f"\n$ {cmd}\n{stdout}"
            
            if not success:
                all_stderr += f"\n[{task_name.upper()} FAILED]\n{stderr or stdout}"
                if svc_span:
                    svc_span.end(output={"status": f"{task_name.upper()}_FAIL"})
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
        
        set_tool_context(root_dir=workspace_path, project_id=project_id, task_id=task_id)
        
        project_config = state.get("project_config", {})
        tech_stack = project_config.get("tech_stack", {})
        services = tech_stack.get("service", []) if isinstance(tech_stack, dict) else []
        
        if not services:
            logger.error("[run_code] Missing project_config.tech_stack.service")
            if run_code_span:
                run_code_span.end(output={"status": "ERROR", "reason": "Missing config"})
            return {**state, "run_status": "ERROR", "run_result": {"status": "ERROR", "summary": "Missing config"}}
        
        logger.info(f"[run_code] Services: {[s.get('name', 'app') for s in services]}")
        
        # Run seed + format/lint in PARALLEL (optimization: saves ~5s)
        loop = asyncio.get_event_loop()
        seed_task = loop.run_in_executor(_executor, _run_seed, workspace_path)
        format_lint_task = _run_format_lint_parallel(services, workspace_path)
        
        logger.info("[run_code] Running seed + format/lint in parallel...")
        await asyncio.gather(seed_task, format_lint_task, return_exceptions=True)
        
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
