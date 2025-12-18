"""Run code node - Execute format, lint fix, typecheck, build."""
import asyncio
import concurrent.futures
import hashlib
import json
import logging
import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Tuple, Optional, List
from app.agents.developer.src.state import DeveloperState
from app.agents.developer.src.utils.shell_utils import run_shell
from app.agents.developer.src.utils.llm_utils import get_langfuse_span, track_node


from langgraph.types import interrupt
from app.agents.developer.src.utils.signal_utils import check_interrupt_signal
from app.agents.developer.src.utils.story_logger import log_to_story, StoryLogger
logger = logging.getLogger(__name__)


def _clear_next_types_cache(workspace_path: str) -> None:
    """
    Clear .next/types cache
    """
    next_types = Path(workspace_path) / ".next" / "types"
    if next_types.exists():
        try:
            shutil.rmtree(next_types, ignore_errors=True)
            logger.debug("[run_code] Cleared .next/types cache")
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
# Increased from 4 to 10 to support more concurrent stories
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix="runcode_worker")


def _should_skip_seed(workspace_path: str) -> bool:
    """Check if seed can be skipped (seed.ts AND schema.prisma unchanged)."""
    seed_file = Path(workspace_path) / "prisma" / "seed.ts"
    schema_file = Path(workspace_path) / "prisma" / "schema.prisma"
    cache_file = Path(workspace_path) / ".seed_cache"
    
    if not seed_file.exists():
        return True  # No seed file, nothing to run
    
    try:
        # Calculate combined hash of seed.ts and schema.prisma
        seed_hash = hashlib.md5(seed_file.read_bytes()).hexdigest()
        
        # Include schema hash if schema exists
        if schema_file.exists():
            schema_hash = hashlib.md5(schema_file.read_bytes()).hexdigest()
            current_hash = f"{seed_hash}:{schema_hash}"
        else:
            current_hash = seed_hash
        
        # Check cache
        if cache_file.exists():
            cached_hash = cache_file.read_text().strip()
            if cached_hash == current_hash:
                return True  # Both unchanged
    except Exception:
        pass
    
    return False  # Re-run seed (changed or no cache)


def _update_seed_cache(workspace_path: str) -> None:
    """Update seed cache after successful seed (combined seed.ts + schema.prisma hash)."""
    seed_file = Path(workspace_path) / "prisma" / "seed.ts"
    schema_file = Path(workspace_path) / "prisma" / "schema.prisma"
    cache_file = Path(workspace_path) / ".seed_cache"
    
    try:
        if seed_file.exists():
            # Calculate combined hash
            seed_hash = hashlib.md5(seed_file.read_bytes()).hexdigest()
            
            # Include schema hash if schema exists
            if schema_file.exists():
                schema_hash = hashlib.md5(schema_file.read_bytes()).hexdigest()
                current_hash = f"{seed_hash}:{schema_hash}"
            else:
                current_hash = seed_hash
            
            cache_file.write_text(current_hash)
    except Exception:
        pass


def _run_prisma_db_push(workspace_path: str) -> bool:
    """Run prisma db push (blocking). Returns True if successful."""
    schema_path = os.path.join(workspace_path, "prisma", "schema.prisma")
    if not os.path.exists(schema_path):
        return True  # No schema, nothing to push
    
    try:
        result = subprocess.run(
            "pnpm exec prisma db push --skip-generate --accept-data-loss",
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120,
            shell=True,
        )
        if result.returncode == 0:
            logger.debug("[run_code] prisma db push successful")
            return True
        else:
            logger.warning(f"[run_code] prisma db push failed: {result.stderr[:200] if result.stderr else 'unknown'}")
            return False
    except subprocess.TimeoutExpired:
        logger.warning("[run_code] prisma db push timed out")
        return False
    except Exception as e:
        logger.warning(f"[run_code] prisma db push error: {e}")
        return False


def _run_seed(workspace_path: str) -> Tuple[bool, str, str]:
    """Run database seed (blocking). Returns (success, stdout, stderr)."""
    seed_file = Path(workspace_path) / "prisma" / "seed.ts"
    
    if not seed_file.exists():
        return True, "", ""
    
    if _should_skip_seed(workspace_path):
        logger.debug("[run_code] Skipping seed (cached)")
        return True, "", ""
    
    logger.debug("[run_code] Running database seed...")
    # Use prisma db seed command - handles compiler-options automatically
    success, stdout, stderr = _run_step(
        "DB Seed", "pnpm prisma db seed",
        workspace_path, ".", timeout=60, allow_fail=False  # Seed errors should be fixed
    )
    
    if success:
        _update_seed_cache(workspace_path)
        logger.debug("[run_code] Database seeded successfully")
    else:
        logger.error(f"[run_code] Seed FAILED: {stderr[:500] if stderr else stdout[:500] if stdout else 'unknown'}")
    
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
    logger.debug(f"[run_code] [{svc_name}] {step_name}: {cmd}")
    
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
        
        logger.debug(f"[run_code] [{svc_name}] {step_name} completed")
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
    """
    Run format and lint commands in parallel for all services.
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
        logger.debug(f"[run_code] Running {len(tasks)} format/lint tasks in parallel...")
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug("[run_code] Format/lint parallel execution completed")


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
            logger.debug(f"[run_code] [{svc_name}] Skipping typecheck (script not found)")
        
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
        logger.debug(f"[run_code] [{svc_name}] Running {' + '.join(task_names)} in parallel...")
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


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

@track_node("run_code")
async def run_code(state: DeveloperState, agent=None) -> DeveloperState:

    
    # Get IDs for logging
    story_id = state.get("story_id", "")
    project_id = state.get("project_id", "")
    node_name = "run_code"
    
    # Helper for logging
    async def log(message: str, level: str = "info"):
        if story_id and project_id:
            await log_to_story(story_id, project_id, message, level, node_name)
    
    # Create story logger for milestone messages
    story_logger = StoryLogger.from_state(state, agent).with_node(node_name)
    
    # Check for pause/cancel signal
    if story_id:
        signal = check_interrupt_signal(story_id, agent)
        if signal:
            await log(f"Interrupt signal received: {signal}", "warning")
            interrupt({"reason": signal, "story_id": story_id, "node": node_name})
    
    # Check if there were implementation errors that weren't handled
    parallel_errors = state.get("parallel_errors")
    if parallel_errors and len(parallel_errors) > 0:
        error_summary = f"{len(parallel_errors)} implementation errors"
        await log(f"❌ Skipping build - implementation had errors: {error_summary}", "error")
        await story_logger.message(f"❌ Implementation failed with {len(parallel_errors)} errors")
        return {
            **state,
            "run_status": "FAIL",
            "run_result": {"status": "FAIL", "summary": error_summary, "implementation_errors": parallel_errors},
            "action": "ANALYZE_ERROR"
        }
    
    await log("🧪 Starting build validation...")
    
    workspace_path = state.get("workspace_path", "")
    task_id = state.get("task_id") or story_id
    
    run_code_span = get_langfuse_span(state, "run_code", {"workspace": workspace_path, "task_id": task_id})
    
    try:
        if not workspace_path or not Path(workspace_path).exists():
            await log("No workspace path found, skipping build validation", "warning")
            if run_code_span:
                run_code_span.end(output={"status": "PASS", "reason": "No workspace"})
            return {**state, "run_status": "PASS", "run_result": {"status": "PASS", "summary": "No workspace"}}
        
        await log(f"Workspace: {workspace_path}", "debug")
        
        project_config = state.get("project_config", {})
        tech_stack = project_config.get("tech_stack", {})
        services = tech_stack.get("service", []) if isinstance(tech_stack, dict) else []
        
        if not services:
            await log("Missing project_config.tech_stack.service configuration", "error")
            if run_code_span:
                run_code_span.end(output={"status": "ERROR", "reason": "Missing config"})
            return {**state, "run_status": "ERROR", "run_result": {"status": "ERROR", "summary": "Missing config"}}
        
        service_names = [s.get('name', 'app') for s in services]
        await log(f"Found {len(services)} service(s): {', '.join(service_names)}")
        
        # =====================================================================
        # Step 0: Prisma DB Push (generate already done in setup_workspace)
        # =====================================================================
        schema_file = Path(workspace_path) / "prisma" / "schema.prisma"
        if schema_file.exists():
            await log("🗄️ Syncing database schema...")
            
            loop = asyncio.get_event_loop()
            
            # Only db push - generate already done in setup_workspace
            push_success = await loop.run_in_executor(_executor, _run_prisma_db_push, workspace_path)
            
            if not push_success:
                await log("❌ Prisma DB push failed", "error")
                await story_logger.message("❌ Prisma DB push failed - schema sync issue")
                if run_code_span:
                    run_code_span.end(output={"status": "FAIL", "step": "prisma_db_push"})
                return {
                    **state,
                    "run_status": "FAIL",
                    "run_result": {"status": "FAIL", "step": "prisma_db_push", "summary": "Prisma DB push failed"},
                    "action": "ANALYZE_ERROR"
                }
            
            await log("Database schema synced ✓", "success")
        else:
            await log("No schema.prisma found, skipping DB sync", "debug")
        
        # =====================================================================
        # Step 1: Database Seed (if prisma/seed.ts exists)
        # =====================================================================
        seed_file = Path(workspace_path) / "prisma" / "seed.ts"
        if seed_file.exists():
            await log("🌱 Running database seed...")
            if _should_skip_seed(workspace_path):
                await log("Seed skipped (no changes detected)", "debug")
            else:
                loop = asyncio.get_event_loop()
                seed_success, seed_stdout, seed_stderr = await loop.run_in_executor(_executor, _run_seed, workspace_path)
                if seed_success:
                    await log("Database seed completed", "success")
                else:
                    # Seed failed - return to ANALYZE_ERROR for fixing
                    error_output = seed_stderr or seed_stdout or "Unknown seed error"
                    await log(f"❌ Database seed FAILED: {error_output[:500]}", "error")
                    await story_logger.message(f"❌ Seed failed - analyzing error...")
                    if run_code_span:
                        run_code_span.end(output={"status": "FAIL", "step": "seed", "error": error_output[:500]})
                    return {
                        **state,
                        "run_status": "FAIL",
                        "run_result": {
                            "status": "FAIL",
                            "step": "seed",
                            "summary": "Database seed failed",
                            "error_output": error_output,
                            "file": "prisma/seed.ts"
                        },
                        "action": "ANALYZE_ERROR"
                    }
        else:
            await log("No prisma/seed.ts found, skipping seed", "debug")
        
        # =====================================================================
        # Step 2: Format + Lint (parallel for each service)
        # =====================================================================
        await log("📝 Running code formatting and linting...")
        
        for svc in services:
            svc_name = svc.get("name", "app")
            str(Path(workspace_path) / svc.get("path", "."))
            
            # Format
            if svc.get("format_cmd"):
                await log(f"[{svc_name}] Running format: {svc['format_cmd']}", "debug")
            
            # Lint
            if svc.get("lint_fix_cmd"):
                await log(f"[{svc_name}] Running lint fix: {svc['lint_fix_cmd']}", "debug")
        
        await _run_format_lint_parallel(services, workspace_path)
        await log("Format and lint completed", "success")
        
        # =====================================================================
        # Step 3: Clear Next.js cache (if applicable)
        # =====================================================================
        next_types = Path(workspace_path) / ".next" / "types"
        if next_types.exists():
            await log("Clearing .next/types cache...", "debug")
            _clear_next_types_cache(workspace_path)
        
        # =====================================================================
        # Step 4: Null Safety Validation
        # =====================================================================
        await log("Running null safety validation...", "debug")
        null_warnings = _validate_null_safety(workspace_path)
        if null_warnings:
            await log(f"Found {len(null_warnings)} potential null safety issue(s): {', '.join(null_warnings[:5])}", "warning")
        else:
            await log("No null safety issues detected", "debug")
        
        # =====================================================================
        # Step 5: Typecheck + Build (for each service)
        # =====================================================================
        await log("🔨 Running typecheck and build...")
        
        all_stdout = ""
        all_stderr = ""
        all_passed = True
        summaries = []
        
        for i, svc in enumerate(services):
            svc_name = svc.get("name", "app")
            typecheck_cmd = svc.get("typecheck_cmd", "pnpm run typecheck")
            build_cmd = svc.get("build_cmd", "")
            
            await log(f"[{svc_name}] Building service ({i+1}/{len(services)})...")
            
            # Log typecheck
            if typecheck_cmd and _has_script(workspace_path, "typecheck"):
                await log(f"[{svc_name}] Running typecheck: {typecheck_cmd}", "debug")
            
            # Log build
            if build_cmd:
                await log(f"[{svc_name}] Running build: {build_cmd}", "debug")
            
            result = await _run_service_build(svc, workspace_path, run_code_span)
            
            all_stdout += result["stdout"]
            all_stderr += result["stderr"]
            
            if result["status"] == "PASS":
                await log(f"[{svc_name}] Build passed ✓", "success")
                summaries.append(f"{svc_name}: PASS")
            else:
                # Log error details
                error_preview = result["stderr"][:500] if result["stderr"] else result["stdout"][:500]
                await log(f"[{svc_name}] Build failed: {error_preview}", "error")
                summaries.append(f"{svc_name}: FAIL")
                all_passed = False
        
        run_status = "PASS" if all_passed else "FAIL"
        summary = ", ".join(summaries)
        
        # =====================================================================
        # Final Result
        # =====================================================================
        if all_passed:
            await log(f"✅ All builds passed: {summary}")
            await story_logger.message("✅ Build validation passed!")
        else:
            await log(f"❌ Build failed: {summary}", "error")
            await story_logger.message(f"❌ Build validation failed: {summary}")
        
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
        # Re-raise GraphInterrupt - it's expected for pause/cancel
        from langgraph.errors import GraphInterrupt
        if isinstance(e, GraphInterrupt):
            raise
        await log(f"Build validation failed with exception: {str(e)}", "error")
        if run_code_span:
            run_code_span.end(output={"error": str(e)})
        return {**state, "run_status": "PASS", "run_result": {"status": "PASS", "summary": f"Error: {e}"}}
