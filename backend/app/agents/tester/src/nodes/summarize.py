"""Summarize node - MetaGPT-style test summarization with IS_PASS gate."""
import logging
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.tester.src.state import TesterState

logger = logging.getLogger(__name__)

# LLM setup
_api_key = os.getenv("TESTER_API_KEY") or os.getenv("OPENAI_API_KEY")
_base_url = os.getenv("TESTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
_model = os.getenv("TESTER_MODEL", "gpt-4.1")

_llm = (
    ChatOpenAI(model=_model, temperature=0, api_key=_api_key, base_url=_base_url)
    if _base_url
    else ChatOpenAI(model=_model, temperature=0)
)


SUMMARIZE_SYSTEM_PROMPT = """You are a Senior QA Engineer performing final test review.
Your task is to review ALL test files and:
1. Summarize what tests were implemented
2. Detect any incomplete tests, missing assertions, or issues
3. Decide if test implementation IS_PASS (complete) or needs more work

## Review Each Test File For:
- All planned scenarios are covered
- Proper assertions for each test case
- Proper mocking of external dependencies
- describe/it structure is correct
- No TODO comments or placeholder code
- Error cases are tested

## Output Format
```
## Summary
[Brief summary of tests implemented]

## Files Reviewed
- file1.test.ts: [status - OK/HAS_ISSUES] [brief description]
- file2.spec.ts: [status - OK/HAS_ISSUES] [brief description]

## TODOs Found
{
  "file_path": "issue description",
  "file_path2": "issue description"
}
(Use {} if no TODOs found)

----
Does the above log indicate anything that needs to be done?
If there are any tasks to be completed, please answer 'NO' along with the to-do list in JSON format;
otherwise, answer 'YES' in JSON format.

## IS_PASS: YES|NO

## Feedback (if NO)
[What needs to be fixed]
```
"""

SUMMARIZE_INPUT_TEMPLATE = """## Test Plan Summary
{test_plan_summary}

## Test Files Implemented
{files_content}

Review all test files above and provide summary with IS_PASS decision.
"""


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {"run_name": name}


def _read_test_files(workspace_path: str, files_created: list) -> dict:
    """Read content of all created test files."""
    files_content = {}

    for file_path in files_created:
        full_path = os.path.join(workspace_path, file_path) if workspace_path else file_path

        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                files_content[file_path] = content[:3000]
            except Exception as e:
                files_content[file_path] = f"[Error reading file: {e}]"
        else:
            files_content[file_path] = "[File not found]"

    return files_content


def _format_files_for_prompt(files_content: dict) -> str:
    """Format files content for prompt."""
    parts = []
    for file_path, content in files_content.items():
        ext = file_path.split(".")[-1] if "." in file_path else ""
        lang = "typescript" if ext in ["ts", "tsx"] else "javascript" if ext in ["js", "jsx"] else ext
        parts.append(f"### {file_path}\n```{lang}\n{content}\n```\n")

    return "\n".join(parts) if parts else "No test files to review"


def _format_test_plan_summary(test_plan: list) -> str:
    """Format test plan for prompt."""
    if not test_plan:
        return "No test plan"

    parts = []
    for step in test_plan:
        test_type = step.get("type", "integration")
        description = step.get("description", "N/A")
        scenarios = step.get("scenarios", [])
        file_path = step.get("file_path", "N/A")

        parts.append(f"- [{test_type}] {description}")
        parts.append(f"  File: {file_path}")
        if scenarios:
            parts.append(f"  Scenarios: {', '.join(scenarios[:3])}")

    return "\n".join(parts)


def _parse_summarize_response(response: str) -> dict:
    """Parse summarize response."""
    result = {
        "summary": "",
        "files_reviewed": "",
        "todos": {},
        "is_pass": "YES",
        "feedback": "",
    }

    # Extract summary
    summary_match = re.search(r"## Summary\s*\n([\s\S]*?)(?=## Files|## TODOs|$)", response)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()

    # Extract files reviewed
    files_match = re.search(
        r"## Files Reviewed\s*\n([\s\S]*?)(?=## TODOs|## IS_PASS|$)", response
    )
    if files_match:
        result["files_reviewed"] = files_match.group(1).strip()

    # Extract TODOs
    todos_match = re.search(r"## TODOs Found\s*\n\{([\s\S]*?)\}", response)
    if todos_match:
        todos_str = todos_match.group(1).strip()
        if todos_str:
            for line in todos_str.split("\n"):
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip().strip("\"'")
                    value = parts[1].strip().strip("\",'\n")
                    if key:
                        result["todos"][key] = value

    # Extract IS_PASS
    is_pass_match = re.search(r"## IS_PASS:\s*(YES|NO)", response, re.IGNORECASE)
    if is_pass_match:
        result["is_pass"] = is_pass_match.group(1).upper()

    # Extract feedback
    feedback_match = re.search(r"## Feedback[^\n]*\n([\s\S]*?)$", response)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip()

    return result


async def summarize(state: TesterState, agent=None) -> dict:
    """Summarize all test files and decide IS_PASS (MetaGPT-style).

    Returns:
        State with:
        - summary: Summary of tests
        - todos: Dict of files with issues
        - is_pass: "YES" or "NO"
        - summarize_feedback: Feedback if NO
    """
    print("[NODE] summarize")

    try:
        workspace_path = state.get("workspace_path", "") or state.get("project_path", "")
        files_created = state.get("files_created", [])
        test_plan = state.get("test_plan", [])

        if not files_created:
            logger.info("[summarize] No test files created, passing")
            return {
                "summary": "No test files were created",
                "todos": {},
                "is_pass": "YES",
                "summarize_feedback": "",
            }

        # Read all test files
        files_content = _read_test_files(workspace_path, files_created)
        files_formatted = _format_files_for_prompt(files_content)
        test_plan_summary = _format_test_plan_summary(test_plan)

        # Build prompt
        input_text = SUMMARIZE_INPUT_TEMPLATE.format(
            test_plan_summary=test_plan_summary,
            files_content=files_formatted,
        )

        messages = [
            SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT),
            HumanMessage(content=input_text),
        ]

        # Get summary from LLM
        response = await _llm.ainvoke(messages, config=_cfg(state, "summarize_tests"))
        response_text = response.content if hasattr(response, "content") else str(response)

        # Parse response
        result = _parse_summarize_response(response_text)

        logger.info(f"[summarize] IS_PASS: {result['is_pass']}, TODOs: {len(result['todos'])}")

        if result["todos"]:
            logger.info(f"[summarize] Issues found: {list(result['todos'].keys())}")

        # Increment summarize_count if IS_PASS=NO, reset if YES
        current_count = state.get("summarize_count", 0)
        new_count = current_count + 1 if result["is_pass"] == "NO" else 0

        # Create fix_steps when IS_PASS=NO
        fix_steps = []
        seen_files = set()  # Avoid duplicates
        if result["is_pass"] == "NO" and result["todos"]:
            for file_path, issue in result["todos"].items():
                # Normalize file path - remove escape sequences and use forward slashes
                normalized_path = file_path.replace("\\\\", "/").replace("\\", "/")
                
                # Skip invalid paths (config files, non-test files)
                if not normalized_path.endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx')):
                    logger.warning(f"[summarize] Skipping non-test file: {normalized_path}")
                    continue
                
                # Skip if already seen (handle duplicate paths with different formats)
                base_name = os.path.basename(normalized_path)
                if base_name in seen_files:
                    continue
                seen_files.add(base_name)
                
                # Check if file exists (try multiple paths)
                actual_path = None
                possible_paths = [
                    normalized_path,
                    os.path.join(workspace_path, normalized_path) if workspace_path else None,
                ]
                for p in possible_paths:
                    if p and os.path.exists(p):
                        actual_path = normalized_path
                        break
                
                if not actual_path:
                    # File doesn't exist - skip this fix step
                    logger.warning(f"[summarize] File not found, skipping: {normalized_path}")
                    continue
                
                fix_steps.append({
                    "order": len(fix_steps) + 1,
                    "type": "fix",
                    "description": f"Fix issue in {normalized_path}: {issue}",
                    "file_path": normalized_path,
                    "action": "modify",
                    "scenarios": [],
                })
            logger.info(f"[summarize] Created {len(fix_steps)} fix_steps")

        return {
            "summary": result["summary"],
            "todos": result["todos"],
            "is_pass": result["is_pass"],
            "summarize_feedback": result["feedback"],
            "files_reviewed": result["files_reviewed"],
            "summarize_count": new_count,
            # Replace test_plan with fix_steps when IS_PASS=NO
            "test_plan": fix_steps if fix_steps else state.get("test_plan", []),
            "total_steps": len(fix_steps) if fix_steps else state.get("total_steps", 0),
            "current_step": 0 if fix_steps else state.get("current_step", 0),
        }

    except Exception as e:
        logger.error(f"[summarize] Error: {e}", exc_info=True)
        return {
            "summary": f"Error during summarization: {e}",
            "todos": {},
            "is_pass": "YES",
            "summarize_feedback": "",
        }


def route_after_summarize(state: TesterState) -> str:
    """Route based on IS_PASS result.

    Returns:
        - "implement_tests": NO, need to fix issues
        - "run_tests": YES, proceed to run tests
    """
    is_pass = state.get("is_pass", "YES")
    summarize_count = state.get("summarize_count", 0)
    max_summarize_retries = 2

    if is_pass == "NO" and summarize_count < max_summarize_retries:
        logger.info(f"[route_after_summarize] IS_PASS=NO -> re-implement (attempt {summarize_count + 1})")
        return "implement_tests"

    logger.info("[route_after_summarize] IS_PASS=YES -> run_tests")
    return "run_tests"
