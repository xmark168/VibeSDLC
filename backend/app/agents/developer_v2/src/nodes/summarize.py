"""Summarize node - MetaGPT-style code summarization with IS_PASS gate."""
import logging
import re
import os
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg

logger = logging.getLogger(__name__)

SUMMARIZE_SYSTEM_PROMPT = """You are a Senior Engineer performing final code review.
Your task is to review ALL implemented files and:
1. Summarize what was implemented
2. Detect any TODOs, incomplete code, or issues
3. Decide if implementation IS_PASS (complete) or needs more work

## Review Each File For:
- TODOs or placeholder comments
- Incomplete functions (empty bodies, pass statements)
- Missing error handling
- Type issues (any types, missing types)
- Import errors

## Output Format
```
## Summary
[Brief summary of what was implemented]

## Files Reviewed
- file1.ts: [status - OK/HAS_ISSUES] [brief description]
- file2.tsx: [status - OK/HAS_ISSUES] [brief description]

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
[What needs to be fixed in JSON format]
```
"""

SUMMARIZE_INPUT_TEMPLATE = """## Story/Task
{story_summary}

## Files Implemented
{files_content}

Review all files above and provide summary with IS_PASS decision.
"""


def _read_modified_files(workspace_path: str, files_modified: list) -> dict:
    """Read content of all modified files."""
    files_content = {}
    
    for file_path in files_modified:
        full_path = os.path.join(workspace_path, file_path) if workspace_path else file_path
        
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                files_content[file_path] = content[:3000]  # Limit per file
            except Exception as e:
                files_content[file_path] = f"[Error reading file: {e}]"
        else:
            files_content[file_path] = "[File not found]"
    
    return files_content


def _format_files_for_prompt(files_content: dict) -> str:
    """Format files content for prompt."""
    parts = []
    for file_path, content in files_content.items():
        ext = file_path.split('.')[-1] if '.' in file_path else ''
        lang = 'typescript' if ext in ['ts', 'tsx'] else 'javascript' if ext in ['js', 'jsx'] else ext
        parts.append(f"### {file_path}\n```{lang}\n{content}\n```\n")
    
    return "\n".join(parts) if parts else "No files to review"


def _parse_summarize_response(response: str) -> dict:
    """Parse summarize response."""
    result = {
        "summary": "",
        "files_reviewed": "",
        "todos": {},
        "is_pass": "YES",
        "feedback": ""
    }
    
    # Extract summary
    summary_match = re.search(r'## Summary\s*\n([\s\S]*?)(?=## Files|## TODOs|$)', response)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()
    
    # Extract files reviewed
    files_match = re.search(r'## Files Reviewed\s*\n([\s\S]*?)(?=## TODOs|## IS_PASS|$)', response)
    if files_match:
        result["files_reviewed"] = files_match.group(1).strip()
    
    # Extract TODOs (as dict-like string)
    todos_match = re.search(r'## TODOs Found\s*\n\{([\s\S]*?)\}', response)
    if todos_match:
        todos_str = todos_match.group(1).strip()
        if todos_str:
            # Parse simple key-value pairs
            for line in todos_str.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip().strip('"\'')
                    value = parts[1].strip().strip('",\'')
                    if key:
                        result["todos"][key] = value
    
    # Extract IS_PASS
    is_pass_match = re.search(r'## IS_PASS:\s*(YES|NO)', response, re.IGNORECASE)
    if is_pass_match:
        result["is_pass"] = is_pass_match.group(1).upper()
    
    # Extract feedback
    feedback_match = re.search(r'## Feedback[^\n]*\n([\s\S]*?)$', response)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip()
    
    return result


async def summarize(state: DeveloperState, agent=None) -> DeveloperState:
    """Summarize all implemented code and decide IS_PASS (MetaGPT-style).
    
    Returns:
        State with:
        - summary: Summary of implementation
        - todos: Dict of files with issues
        - is_pass: "YES" or "NO"
        - summarize_feedback: Feedback if NO
    """
    print("[NODE] summarize")
    
    try:
        workspace_path = state.get("workspace_path", "")
        files_modified = state.get("files_modified", [])
        story_summary = state.get("story_summary", state.get("task_description", ""))
        
        if not files_modified:
            logger.info("[summarize] No files modified, passing")
            return {
                **state,
                "summary": "No files were modified",
                "todos": {},
                "is_pass": "YES",
                "summarize_feedback": ""
            }
        
        # Read all modified files
        files_content = _read_modified_files(workspace_path, files_modified)
        files_formatted = _format_files_for_prompt(files_content)
        
        # Build prompt
        input_text = SUMMARIZE_INPUT_TEMPLATE.format(
            story_summary=story_summary or "Implementation task",
            files_content=files_formatted
        )
        
        messages = [
            SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT),
            HumanMessage(content=input_text)
        ]
        
        # Get summary from LLM
        response = await code_llm.ainvoke(messages, config=_cfg(state, "summarize"))
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parse response
        result = _parse_summarize_response(response_text)
        
        logger.info(f"[summarize] IS_PASS: {result['is_pass']}, TODOs: {len(result['todos'])}")
        
        if result["todos"]:
            logger.info(f"[summarize] Issues found: {list(result['todos'].keys())}")
        
        # Increment summarize_count if IS_PASS=NO, reset if YES
        current_count = state.get("summarize_count", 0)
        new_count = current_count + 1 if result["is_pass"] == "NO" else 0
        
        # Option B: When IS_PASS=NO, create fix_steps targeting specific files with issues
        fix_steps = []
        if result["is_pass"] == "NO" and result["todos"]:
            for file_path, issue in result["todos"].items():
                fix_steps.append({
                    "order": len(fix_steps) + 1,
                    "task": f"Fix issue in {file_path}: {issue}",
                    "description": f"Fix: {issue}",
                    "file_path": file_path,
                    "action": "modify",
                    "dependencies": []
                })
            logger.info(f"[summarize] Created {len(fix_steps)} fix_steps for files with issues")
        
        return {
            **state,
            "summary": result["summary"],
            "todos": result["todos"],
            "is_pass": result["is_pass"],
            "summarize_feedback": result["feedback"],
            "files_reviewed": result["files_reviewed"],
            "summarize_count": new_count,  # Track retries, reset on success
            # Option B: Replace implementation_plan with fix_steps when IS_PASS=NO
            "implementation_plan": fix_steps if fix_steps else state.get("implementation_plan", []),
            "total_steps": len(fix_steps) if fix_steps else state.get("total_steps", 0),
            "current_step": 0 if fix_steps else state.get("current_step", 0),  # Reset to start fixing
        }
        
    except Exception as e:
        logger.error(f"[summarize] Error: {e}")
        # On error, default to YES to not block
        return {
            **state,
            "summary": f"Error during summarization: {e}",
            "todos": {},
            "is_pass": "YES",
            "summarize_feedback": ""
        }


def route_after_summarize(state: DeveloperState) -> str:
    """Route based on IS_PASS result.
    
    Returns:
        - "implement": NO, need to fix issues
        - "validate": YES, proceed to run tests
    """
    is_pass = state.get("is_pass", "YES")
    summarize_count = state.get("summarize_count", 0)
    max_summarize_retries = 2
    
    if is_pass == "NO" and summarize_count < max_summarize_retries:
        logger.info(f"[route_after_summarize] IS_PASS=NO -> re-implement (attempt {summarize_count + 1})")
        return "implement"
    
    logger.info("[route_after_summarize] IS_PASS=YES -> validate")
    return "validate"
