"""Debug error node - Debug and fix errors based on test output."""
import logging
import re
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_tavily import TavilySearch

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import DebugResult
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, list_directory_safe, write_file_safe
from app.agents.developer_v2.src.tools.shell_tools import execute_shell, semantic_code_search
from app.agents.developer_v2.src.tools import find_test_file, get_markdown_code_block_type
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.utils.prompt_utils import (
    get_prompt as _get_prompt,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context, build_static_context

logger = logging.getLogger(__name__)


def _extract_failing_file(error_logs: str) -> str | None:
    """Extract failing file from error logs (generic patterns)."""
    if not error_logs:
        return None
    
    # Generic patterns - match file paths in error output
    patterns = [
        r'FAIL\s+([^\s]+)',                      # FAIL path/to/file
        r'at\s+.*?\(([^)\s:]+):\d+:\d+\)',       # at X (file:line:col)
        r'File "([^"]+)", line \d+',             # Python style
        r'>\s*\d+\s*\|.*\n.*?([^\s]+):\d+:\d+',  # Error pointer with file
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_logs)
        if match:
            file_path = match.group(1)
            # Skip node_modules and common non-source paths
            if 'node_modules' not in file_path and file_path.strip():
                logger.info(f"[debug_error] Extracted failing file: {file_path}")
                return file_path
    
    return None


def _classify_error(error_logs: str) -> tuple[str, list[str]]:
    """Classify: MISSING_PACKAGE (auto-install) or CODE_ERROR (LLM fix)."""
    # Only check for installable packages (npm/pip packages, not local paths)
    pkg_patterns = [
        r"Cannot find package ['\"]([^'\"@./][^'\"]*)['\"]",
        r"ModuleNotFoundError: No module named ['\"]([^'\"./]+)['\"]",
    ]
    
    packages = []
    for pattern in pkg_patterns:
        matches = re.findall(pattern, error_logs, re.IGNORECASE)
        for pkg in matches:
            # Only external packages (not local paths)
            if not pkg.startswith('.') and '/' not in pkg and pkg not in packages:
                packages.append(pkg)
    
    if packages:
        return ("MISSING_PACKAGE", packages)
    
    return ("CODE_ERROR", [])


def _auto_install_packages(workspace_path: str, packages: list[str], runtime: str = "bun") -> bool:
    """Auto-install missing packages. Returns True if successful."""
    if not packages or not workspace_path:
        return False
    
    if runtime in ["bun"]:
        install_cmd = "bun add -D"
    elif runtime in ["pnpm"]:
        install_cmd = "pnpm add -D"
    elif runtime in ["npm", "node"]:
        install_cmd = "npm install -D"
    elif runtime in ["python"]:
        install_cmd = "pip install"
    else:
        install_cmd = "npm install -D"
    
    success = True
    for pkg in packages:
        try:
            cmd = f"{install_cmd} {pkg}"
            logger.info(f"[debug_error] Auto-installing package: {cmd}")
            result = execute_shell.invoke({
                "command": cmd,
                "working_directory": workspace_path,
                "timeout": 120
            })
            logger.info(f"[debug_error] Install result: {result}")
        except Exception as e:
            logger.warning(f"[debug_error] Failed to install {pkg}: {e}")
            success = False
    
    return success


async def debug_error(state: DeveloperState, agent=None) -> DeveloperState:
    """Debug and fix errors based on test output."""
    print("[NODE] debug_error")
    try:
        run_result = state.get("run_result", {})
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        debug_count = state.get("debug_count", 0)
        max_debug = state.get("max_debug", 5)
        
        if run_result.get("status") == "PASS":
            logger.info("[debug_error] No errors to debug")
            return state
        
        stderr = state.get("run_stderr", "") or run_result.get("stderr", "")
        ok_pattern = r"Ran (\d+) tests? in ([\d.]+)s\s*\n\s*OK"
        if re.search(ok_pattern, stderr):
            logger.info("[debug_error] Tests already pass (OK pattern detected), skipping")
            return {**state, "run_result": {"status": "PASS", "summary": "All tests passed"}}
        
        error_logs = state.get("run_stderr", "") or run_result.get("stderr", "")
        error_type, error_details = _classify_error(error_logs)
        logger.info(f"[debug_error] Error type: {error_type}, details: {error_details}")
        
        if error_type == "MISSING_PACKAGE" and error_details:
            project_config = state.get("project_config", {})
            tech_stack = project_config.get("tech_stack", {})
            services = tech_stack.get("service", []) if isinstance(tech_stack, dict) else []
            runtime = services[0].get("runtime", "bun") if services else "bun"
            
            logger.info(f"[debug_error] Auto-installing missing packages: {error_details}")
            install_success = _auto_install_packages(workspace_path, error_details, runtime)
            
            if install_success:
                logger.info("[debug_error] Packages installed, will retry tests")
                return {
                    **state,
                    "run_result": {"status": "RETRY", "summary": f"Installed packages: {', '.join(error_details)}"},
                }
        
        if debug_count >= max_debug:
            logger.warning(f"[debug_error] Max attempts ({max_debug}) reached")
            return state
        
        # Use error analysis from analyze_error node if available
        error_analysis = state.get("error_analysis")
        fix_strategy = ""
        file_to_fix = ""
        
        if error_analysis and error_analysis.get("file_to_fix"):
            file_to_fix = error_analysis.get("file_to_fix", "")
            fix_strategy = error_analysis.get("fix_strategy", "")
            logger.info(f"[debug_error] Using analysis: type={error_analysis.get('error_type')}, file={file_to_fix}")
        else:
            # Fallback: extract from error logs or use modified files
            logger.warning("[debug_error] No analysis available, using fallback extraction")
            file_to_fix = _extract_failing_file(error_logs)
        
        if not file_to_fix:
            file_to_fix = run_result.get("file_to_fix", "")
        if not file_to_fix:
            files_modified = state.get("files_modified", [])
            file_to_fix = files_modified[0] if files_modified else ""
        
        if not file_to_fix:
            logger.warning("[debug_error] No file identified to fix")
            return {**state, "debug_count": debug_count + 1}
        
        logger.info(f"[debug_error] File: {file_to_fix}")
        
        # Smart file reading
        is_test_file = ".test." in file_to_fix or ".spec." in file_to_fix
        code_content = ""
        test_content = ""
        test_filename = ""
        
        if is_test_file:
            test_filename = file_to_fix
            if workspace_path:
                try:
                    result = read_file_safe.invoke({"file_path": file_to_fix})
                    if result and not result.startswith("Error:"):
                        if "\n\n" in result:
                            test_content = result.split("\n\n", 1)[1]
                        else:
                            test_content = result
                    logger.info(f"[debug_error] Read test file: {file_to_fix} ({len(test_content)} chars)")
                except Exception as e:
                    logger.warning(f"[debug_error] Failed to read test file: {e}")
            
            source_file = file_to_fix.replace(".test.", ".").replace(".spec.", ".")
            if workspace_path:
                try:
                    result = read_file_safe.invoke({"file_path": source_file})
                    if result and not result.startswith("Error:"):
                        if "\n\n" in result:
                            code_content = result.split("\n\n", 1)[1]
                        else:
                            code_content = result
                except Exception:
                    pass
        else:
            if workspace_path:
                try:
                    result = read_file_safe.invoke({"file_path": file_to_fix})
                    if result and not result.startswith("Error:"):
                        if "\n\n" in result:
                            code_content = result.split("\n\n", 1)[1]
                        else:
                            code_content = result
                except Exception:
                    pass
            
            test_filename = find_test_file(workspace_path, file_to_fix) if workspace_path else ""
            if test_filename and workspace_path:
                try:
                    result = read_file_safe.invoke({"file_path": test_filename})
                    if result and not result.startswith("Error:"):
                        if "\n\n" in result:
                            test_content = result.split("\n\n", 1)[1]
                        else:
                            test_content = result
                except Exception:
                    pass
        
        language = get_markdown_code_block_type(file_to_fix)
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        project_config = state.get("project_config", {})
        tech_stack = project_config.get("tech_stack", {})
        services = tech_stack.get("service", []) if isinstance(tech_stack, dict) else []
        
        tech_stack_info = ""
        if services:
            for svc in services:
                runtime = svc.get("runtime", "node")
                install_cmd = svc.get("install_cmd", "npm install")
                tech_stack_info += f"- Runtime: {runtime}, Install command pattern: {install_cmd}\n"
        
        # Get AGENTS.md context
        static_context = build_static_context(state, file_to_fix)
        
        # Get existing files for context (helps LLM fix wrong paths)
        existing_files = ""
        try:
            result = list_directory_safe.invoke({"dir_path": "src"})
            if result and not result.startswith("Error:"):
                existing_files = result[:2000]
        except Exception:
            pass
        
        # Get list of modified files
        files_modified_list = ", ".join(state.get("files_modified", []) or [])
        
        # Build fix guidance from analysis
        fix_guidance = ""
        if fix_strategy:
            fix_guidance = f"\n## Fix Strategy (from analysis)\n{fix_strategy}\n"
        
        sys_prompt = _build_system_prompt("debug_error", agent)
        user_prompt = _get_prompt("debug_error", "user_prompt").format(
            code_filename=file_to_fix,
            language=language,
            code=code_content or "No code available",
            test_filename=test_filename or "No test file",
            test_code=test_content or "No test code available",
            error_logs=state.get("run_stderr", "")[:8000],
            files_modified=files_modified_list or "None",
            existing_files=existing_files or "N/A",
            static_context=static_context[:3000] if static_context else "No guidelines available",
        )
        
        # Add fix guidance if available
        if fix_guidance:
            user_prompt = fix_guidance + user_prompt
        
        tavily_tool = TavilySearch(max_results=3)
        tools = [read_file_safe, list_directory_safe, semantic_code_search, execute_shell, tavily_tool]
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        exploration = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="debug_explore",
            max_iterations=2
        )
        
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:5000]}\n\nNow provide your debug analysis and fixed code."))
        structured_llm = code_llm.with_structured_output(DebugResult)
        debug_result = await structured_llm.ainvoke(messages, config=_cfg(state, "debug_error"))
        
        # Use LLM's suggested file if available, otherwise use detected file
        actual_file_to_fix = debug_result.file_to_fix or file_to_fix
        
        if debug_result.fixed_code and workspace_path:
            try:
                result = write_file_safe.invoke({
                    "file_path": actual_file_to_fix,
                    "content": debug_result.fixed_code,
                    "mode": "w"
                })
                logger.info(f"[debug_error] Written to file: {actual_file_to_fix} ({len(debug_result.fixed_code)} characters)")
            except Exception as e:
                logger.error(f"[debug_error] Failed to write fixed code: {e}")
        
        debug_history = state.get("debug_history", []) or []
        debug_history.append({
            "iteration": debug_count + 1,
            "file": file_to_fix,
            "analysis": debug_result.analysis,
            "root_cause": debug_result.root_cause,
            "fix_description": debug_result.fix_description,
        })
        
        return {
            **state,
            "debug_count": debug_count + 1,
            "last_debug_file": file_to_fix,
            "debug_history": debug_history,
        }
        
    except Exception as e:
        logger.error(f"[debug_error] Error: {e}", exc_info=True)
        return {**state, "debug_count": state.get("debug_count", 0) + 1}
