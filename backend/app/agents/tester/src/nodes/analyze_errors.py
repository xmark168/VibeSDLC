"""Analyze Errors node - Debug failing tests and create fix plan."""

import json
import logging
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.core_nodes import send_message

logger = logging.getLogger(__name__)

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
    
    # Combine error logs
    error_logs = f"STDOUT:\n{run_stdout[-3000:]}\n\nSTDERR:\n{run_stderr[-2000:]}"
    
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
