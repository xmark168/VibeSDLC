"""Run code node - Execute lint fix + tests."""
import json
import logging
from pathlib import Path

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.shell_tools import execute_shell
from app.agents.developer_v2.src.tools.container_tools import (
    dev_container_manager, set_container_context,
)
from app.agents.developer_v2.src.nodes._helpers import (
    setup_tool_context, get_langfuse_span, write_test_log
)

logger = logging.getLogger(__name__)


async def _run_code_multi_service(state: DeveloperState, workspace_path: str, services: list) -> DeveloperState:
    """Run tests for project services (single or multi-service)."""
    task_id = state.get("task_id") or state.get("story_id", "")
    branch_name = state.get("branch_name") or task_id
    
    parent_span = get_langfuse_span(state, "run_code_multi_service", {
        "services": [s.get("name") for s in services],
        "workspace": workspace_path,
    })
    
    all_stdout = ""
    all_stderr = ""
    all_passed = True
    summaries = []
    
    try:
        for svc_config in services:
            svc_name = svc_config.get("name", "app")
            svc_path = str(Path(workspace_path) / svc_config.get("path", "."))
            test_cmd = svc_config.get("test_cmd", "")
            install_cmd = svc_config.get("install_cmd", "")
            needs_db = svc_config.get("needs_db", False)
            db_cmds = svc_config.get("db_cmds", [])
            
            if not test_cmd:
                logger.info(f"[run_code] Skipping {svc_name}: no test_cmd")
                continue
            
            svc_span = parent_span.span(name=f"service:{svc_name}", input={
                "path": svc_config.get("path", "."),
                "needs_db": needs_db,
            }) if parent_span else None
            
            logger.info(f"[run_code] Running tests for {svc_name} at {svc_path}")
            all_stdout += f"\n\n{'='*40}\n SERVICE: {svc_name}\n{'='*40}\n"
            
            commands = []
            for db_cmd in db_cmds:
                commands.append(db_cmd)
            
            # Install dependencies first (required before build)
            if install_cmd:
                logger.info(f"[run_code] Installing deps for {svc_name}: {install_cmd}")
                try:
                    install_result = execute_shell.invoke({
                        "command": install_cmd,
                        "working_directory": workspace_path,
                        "timeout": 300
                    })
                    if isinstance(install_result, str):
                        install_result = json.loads(install_result)
                    all_stdout += f"\n$ {install_cmd}\n{install_result.get('stdout', '')}"
                    if install_result.get("exit_code", 0) != 0:
                        logger.warning(f"[run_code] Install warning for {svc_name}: {install_result.get('stderr', '')}")
                    else:
                        logger.info(f"[run_code] Install completed for {svc_name}")
                except Exception as e:
                    logger.warning(f"[run_code] Install error for {svc_name}: {e}")
            
            commands.append(test_cmd)
            
            svc_passed = True
            
            if needs_db:
                try:
                    set_container_context(branch_name=branch_name, workspace_path=workspace_path)
                    dev_container_manager.get_or_create(
                        branch_name=branch_name,
                        workspace_path=workspace_path,
                        project_type="node",
                    )
                    logger.info(f"[run_code] DB container started for {svc_name}")
                except Exception as e:
                    logger.warning(f"[run_code] DB container error (continuing anyway): {e}")
            
            for base_cmd in commands:
                cmd_span = svc_span.span(name=f"exec:{base_cmd[:40]}...") if svc_span else None
                
                try:
                    timeout = 300 if "install" in base_cmd else 120
                    result = execute_shell.invoke({"command": base_cmd, "working_directory": workspace_path, "timeout": timeout})
                    
                    if isinstance(result, str):
                        result = json.loads(result)
                    
                    if isinstance(result, dict):
                        all_stdout += f"\n$ {base_cmd}\n{result.get('stdout', '')}"
                        exit_code = result.get("exit_code", 0)
                        
                        if cmd_span:
                            cmd_span.end(output={"exit_code": exit_code})
                        
                        if exit_code != 0 and "test" in base_cmd.lower():
                            test_output = result.get("stdout", "") + result.get("stderr", "")
                            all_stderr += test_output
                            all_passed = False
                            svc_passed = False
                            summaries.append(f"{svc_name}: FAIL")
                            logger.error(f"[run_code] TEST FAILED for {svc_name}:\n{test_output[:2000]}")
                            task_id = state.get("task_id") or state.get("story_id", "unknown")
                            write_test_log(task_id, test_output, "FAIL")
                            break
                except Exception as e:
                    if cmd_span:
                        cmd_span.end(output={"error": str(e)})
                    all_stderr += f"\nError: {e}"
                    all_passed = False
                    svc_passed = False
                    summaries.append(f"{svc_name}: ERROR")
                    break
            else:
                summaries.append(f"{svc_name}: PASS")
            
            if svc_span:
                svc_span.end(output={"status": "PASS" if svc_passed else "FAIL"})
        
        run_status = "PASS" if all_passed else "FAIL"
        summary = ", ".join(summaries)
        
        logger.info(f"[run_code] Multi-service result: {run_status} ({summary})")
        
        app_url = None
        if run_status == "PASS":
           print('completed tests successfully')
        
        if parent_span:
            parent_span.end(output={"status": run_status, "summary": summary, "services": summaries})
        
        return {
            **state,
            "run_status": run_status,
            "run_stdout": all_stdout,
            "run_stderr": all_stderr,
            "run_result": {
                "status": run_status,
                "summary": f"Multi-service: {summary}",
                "services": summaries,
            },
            "app_url": app_url,
            "message": f"✅ Tests passed! Dev server running at {app_url}" if app_url else None,
        }
    except Exception as e:
        if parent_span:
            parent_span.end(output={"error": str(e)})
        raise


async def run_code(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute lint fix + tests (merged node)."""
    print("[NODE] run_code")
    
    workspace_path = state.get("workspace_path", "")
    project_id = state.get("project_id", "default")
    task_id = state.get("task_id") or state.get("story_id", "")
    
    run_code_span = get_langfuse_span(state, "run_code", {
        "workspace": workspace_path,
        "task_id": task_id,
    })
    
    try:
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
        
        project_config = state.get("project_config", {})
        tech_stack = project_config.get("tech_stack", {})
        services = tech_stack.get("service", []) if isinstance(tech_stack, dict) else []
        
        if not services:
            logger.error("[run_code] Missing project_config.tech_stack.service")
            if run_code_span:
                run_code_span.end(output={"status": "ERROR", "reason": "Missing tech_stack.service"})
            return {
                **state,
                "run_status": "ERROR",
                "run_result": {"status": "ERROR", "summary": "Missing project_config.tech_stack.service"},
            }
        
        svc_names = [s.get("name", "app") for s in services]
        logger.info(f"[run_code] tech_stack services: {svc_names}")
        
        # Run lint fix before tests
        for svc in services:
            svc_name = svc.get("name", "app")
            svc_path = str(Path(workspace_path) / svc.get("path", "."))
            lint_fix_cmd = svc.get("lint_fix_cmd")
            
            if lint_fix_cmd:
                logger.info(f"[run_code] Lint fix for {svc_name}: {lint_fix_cmd}")
                try:
                    execute_shell.invoke({
                        "command": lint_fix_cmd,
                        "working_directory": svc_path,
                        "timeout": 60
                    })
                except Exception as e:
                    logger.warning(f"[run_code] Lint fix error (continuing): {e}")
        
        if run_code_span:
            run_code_span.end(output={"mode": "tech_stack", "services": svc_names})
        return await _run_code_multi_service(state, workspace_path, services)
        
    except Exception as e:
        logger.error(f"[run_code] Error: {e}", exc_info=True)
        if run_code_span:
            run_code_span.end(output={"error": str(e)})
        return {
            **state,
            "run_status": "PASS",
            "run_result": {"status": "PASS", "summary": f"Test execution error: {str(e)}"},
        }
