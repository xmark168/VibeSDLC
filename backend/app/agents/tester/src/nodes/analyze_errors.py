"""Analyze Errors node - Debug failing tests and create fix plan."""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.core_nodes import send_message
from app.agents.tester.src.utils.token_utils import truncate_error_logs

logger = logging.getLogger(__name__)


# =============================================================================
# STRUCTURED ERROR PARSING (MetaGPT-style)
# =============================================================================

@dataclass
class ParsedTestError:
    """Parsed error from test logs. Types: Jest, Playwright, TypeScript, Import."""
    file_path: str
    line: Optional[int]
    column: Optional[int]
    error_code: Optional[str]
    error_type: str
    message: str
    raw_line: str


def _parse_test_errors_structured(logs: str) -> List[ParsedTestError]:
    """Parse test error logs into structured format."""
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
    jest_fail_pattern = r'FAIL\s+([^\s]+\.(?:test|spec)\.tsx?)'
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
    
    # 4. Playwright error: Error: locator.click: ...
    playwright_pattern = r'Error:\s*(locator\.\w+|page\.\w+|expect\(.*?\)\.to\w+).*?:\s*(.+?)(?:\n|$)'
    for match in re.finditer(playwright_pattern, logs, re.DOTALL):
        errors.append(ParsedTestError(
            file_path="e2e/",
            line=None,
            column=None,
            error_code=None,
            error_type="Playwright",
            message=f"{match.group(1)}: {match.group(2).strip()[:100]}",
            raw_line=match.group(0)[:200]
        ))
    
    # 5. Playwright timeout: Timeout 30000ms exceeded
    timeout_pattern = r'Timeout\s+(\d+)ms\s+exceeded'
    for match in re.finditer(timeout_pattern, logs):
        errors.append(ParsedTestError(
            file_path="e2e/",
            line=None,
            column=None,
            error_code="TIMEOUT",
            error_type="Playwright",
            message=f"Timeout {match.group(1)}ms exceeded",
            raw_line=match.group(0)
        ))
    
    # 6. Module not found: Can't resolve 'package' or Cannot find module
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
    
    # 7. Property does not exist: Property 'X' does not exist on type 'Y'
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

# Use custom API endpoint if configured
_api_key = os.getenv("TESTER_API_KEY") or os.getenv("OPENAI_API_KEY")
_base_url = os.getenv("TESTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
_model = os.getenv("TESTER_MODEL", "gpt-4.1")

_llm = ChatOpenAI(
    model=_model,
    temperature=0,
    api_key=_api_key,
    base_url=_base_url,
) if _base_url else ChatOpenAI(model=_model, temperature=0)


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


def _parse_json(content: str) -> dict:
    """Parse JSON from LLM response."""
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass
    
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"[_parse_json] Failed: {content[:300]}...")
        raise e


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


async def analyze_errors(state: TesterState, agent=None) -> dict:
    """Analyze test failures and create fix plan.
    
    This node:
    1. Parses error logs from run_tests
    2. Uses LLM to identify root cause
    3. Creates fix plan (update test_plan for re-implementation)
    4. Increments debug_count
    
    Output:
    - error_analysis: Description of what went wrong
    - test_plan: Updated with fix steps
    - debug_count: Incremented
    - debug_history: Append current analysis
    """
    debug_count = state.get("debug_count", 0)
    max_debug = state.get("max_debug", 3)
    
    print(f"[NODE] analyze_errors - attempt {debug_count + 1}/{max_debug}")
    
    # Check if max retries reached
    if debug_count >= max_debug:
        msg = f"⚠️ Đã thử sửa {max_debug} lần nhưng tests vẫn fail. Dừng debug loop."
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
    
    # Inject parsed errors at the top of the prompt for better LLM understanding
    error_logs = parsed_context + "\n\n" + truncated_logs if parsed_context else truncated_logs
    
    # Format debug history
    history_str = ""
    if debug_history:
        history_str = "\n".join(f"Attempt {i+1}: {h}" for i, h in enumerate(debug_history))
    
    try:
        # Call LLM to analyze errors
        response = await _llm.ainvoke(
            [
                SystemMessage(content=get_system_prompt("analyze_error")),
                HumanMessage(content=get_user_prompt(
                    "analyze_error",
                    error_logs=error_logs,
                    files_modified=", ".join(files_created + files_modified) or "None",
                    debug_count=debug_count + 1,
                    max_debug=max_debug,
                    debug_history=history_str or "First attempt",
                )),
            ],
            config=_cfg(state, f"analyze_errors_{debug_count + 1}"),
        )
        
        result = _parse_json(response.content)
        root_cause = result.get("root_cause", "Unknown error")
        fix_steps = result.get("fix_steps", [])
        
        # Get workspace_path for sanitization
        workspace_path = state.get("workspace_path", "") or state.get("project_path", "")
        
        # Build new test_plan from fix_steps with sanitized file paths
        new_test_plan = []
        for i, step in enumerate(fix_steps):
            raw_file_path = step.get("file_path", "")
            sanitized_path = _sanitize_file_path(raw_file_path, workspace_path)
            
            # Skip steps with empty or invalid paths
            if not sanitized_path:
                logger.warning(f"[analyze_errors] Skipping step with invalid path: {raw_file_path}")
                continue
                
            new_test_plan.append({
                "order": i + 1,
                "type": "fix",
                "file_path": sanitized_path,
                "description": step.get("description", "Fix error"),
                "action": step.get("action", "modify"),
                "scenarios": [],
            })
        
        # Update debug history
        new_history = debug_history.copy()
        new_history.append(root_cause)
        
        # Message
        msg = f"🔍 Phân tích lỗi (lần {debug_count + 1}):\n"
        msg += f"Root cause: {root_cause}\n"
        msg += f"Fix plan: {len(fix_steps)} steps"
        
        await send_message(state, agent, msg, "progress")
        
        logger.info(f"[analyze_errors] Root cause: {root_cause}, Fix steps: {len(fix_steps)}")
        
        # Determine next action
        if fix_steps:
            return {
                "error_analysis": root_cause,
                "test_plan": new_test_plan,
                "total_steps": len(new_test_plan),
                "current_step": 0,
                "debug_count": debug_count + 1,
                "debug_history": new_history,
                "message": msg,
                "action": "IMPLEMENT",
            }
        else:
            # No fix possible
            msg = f"⚠️ Không thể xác định cách fix. Root cause: {root_cause}"
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
        error_msg = f"Lỗi khi phân tích errors: {str(e)}"
        await send_message(state, agent, error_msg, "error")
        return {
            "error": str(e),
            "debug_count": debug_count + 1,
            "message": error_msg,
            "action": "RESPOND",
        }
