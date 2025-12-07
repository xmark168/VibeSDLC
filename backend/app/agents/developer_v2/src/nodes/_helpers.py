"""Shared helper functions for Developer V2 nodes."""
import logging
import re
from datetime import datetime
from pathlib import Path

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools import set_tool_context

logger = logging.getLogger(__name__)


def log(node: str, msg: str, level: str = "info"):
    """Unified logging helper."""
    getattr(logger, level)(f"[{node}] {msg}")


def write_test_log(task_id: str, test_output: str, status: str = "FAIL"):
    """Write test output to logs/developer/test_log directory."""
    try:
        log_dir = Path("logs/developer/test_log")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_task_id = re.sub(r'[^\w\-]', '_', task_id or "unknown")
        filename = f"{safe_task_id}_{timestamp}_{status}.log"
        
        log_path = log_dir / filename
        content = f"""{'='*60}
TEST LOG - {status}
Task: {task_id}
Time: {datetime.now().isoformat()}
{'='*60}

{test_output}
"""
        log_path.write_text(content, encoding='utf-8')
        logger.info(f"[run_code] Test log saved: {log_path}")
    except Exception as e:
        logger.warning(f"[run_code] Failed to write test log: {e}")


def filter_agents_md(content: str) -> str:
    """Remove Common Commands section from AGENTS.md."""
    return re.sub(r'## Common Commands.*?(?=\n## |\Z)', '', content, flags=re.DOTALL).strip()


def extract_relevant_sections(content: str, file_path: str) -> str:
    """Extract relevant sections from AGENTS.md based on file being implemented."""
    sections = []
    
    # Always include first part (conventions, architecture)
    sections.append(content[:4000])
    
    # For API routes, include Error Handling section
    if file_path and ('route.ts' in file_path or 'api/' in file_path):
        error_match = re.search(r'## Error Handling.*?(?=\n## [A-Z]|\Z)', content, re.DOTALL)
        if error_match:
            sections.append(error_match.group(0))
    
    # For test files, include Testing Guidelines section
    if file_path and ('.test.' in file_path or '__tests__' in file_path):
        testing_match = re.search(r'## Testing Guidelines.*?(?=\n## [A-Z]|\Z)', content, re.DOTALL)
        if testing_match:
            sections.append(testing_match.group(0))
    
    return "\n\n---\n\n".join(sections)


def build_static_context(state: dict, current_file: str = "") -> str:
    """Build static context with smart section extraction."""
    parts = []
    
    project_context = state.get("project_context", "")
    if project_context:
        filtered = filter_agents_md(project_context)
        relevant = extract_relevant_sections(filtered, current_file)
        parts.append(relevant)
    
    project_config = state.get("project_config", {})
    if project_config:
        tech_stack = project_config.get('tech_stack', {})
        tech_name = tech_stack.get('name', 'unknown') if isinstance(tech_stack, dict) else 'unknown'
        services = tech_stack.get('service', []) if isinstance(tech_stack, dict) else []
        services_info = ", ".join(s.get("name", "") for s in services) if services else "N/A"
        parts.append(f"## PROJECT CONFIG\nTech Stack: {tech_name}\nServices: {services_info}")
    
    return "\n\n---\n\n".join(parts) if parts else ""


def analyze_test_output(stdout: str, stderr: str, project_type: str = "") -> dict:
    """Analyze test results using regex patterns (no LLM needed)."""
    combined = f"{stdout}\n{stderr}"
    
    # === PASS patterns ===
    pytest_pass = re.search(r"(\d+) passed", combined)
    if pytest_pass:
        passed_count = pytest_pass.group(1)
        failed_match = re.search(r"(\d+) failed", combined)
        if not failed_match or failed_match.group(1) == "0":
            return {"status": "PASS", "summary": f"{passed_count} tests passed"}
    
    if re.search(r"Ran \d+ tests? in [\d.]+s\s*\n\s*OK", combined):
        return {"status": "PASS", "summary": "All tests passed (unittest)"}
    
    jest_pass = re.search(r"Tests:\s*(\d+)\s*passed", combined)
    if jest_pass and "failed" not in combined.lower():
        return {"status": "PASS", "summary": f"{jest_pass.group(1)} tests passed (Jest)"}
    
    mocha_pass = re.search(r"(\d+)\s+passing", combined)
    if mocha_pass and "failing" not in combined.lower():
        return {"status": "PASS", "summary": f"{mocha_pass.group(1)} tests passing (Mocha)"}
    
    if re.search(r"test result: ok\.", combined, re.IGNORECASE):
        return {"status": "PASS", "summary": "All tests passed (Cargo)"}
    
    if re.search(r"^ok\s+", combined, re.MULTILINE) or re.search(r"^PASS$", combined, re.MULTILINE):
        return {"status": "PASS", "summary": "All tests passed (Go)"}
    
    if re.search(r"all\s+tests?\s+pass", combined, re.IGNORECASE):
        return {"status": "PASS", "summary": "All tests passed"}
    
    # === FAIL patterns ===
    pytest_fail = re.search(r"(\d+) failed", combined)
    if pytest_fail and int(pytest_fail.group(1)) > 0:
        return {"status": "FAIL", "summary": f"{pytest_fail.group(1)} tests failed"}
    
    if re.search(r"FAILED|AssertionError|Error:|Traceback", combined):
        return {"status": "FAIL", "summary": "Tests failed with errors"}
    
    jest_fail = re.search(r"Tests:\s*\d+\s*failed", combined)
    if jest_fail:
        return {"status": "FAIL", "summary": "Tests failed (Jest)"}
    
    mocha_fail = re.search(r"(\d+)\s+failing", combined)
    if mocha_fail and int(mocha_fail.group(1)) > 0:
        return {"status": "FAIL", "summary": f"{mocha_fail.group(1)} tests failing (Mocha)"}
    
    if re.search(r"test result: FAILED", combined, re.IGNORECASE):
        return {"status": "FAIL", "summary": "Tests failed (Cargo)"}
    
    if re.search(r"^FAIL\s+", combined, re.MULTILINE):
        return {"status": "FAIL", "summary": "Tests failed (Go)"}
    
    if re.search(r"error:|exception:|failed|failure", combined, re.IGNORECASE):
        if not re.search(r"0\s+(failed|failures?|errors?)", combined, re.IGNORECASE):
            return {"status": "FAIL", "summary": "Tests failed with errors"}
    
    # === No tests or unknown ===
    if re.search(r"no tests (found|ran|collected)", combined, re.IGNORECASE):
        return {"status": "PASS", "summary": "No tests found (skipped)"}
    
    if "exit code: 0" in combined.lower() or "exited with code 0" in combined.lower():
        return {"status": "PASS", "summary": "Command succeeded"}
    
    if "exit code:" in combined.lower() and "exit code: 0" not in combined.lower():
        return {"status": "FAIL", "summary": "Command failed with non-zero exit code"}
    
    return {"status": "PASS", "summary": "Test execution completed"}


def setup_tool_context(workspace_path: str = None, project_id: str = None, task_id: str = None):
    """Set global context for all tools before agent invocation."""
    set_tool_context(root_dir=workspace_path, project_id=project_id, task_id=task_id)


def get_langfuse_span(state: DeveloperState, name: str, input_data: dict = None):
    """Get Langfuse span if handler is available."""
    handler = state.get("langfuse_handler")
    if not handler:
        return None
    try:
        from langfuse import get_client
        langfuse = get_client()
        return langfuse.span(name=name, input=input_data or {})
    except Exception:
        return None
