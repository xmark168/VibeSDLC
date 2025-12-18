"""Analyze Errors node - Debug failing tests and create fix plan."""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.nodes.helpers import send_message, generate_user_message, get_llm_config as _cfg
from app.agents.tester.src.schemas import FixStep, ErrorAnalysisOutput
from app.utils.token_utils import truncate_error_logs
from app.core.agent.llm_factory import get_llm, MAX_DEBUG_ATTEMPTS
from app.agents.tester.src.nodes.plan import _get_existing_routes

logger = logging.getLogger(__name__)



def _extract_component_imports(test_content: str) -> List[str]:
    """Extract component import paths from test file.
    
    Returns list of component paths like:
    - src/components/home/HeroSection.tsx
    - src/components/search/SearchBar.tsx
    """
    components = []
    
    # Pattern: import { X } from '@/components/...'
    import_pattern = r"import\s+\{[^}]+\}\s+from\s+['\"]@/components/([^'\"]+)['\"]"
    for match in re.finditer(import_pattern, test_content):
        component_path = f"src/components/{match.group(1)}"
        if not component_path.endswith('.tsx') and not component_path.endswith('.ts'):
            component_path += '.tsx'
        components.append(component_path)
    
    # Pattern: import X from '@/components/...'
    default_import_pattern = r"import\s+\w+\s+from\s+['\"]@/components/([^'\"]+)['\"]"
    for match in re.finditer(default_import_pattern, test_content):
        component_path = f"src/components/{match.group(1)}"
        if not component_path.endswith('.tsx') and not component_path.endswith('.ts'):
            component_path += '.tsx'
        if component_path not in components:
            components.append(component_path)
    
    return components


def _load_component_sources(workspace_path: str, component_paths: List[str]) -> str:
    """Load component source code for comparison with test assertions.
    
    Returns formatted string with component sources.
    """
    if not workspace_path or not component_paths:
        return ""
    
    sources = []
    for comp_path in component_paths[:3]:  # Limit to 3 components
        full_path = os.path.join(workspace_path, comp_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Truncate to 2000 chars per component
                if len(content) > 2000:
                    content = content[:2000] + "\n... (truncated)"
                sources.append(f"### {comp_path}\n```tsx\n{content}\n```")
                logger.info(f"[_load_component_sources] Loaded: {comp_path} ({len(content)} chars)")
            except Exception as e:
                logger.warning(f"[_load_component_sources] Failed to load {comp_path}: {e}")
    
    if sources:
        return "\n\n## COMPONENT SOURCE CODE (compare with test assertions!):\n" + "\n\n".join(sources)
    return ""


def _load_test_file_content(workspace_path: str, test_file: str) -> str:
    """Load test file content for analysis."""
    if not workspace_path or not test_file:
        return ""
    
    full_path = os.path.join(workspace_path, test_file)
    if os.path.exists(full_path):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"[_load_test_file_content] Failed to load {test_file}: {e}")
    return ""


# =============================================================================
# STRUCTURED ERROR PARSING (MetaGPT-style)
# =============================================================================

@dataclass
class ParsedTestError:
    """Parsed error from test logs. Types: Jest, TypeScript, Import."""
    file_path: str
    line: Optional[int]
    column: Optional[int]
    error_code: Optional[str]
    error_type: str
    message: str
    raw_line: str


def _parse_test_errors_structured(logs: str) -> List[ParsedTestError]:
    """Parse test error logs into structured format (Jest only - no e2e)."""
    errors = []
    
    # 1. TypeScript error format: src/file.tsx(line,col): error TS2307: message
    ts_pattern = r'([^\s(]+\.tsx?)\((\d+),(\d+)\):\s*error\s*(TS\d+):\s*(.+)'
    for match in re.finditer(ts_pattern, logs):
        errors.append(ParsedTestError(
            file_path=match.group(1),
            line=int(match.group(2)),
            column=int(match.group(3)),
            error_code=match.group(4),
            error_type="TypeScript",
            message=match.group(5).strip(),
            raw_line=match.group(0)
        ))
    
    # 2. Jest test error: FAIL src/file.test.ts + error message
    jest_fail_pattern = r'FAIL\s+([^\s]+\.test\.tsx?)'
    for match in re.finditer(jest_fail_pattern, logs):
        errors.append(ParsedTestError(
            file_path=match.group(1),
            line=None,
            column=None,
            error_code=None,
            error_type="Jest",
            message="Test failed",
            raw_line=match.group(0)
        ))
    
    # 3. Jest assertion error: expect(received).toEqual(expected)
    jest_expect_pattern = r'expect\((.+?)\)\.(\w+)\((.+?)\)'
    for match in re.finditer(jest_expect_pattern, logs):
        errors.append(ParsedTestError(
            file_path="unknown",
            line=None,
            column=None,
            error_code=None,
            error_type="Jest-Assertion",
            message=f"expect({match.group(1)}).{match.group(2)}({match.group(3)}) failed",
            raw_line=match.group(0)
        ))
    
    # 4. Module not found: Can't resolve 'package' or Cannot find module
    module_pattern = r"(?:Cannot find module|Module not found|Can't resolve)\s*['\"]([^'\"]+)['\"]"
    for match in re.finditer(module_pattern, logs):
        module_name = match.group(1)
        errors.append(ParsedTestError(
            file_path="unknown",
            line=None,
            column=None,
            error_code="MODULE_NOT_FOUND",
            error_type="Import",
            message=f"Cannot find module '{module_name}'",
            raw_line=match.group(0)
        ))
    
    # 5. Property does not exist: Property 'X' does not exist on type 'Y'
    prop_pattern = r"Property\s+'(\w+)'\s+does not exist on type\s+'([^']+)'"
    for match in re.finditer(prop_pattern, logs):
        errors.append(ParsedTestError(
            file_path="unknown",
            line=None,
            column=None,
            error_code="TS2339",
            error_type="TypeScript",
            message=f"Property '{match.group(1)}' does not exist on type '{match.group(2)}'",
            raw_line=match.group(0)
        ))
    
    # 6. ARIA-SELECTED errors: Expected "true" but got "false"
    aria_pattern = r'(?:aria-selected|toHaveAttribute\([\'"]aria-selected[\'"])'
    if re.search(aria_pattern, logs, re.IGNORECASE):
        errors.append(ParsedTestError(
            file_path="unknown",
            line=None,
            column=None,
            error_code="ARIA_SELECTED",
            error_type="Unit-Test",
            message="aria-selected assertion failed - component has no selection state",
            raw_line="aria-selected test failure"
        ))
    
    # 7. FETCH assertion errors: expect(fetch).toHaveBeenCalled
    fetch_pattern = r'expect\(fetch\)\.toHaveBeenCalled'
    if re.search(fetch_pattern, logs):
        errors.append(ParsedTestError(
            file_path="unknown",
            line=None,
            column=None,
            error_code="FETCH_ASSERTION",
            error_type="Unit-Test",
            message="fetch assertion in unit test - should test UI rendering instead",
            raw_line="fetch assertion failure"
        ))
    
    # 8. Error message not found (no error state)
    error_ui_pattern = r"Unable to find.*(?:error|Error|failed|Failed)"
    if re.search(error_ui_pattern, logs):
        errors.append(ParsedTestError(
            file_path="unknown",
            line=None,
            column=None,
            error_code="NO_ERROR_STATE",
            error_type="Unit-Test",
            message="Error UI assertion failed - component does not render error state",
            raw_line="error UI not found"
        ))
    
    # 9. COMPONENT_MISMATCH: Unable to find element (placeholder, text, role)
    mismatch_patterns = [
        (r"Unable to find an element with the placeholder text[:\s]*['\"]?([^'\"]+)", "placeholder"),
        (r"Unable to find an element with the text[:\s]*['\"]?([^'\"]+)", "text"),
        (r"Unable to find role=\"(\w+)\"", "role"),
        (r"TestingLibraryElementError: Unable to find", "element"),
    ]
    for pattern, elem_type in mismatch_patterns:
        match = re.search(pattern, logs, re.IGNORECASE)
        if match:
            elem_value = match.group(1) if match.lastindex else "unknown"
            errors.append(ParsedTestError(
                file_path="unknown",
                line=None,
                column=None,
                error_code="COMPONENT_MISMATCH",
                error_type="Unit-Test",
                message=f"Component does not have {elem_type}='{elem_value}'. Compare test with component source!",
                raw_line=match.group(0)[:100]
            ))
            break  # Only add one mismatch error
    
    # 10. MULTIPLE_ELEMENTS: Found multiple elements with text/role
    multiple_pattern = r"Found multiple elements with the (?:text|role)[:\s]*['\"]?([^'\"]+)"
    match = re.search(multiple_pattern, logs, re.IGNORECASE)
    if match:
        elem_value = match.group(1) if match.lastindex else "unknown"
        errors.append(ParsedTestError(
            file_path="unknown",
            line=None,
            column=None,
            error_code="MULTIPLE_ELEMENTS",
            error_type="Unit-Test",
            message=f"Multiple elements found with '{elem_value}'. Use getAllByText or getByRole with specific name.",
            raw_line=match.group(0)[:100]
        ))
    
    # 11. TIMEOUT: waitFor timeout or async operation timeout
    timeout_pattern = r"(?:waitFor|findBy|Timeout).*(?:timed out|exceeded|timeout)"
    if re.search(timeout_pattern, logs, re.IGNORECASE):
        errors.append(ParsedTestError(
            file_path="unknown",
            line=None,
            column=None,
            error_code="TIMEOUT",
            error_type="Unit-Test",
            message="Async operation timed out. Use findBy* instead of getBy* for async content, or check if element exists.",
            raw_line="timeout error"
        ))
    
    # 12. NOT_FOUND: Element/text not in document
    not_found_pattern = r"Unable to find.*(?:text|element|role).*(?:in|within|document)"
    if re.search(not_found_pattern, logs, re.IGNORECASE) and not any(e.error_code == "COMPONENT_MISMATCH" for e in errors):
        errors.append(ParsedTestError(
            file_path="unknown",
            line=None,
            column=None,
            error_code="NOT_FOUND",
            error_type="Unit-Test",
            message="Element not found in document. Check if element exists in component source code.",
            raw_line="element not found"
        ))
    
    return errors


def _format_parsed_errors(errors: List[ParsedTestError]) -> str:
    """Format parsed errors for LLM context."""
    if not errors:
        return ""
    
    # Deduplicate by message
    seen = set()
    unique_errors = []
    for err in errors:
        key = (err.error_type, err.message[:50])
        if key not in seen:
            seen.add(key)
            unique_errors.append(err)
    
    lines = ["## PARSED ERRORS (fix these!):\n"]
    for i, err in enumerate(unique_errors[:8], 1):
        loc = f":{err.line}" if err.line else ""
        code = f" [{err.error_code}]" if err.error_code else ""
        lines.append(f"{i}. **[{err.error_type}]** {err.file_path}{loc}{code}: {err.message}")
    
    if len(unique_errors) > 8:
        lines.append(f"\n... and {len(unique_errors) - 8} more errors")
    
    return "\n".join(lines)

_llm = get_llm("analyze")


def _cfg(config: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback from runtime config."""
    callbacks = config.get("callbacks", []) if config else []
    return {"callbacks": callbacks, "run_name": name} if callbacks else {}


def _is_test_file(file_path: str) -> bool:
    """Check if file_path is a test file (not source code).
    
    Test files must contain one of:
    - __tests__/
    - .test.ts or .test.tsx
    Note: Only integration tests supported (no e2e/spec files)
    """
    if not file_path:
        return False
    
    path_lower = file_path.lower()
    
    # Must be a test file (integration only - no e2e)
    test_indicators = [
        "__tests__/",
        ".test.ts",
        ".test.tsx",
        "/tests/",
    ]
    
    is_test = any(ind in path_lower for ind in test_indicators)
    
    # Additional check: reject if it looks like source code
    if not is_test:
        # Check for source file patterns
        source_patterns = [
            "src/app/api/",  # API routes (without __tests__)
            "src/components/",
            "src/lib/",
            "route.ts",
            "page.tsx",
            "layout.tsx",
        ]
        if any(pat in path_lower for pat in source_patterns):
            return False
    
    return is_test


def _sanitize_file_path(file_path: str, workspace_path: str = "") -> str:
    """Sanitize file_path from LLM to be relative to workspace.
    
    Handles:
    - Paths ending with '/' (directory)
    - Paths containing 'backend/projects/{uuid}/' prefix
    - Paths containing 'projects/{uuid}/' prefix
    - Absolute paths
    """
    if not file_path:
        return file_path
    
    # Remove trailing slash (directory indicator)
    file_path = file_path.rstrip("/\\")
    
    # Remove common wrong prefixes from LLM
    wrong_prefixes = [
        "backend/projects/",
        "projects/",
        "backend\\projects\\",
        "projects\\",
    ]
    
    for prefix in wrong_prefixes:
        if prefix in file_path:
            # Find the UUID pattern and remove everything up to and including it
            # Match UUID pattern like: 30bdd1ec-7720-45c7-82ed-a5842fc69bde
            uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
            match = re.search(f"{re.escape(prefix)}{uuid_pattern}[/\\\\]?", file_path, re.IGNORECASE)
            if match:
                # Remove the matched prefix
                file_path = file_path[match.end():]
                logger.info(f"[_sanitize_file_path] Removed wrong prefix, result: {file_path}")
                break
    
    # Remove leading slashes
    file_path = file_path.lstrip("/\\")
    
    # If path is empty after sanitization, return empty
    if not file_path:
        logger.warning("[_sanitize_file_path] Path became empty after sanitization")
        return ""
    
    return file_path


async def analyze_errors(state: TesterState, config: dict = None, agent=None) -> dict:
    """Analyze test failures and create fix plan.
    
    Args:
        state: Current tester state
        config: LangGraph runtime config (contains callbacks for Langfuse)
        agent: Tester agent instance
    
    This node:
    1. Parses error logs from run_tests
    2. Uses LLM to identify root cause
    3. Creates fix plan (update test_plan for re-implementation)
    4. Increments debug_count
    
    Includes interrupt signal check for pause/cancel support.
    
    Output:
    - error_analysis: Description of what went wrong
    - test_plan: Updated with fix steps
    - debug_count: Incremented
    - debug_history: Append current analysis
    """
    from langgraph.types import interrupt
    from app.agents.tester.src.utils.interrupt import check_interrupt_signal
    from app.agents.developer.src.utils.story_logger import StoryLogger
    
    config = config or {}  # Ensure config is not None
    
    # Create story logger
    story_logger = StoryLogger.from_state(state, agent).with_node("analyze_errors")
    
    # Check for pause/cancel signal
    story_id = state.get("story_id", "")
    if story_id:
        signal = check_interrupt_signal(story_id)
        if signal:
            await story_logger.info(f"Interrupt signal received: {signal}")
            interrupt({"reason": signal, "story_id": story_id, "node": "analyze_errors"})
    
    debug_count = state.get("debug_count", 0)
    max_debug = state.get("max_debug", 3)
    
    # Check if max retries reached
    if debug_count >= max_debug:
        msg = await generate_user_message(
            "max_retries",
            f"tried {max_debug} times, tests still failing",
            agent
        )
        logger.warning(f"[analyze_errors] Max debug attempts ({max_debug}) reached")
        await send_message(state, agent, msg, "error")
        return {
            "error_analysis": "Max debug attempts reached",
            "message": msg,
            "action": "RESPOND",
        }
    
    # Get error context
    run_stdout = state.get("run_stdout", "")
    run_stderr = state.get("run_stderr", "")
    run_result = state.get("run_result", {})
    files_modified = state.get("files_modified", [])
    files_created = state.get("files_created", [])
    debug_history = state.get("debug_history", [])
    
    # Combine error logs and truncate intelligently
    raw_logs = f"STDOUT:\n{run_stdout}\n\nSTDERR:\n{run_stderr}"
    
    # ==============================================
    # PRIORITY 1: TYPESCRIPT ERRORS (from typecheck)
    # ==============================================
    typescript_errors = run_result.get("typecheck_errors", [])
    typescript_context = ""
    if typescript_errors:
        typescript_context = "## ⚠️ TYPESCRIPT ERRORS (fix these FIRST!):\n"
        typescript_context += "These are COMPILATION errors - tests cannot run until fixed.\n\n"
        for i, err in enumerate(typescript_errors[:10], 1):
            typescript_context += f"{i}. {err}\n"
        typescript_context += "\n---\n\n"
        logger.info(f"[analyze_errors] Found {len(typescript_errors)} TypeScript errors (priority)")
        for err in typescript_errors[:3]:
            logger.info(f"[analyze_errors]   TS: {err[:100]}")
    
    # ==============================================
    # STRUCTURED ERROR PARSING (MetaGPT-style)
    # ==============================================
    parsed_errors = _parse_test_errors_structured(raw_logs)
    parsed_context = _format_parsed_errors(parsed_errors)
    
    if parsed_errors:
        logger.info(f"[analyze_errors] Parsed {len(parsed_errors)} structured errors:")
        for err in parsed_errors[:3]:
            logger.info(f"[analyze_errors]   - [{err.error_type}] {err.file_path}: {err.message[:60]}")
    
    # Truncate logs intelligently (keep more from end where errors usually are)
    truncated_logs = truncate_error_logs(raw_logs, max_tokens=3000)
    
    # Combine: TypeScript first (priority), then parsed errors, then truncated logs
    error_logs = typescript_context + parsed_context + "\n\n" + truncated_logs if parsed_context else typescript_context + truncated_logs
    
    # Format debug history
    history_str = ""
    if debug_history:
        history_str = "\n".join(f"Attempt {i+1}: {h}" for i, h in enumerate(debug_history))
    
    # Get workspace path and existing routes (same constraint as plan_tests)
    workspace_path = state.get("workspace_path", "") or state.get("project_path", "")
    existing_routes = []
    if workspace_path:
        existing_routes = _get_existing_routes(workspace_path)
    existing_routes_text = "\n".join(f"- {r}" for r in existing_routes) if existing_routes else "No API routes found."
    
    # ==============================================
    # COMPONENT SOURCE LOADING FOR UNIT TESTS
    # ==============================================
    component_source_context = ""
    failing_unit_tests = [
        err.file_path for err in parsed_errors 
        if err.file_path and "unit" in err.file_path.lower() and err.file_path.endswith('.tsx')
    ]
    
    if failing_unit_tests and workspace_path:
        for test_file in failing_unit_tests[:2]:  # Limit to 2 test files
            test_content = _load_test_file_content(workspace_path, test_file)
            if test_content:
                # Extract component imports from test
                component_paths = _extract_component_imports(test_content)
                if component_paths:
                    logger.info(f"[analyze_errors] Found {len(component_paths)} components in {test_file}: {component_paths}")
                    component_source_context += _load_component_sources(workspace_path, component_paths)
                    
                    # Also include the test file content for comparison
                    component_source_context += f"\n\n## FAILING TEST FILE:\n### {test_file}\n```tsx\n{test_content[:3000]}\n```"
    
    # Add component source to error_logs
    if component_source_context:
        error_logs = error_logs + "\n\n" + component_source_context
        logger.info(f"[analyze_errors] Added component source context ({len(component_source_context)} chars)")
    
    try:
        # Call LLM with structured output
        structured_llm = _llm.with_structured_output(ErrorAnalysisOutput)
        result = await structured_llm.ainvoke(
            [
                SystemMessage(content=get_system_prompt("analyze_error")),
                HumanMessage(content=get_user_prompt(
                    "analyze_error",
                    error_logs=error_logs,
                    files_modified=", ".join(files_created + files_modified) or "None",
                    existing_routes=existing_routes_text,
                    debug_count=debug_count + 1,
                    max_debug=max_debug,
                    debug_history=history_str or "First attempt",
                )),
            ],
            # Pass config from runtime (not state) to avoid checkpoint serialization issues
            config=_cfg(config, f"analyze_errors_{debug_count + 1}"),
        )
        
        root_cause = result.root_cause
        error_code = result.error_code
        fix_steps = [step.model_dump() for step in result.fix_steps]
        
        # Build new test_plan from fix_steps with sanitized file paths
        new_test_plan = []
        skipped_source_files = []
        
        for i, step in enumerate(fix_steps):
            raw_file_path = step.get("file_path", "")
            sanitized_path = _sanitize_file_path(raw_file_path, workspace_path)
            
            # Skip steps with empty or invalid paths
            if not sanitized_path:
                logger.warning(f"[analyze_errors] Skipping step with invalid path: {raw_file_path}")
                continue
            
            # CRITICAL: Only allow test files, reject source files
            if not _is_test_file(sanitized_path):
                logger.warning(f"[analyze_errors] REJECTED source file (tester cannot modify): {sanitized_path}")
                skipped_source_files.append(sanitized_path)
                continue
            
            # Include find_code and replace_with for precise fixing
            find_code = step.get("find_code", "")
            replace_with = step.get("replace_with", "")
            
            new_test_plan.append({
                "order": len(new_test_plan) + 1,
                "type": "fix",
                "file_path": sanitized_path,
                "description": step.get("description", "Fix error"),
                "action": step.get("action", "modify"),
                "error_code": error_code,
                "find_code": find_code,
                "replace_with": replace_with,
                "scenarios": [],
            })
            
            if find_code:
                logger.info(f"[analyze_errors] Fix step {i+1}: find '{find_code[:50]}...' -> replace with '{replace_with[:30] if replace_with else 'DELETE'}'")
        
        # Log if any source files were rejected
        if skipped_source_files:
            logger.info(f"[analyze_errors] Rejected {len(skipped_source_files)} source files: {skipped_source_files}")
        
        # Update debug history
        new_history = debug_history.copy()
        new_history.append(root_cause)
        
        # Message (persona-driven intro + technical details)
        intro = await generate_user_message(
            "analyzing",
            f"attempt {debug_count + 1}, found {len(fix_steps)} fix steps",
            agent
        )
        msg = f"{intro}\nRoot cause: {root_cause}\nFix plan: {len(fix_steps)} steps"
        
        await send_message(state, agent, msg, "progress")
        
        logger.info(f"[analyze_errors] Root cause: {root_cause}, Fix steps: {len(fix_steps)}")
        
        # Determine next action
        if fix_steps:
            # Extract file paths that need fixing - this triggers re-implementation mode
            # in implement_tests, which preserves existing files_modified (like integration tests)
            failed_files = [step.get("file_path") for step in new_test_plan if step.get("file_path")]
            
            return {
                "error_analysis": root_cause,
                "test_plan": new_test_plan,
                "total_steps": len(new_test_plan),
                "current_step": 0,
                "debug_count": debug_count + 1,
                "debug_history": new_history,
                "failed_files": failed_files,  # Triggers re-implementation mode
                "message": msg,
                "action": "IMPLEMENT",
            }
        else:
            # No fix possible (persona message)
            msg = await generate_user_message(
                "max_retries",
                f"cannot determine fix for: {root_cause}",
                agent
            )
            await send_message(state, agent, msg, "error")
            return {
                "error_analysis": root_cause,
                "debug_count": debug_count + 1,
                "debug_history": new_history,
                "message": msg,
                "action": "RESPOND",
            }
        
    except Exception as e:
        logger.error(f"[analyze_errors] Error: {e}", exc_info=True)
        error_msg = await generate_user_message(
            "default",
            f"Error analyzing: {str(e)[:100]}",
            agent
        )
        await send_message(state, agent, error_msg, "error")
        return {
            "error": str(e),
            "debug_count": debug_count + 1,
            "message": error_msg,
            "action": "RESPOND",
        }
