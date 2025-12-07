"""Summarize node - Code summarization with IS_PASS gate."""
import logging
import re
import os
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg, flush_langfuse
from app.agents.developer_v2.src.utils.prompt_utils import (
    build_system_prompt as _build_system_prompt,
    format_input_template as _format_input_template,
)

logger = logging.getLogger(__name__)


def _read_modified_files(workspace_path: str, files_modified: list) -> dict:
    files_content = {}
    for file_path in files_modified:
        full_path = os.path.join(workspace_path, file_path) if workspace_path else file_path
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    files_content[file_path] = f.read()[:3000]
            except Exception as e:
                files_content[file_path] = f"[Error reading file: {e}]"
        else:
            files_content[file_path] = "[File not found]"
    return files_content


def _format_files_for_prompt(files_content: dict) -> str:
    parts = []
    for file_path, content in files_content.items():
        ext = file_path.split('.')[-1] if '.' in file_path else ''
        lang = 'typescript' if ext in ['ts', 'tsx'] else 'javascript' if ext in ['js', 'jsx'] else ext
        parts.append(f"### {file_path}\n```{lang}\n{content}\n```\n")
    return "\n".join(parts) if parts else "No files to review"


def _parse_summarize_response(response: str) -> dict:
    result = {"summary": "", "files_reviewed": "", "todos": {}, "is_pass": "YES", "feedback": ""}
    
    summary_match = re.search(r'## Summary\s*\n([\s\S]*?)(?=## Files|## TODOs|$)', response)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()
    
    files_match = re.search(r'## Files Reviewed\s*\n([\s\S]*?)(?=## TODOs|## IS_PASS|$)', response)
    if files_match:
        result["files_reviewed"] = files_match.group(1).strip()
    
    todos_match = re.search(r'## TODOs Found\s*\n\{([\s\S]*?)\}', response)
    if todos_match:
        todos_str = todos_match.group(1).strip()
        if todos_str:
            for line in todos_str.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip().strip('"\'')
                    value = parts[1].strip().strip('",\'')
                    if key:
                        result["todos"][key] = value
    
    is_pass_match = re.search(r'## IS_PASS:\s*(YES|NO)', response, re.IGNORECASE)
    if is_pass_match:
        result["is_pass"] = is_pass_match.group(1).upper()
    
    feedback_match = re.search(r'## Feedback[^\n]*\n([\s\S]*?)$', response)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip()
    
    return result


async def summarize(state: DeveloperState, agent=None) -> DeveloperState:
    """Summarize all implemented code and decide IS_PASS."""
    logger.info("[NODE] summarize")
    
    try:
        workspace_path = state.get("workspace_path", "")
        files_modified = state.get("files_modified", [])
        story_summary = state.get("story_summary", state.get("task_description", ""))
        
        if not files_modified:
            return {**state, "summary": "No files were modified", "todos": {}, "is_pass": "YES", "summarize_feedback": ""}
        
        files_content = _read_modified_files(workspace_path, files_modified)
        files_formatted = _format_files_for_prompt(files_content)
        
        input_text = _format_input_template(
            "summarize",
            story_summary=story_summary or "Implementation task",
            files_content=files_formatted
        )
        
        messages = [
            SystemMessage(content=_build_system_prompt("summarize")),
            HumanMessage(content=input_text)
        ]
        
        response = await code_llm.ainvoke(messages, config=_cfg(state, "summarize"))
        flush_langfuse(state)  # Real-time update
        response_text = response.content if hasattr(response, 'content') else str(response)
        result = _parse_summarize_response(response_text)
        
        logger.info(f"[summarize] IS_PASS: {result['is_pass']}, TODOs: {len(result['todos'])}")
        if result['is_pass'] == 'NO':
            logger.info(f"[summarize] Feedback: {result['feedback'][:300] if result['feedback'] else 'No feedback'}")
            logger.info(f"[summarize] Files reviewed: {result['files_reviewed'][:200] if result['files_reviewed'] else 'None'}")
            if result['todos']:
                for file_path, issue in list(result['todos'].items())[:3]:
                    logger.info(f"[summarize] TODO: {file_path}: {issue[:100]}")
        
        current_count = state.get("summarize_count", 0)
        new_count = current_count + 1 if result["is_pass"] == "NO" else 0
        
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
        
        return {
            **state,
            "summary": result["summary"],
            "todos": result["todos"],
            "is_pass": result["is_pass"],
            "summarize_feedback": result["feedback"],
            "files_reviewed": result["files_reviewed"],
            "summarize_count": new_count,
            "implementation_plan": fix_steps if fix_steps else state.get("implementation_plan", []),
            "total_steps": len(fix_steps) if fix_steps else state.get("total_steps", 0),
            "current_step": 0 if fix_steps else state.get("current_step", 0),
        }
        
    except Exception as e:
        logger.error(f"[summarize] Error: {e}")
        return {**state, "summary": f"Error: {e}", "todos": {}, "is_pass": "YES", "summarize_feedback": ""}


def route_after_summarize(state: DeveloperState) -> str:
    """Route based on IS_PASS result."""
    is_pass = state.get("is_pass", "YES")
    if is_pass == "NO" and state.get("summarize_count", 0) < 2:
        return "implement"
    return "run_code"
