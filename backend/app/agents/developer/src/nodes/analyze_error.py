"""Analyze error node - Zero-shot error analysis with preloaded context."""
import logging
import os
import re
from dataclasses import dataclass
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from app.agents.developer.src.state import DeveloperState
from app.agents.developer.src.schemas import PlanStep
from app.agents.developer.src.config import MAX_DEBUG_ATTEMPTS
from app.agents.developer.src.utils.llm_utils import get_langfuse_config as _cfg, flush_langfuse, track_node
from app.agents.developer.src.utils.prompt_utils import build_system_prompt as _build_system_prompt
from app.agents.developer.src.nodes._llm import code_llm
from app.agents.developer.src.skills import SkillRegistry

logger = logging.getLogger(__name__)


@dataclass
class ParsedError:
    file_path: str
    line: Optional[int]
    column: Optional[int]
    error_code: Optional[str]
    error_type: str
    message: str


class ErrorAnalysisOutput(BaseModel):
    """Structured output for error analysis."""
    error_type: Literal["TEST_ERROR", "SOURCE_ERROR", "IMPORT_ERROR", "CONFIG_ERROR", "UNFIXABLE"] = Field(description="Error category")
    file_to_fix: str = Field(description="Primary file to fix")
    root_cause: str = Field(description="Brief root cause explanation")
    should_continue: bool = Field(description="True if error is fixable")
    fix_steps: List[PlanStep] = Field(default_factory=list, description="Steps to fix the error")


def _parse_errors(logs: str) -> List[ParsedError]:
    """Parse error logs into structured format."""
    errors = []
    for m in re.finditer(r'([^\s(]+\.tsx?)\((\d+),(\d+)\):\s*error\s*(TS\d+):\s*(.+)', logs):
        errors.append(ParsedError(m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), "TypeScript", m.group(5).strip()))
    for m in re.finditer(r'\./([^\s:]+\.tsx?):(\d+):(\d+)\s*\n?\s*(.+?)(?:\n|$)', logs):
        errors.append(ParsedError(m.group(1), int(m.group(2)), int(m.group(3)), None, "NextJS", m.group(4).strip()))
    for m in re.finditer(r"([^\s(]+\.tsx?)\((\d+),(\d+)\):\s*error\s*(TS2322|TS2739):\s*Type '\{[^}]*\}' is not assignable to type '([^']+)'", logs):
        errors.append(ParsedError(m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), "PropsMatch", f"Props mismatch - check {m.group(5)} interface"))
    for m in re.finditer(r"(?:Cannot find module|Module not found|Can't resolve)\s*['\"]([^'\"]+)['\"]", logs):
        errors.append(ParsedError("unknown", None, None, "TS2307", "Import", f"Cannot find module '{m.group(1)}'"))
    return errors


def _format_errors(errors: List[ParsedError]) -> str:
    if not errors:
        return ""
    lines = ["## PARSED ERRORS:\n"]
    for i, e in enumerate(errors[:10], 1):
        loc = f":{e.line}:{e.column}" if e.line else ""
        code = f" [{e.error_code}]" if e.error_code else ""
        lines.append(f"{i}. **{e.file_path}{loc}**{code}: {e.message}")
    return "\n".join(lines)


def _preload_error_context(workspace_path: str, errors: List[ParsedError], files_modified: List[str]) -> str:
    """Preload files mentioned in errors and modified files."""
    parts = []
    loaded = set()
    for err in errors[:5]:
        fp = err.file_path
        if fp == "unknown" or fp in loaded:
            continue
        full = os.path.join(workspace_path, fp)
        if os.path.exists(full):
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    parts.append(f"### {fp}\n```\n{f.read()[:4000]}\n```")
                loaded.add(fp)
            except:
                pass
    for fp in files_modified[:5]:
        if fp in loaded:
            continue
        full = os.path.join(workspace_path, fp)
        if os.path.exists(full):
            try:
                with open(full, 'r', encoding='utf-8') as f:
                    parts.append(f"### {fp} (modified)\n```\n{f.read()[:3000]}\n```")
                loaded.add(fp)
            except:
                pass
    schema = os.path.join(workspace_path, "prisma/schema.prisma")
    if os.path.exists(schema) and "prisma/schema.prisma" not in loaded:
        try:
            with open(schema, 'r', encoding='utf-8') as f:
                parts.append(f"### prisma/schema.prisma\n```\n{f.read()[:2000]}\n```")
        except:
            pass
    return "\n\n".join(parts)


def _clean_logs(logs: str, max_lines: int = 50) -> str:
    if not logs:
        return ""
    noise = ["baseline-browser-mapping", "npm WARN", "pnpm install", "Compiling", "Compiled", "webpack"]
    important = ["Error:", "error:", "FAIL", "TypeError", "Cannot", "Expected", "✕", "●"]
    lines = logs.split('\n')
    filtered = [l for l in lines if not any(n in l for n in noise) and (any(i in l for i in important) or '.ts' in l)]
    return '\n'.join(filtered[:max_lines]) or logs[:2000]


@track_node("analyze_error")
async def analyze_error(state: DeveloperState, agent=None) -> DeveloperState:
    """Zero-shot error analysis with structured output."""
    from langgraph.types import interrupt
    from app.agents.developer.src.utils.signal_utils import check_interrupt_signal
    from app.agents.developer.src.utils.story_logger import StoryLogger
    
    story_logger = StoryLogger.from_state(state, agent).with_node("analyze_error")
    story_id = state.get("story_id", "")
    
    if story_id:
        signal = check_interrupt_signal(story_id, agent)
        if signal:
            await story_logger.info(f"Interrupt signal received: {signal}")
            interrupt({"reason": signal, "story_id": story_id, "node": "analyze_error"})
    
    await story_logger.task("🔍 Analyzing build errors...")
    
    try:
        error_logs = state.get("run_stderr", "") or state.get("run_stdout", "")
        workspace_path = state.get("workspace_path", "")
        files_modified = state.get("files_modified", [])
        debug_count = state.get("debug_count", 0)
        debug_history = state.get("debug_history", [])
        
        from app.agents.developer.src.utils.story_logger import analyze_error_type, try_auto_fix
        
        if workspace_path and error_logs:
            error_analysis = analyze_error_type(error_logs)
            logger.info(f"[analyze_error] Error type: {error_analysis['error_type']}, auto_fixable: {error_analysis['auto_fixable']}")
            
            if error_analysis["auto_fixable"]:
                await story_logger.task(f"⚡ Attempting auto-fix: {error_analysis['fix_strategy']}")
                auto_fixed = await try_auto_fix(error_analysis, workspace_path, story_logger)
                if auto_fixed:
                    return {**state, "action": "VALIDATE", "run_status": None, "error_analysis": {"auto_fixed": True, "fix_strategy": error_analysis["fix_strategy"]}}
        
        if debug_count >= MAX_DEBUG_ATTEMPTS:
            return {**state, "action": "RESPOND", "error": f"Max debug attempts ({MAX_DEBUG_ATTEMPTS}) reached"}
        
        if not error_logs:
            return {**state, "action": "RESPOND"}
        
        tech_stack = state.get("tech_stack", "nextjs")
        state.get("skill_registry") or SkillRegistry.load(tech_stack)
        
        parsed_errors = _parse_errors(error_logs)
        error_context = _format_errors(parsed_errors)
        file_context = _preload_error_context(workspace_path, parsed_errors, files_modified)
        cleaned_logs = _clean_logs(error_logs)
        
        await story_logger.task(f"🔎 Analyzing {len(parsed_errors)} errors...")
        
        history = ""
        if debug_history:
            history = "\n## PREVIOUS ATTEMPTS (DO NOT REPEAT!):\n" + "\n".join(f"- #{h.get('iteration')}: {h.get('fix_description', '')} -> FAILED" for h in debug_history[-3:])
        
        system_prompt = _build_system_prompt("analyze_error")
        input_text = f"""## Error Logs
{error_context}

{cleaned_logs[:3000]}

## Preloaded Files
{file_context}

## Modified Files
{', '.join(files_modified) if files_modified else 'None'}
{history}

## Debug Attempt: {debug_count + 1}/{MAX_DEBUG_ATTEMPTS}

Analyze the error and provide fix steps."""

        structured_llm = code_llm.with_structured_output(ErrorAnalysisOutput)
        result = await structured_llm.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=input_text)], 
            config=_cfg(state, "analyze_error")
        )
        flush_langfuse(state)
        
        logger.info(f"[analyze_error] Analysis: {result.error_type} - {result.root_cause[:100]}")
        
        if not result.should_continue or not result.fix_steps:
            await story_logger.message("⚠️ Lỗi không thể tự động sửa")
            return {**state, "error_analysis": {"error_type": result.error_type, "root_cause": result.root_cause}, "action": "RESPOND"}
        
        await story_logger.message(f"🔧 Đang thử sửa lỗi (lần {debug_count + 1})...")
        
        return {
            **state,
            "error_analysis": {"error_type": result.error_type, "file_to_fix": result.file_to_fix, "root_cause": result.root_cause},
            "task_type": "bug_fix",
            "complexity": "low",
            "summarize_feedback": f"Error: {result.root_cause}",
            "implementation_plan": [s.model_dump() for s in result.fix_steps],
            "total_steps": len(result.fix_steps),
            "current_step": 0,
            "action": "IMPLEMENT",
            "debug_count": debug_count + 1,
        }
    except Exception as e:
        from langgraph.errors import GraphInterrupt
        if isinstance(e, GraphInterrupt):
            raise
        await story_logger.error(f"Error analysis failed: {str(e)}", exc=e)
        return {**state, "action": "RESPOND", "error": str(e)}
