"""Analyze error node - Error analysis + fix planning in ONE LLM call."""
import logging
import re
from dataclasses import dataclass
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import Literal, List, Optional

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import PlanStep
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, list_directory_safe, glob
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.utils.prompt_utils import (
    format_input_template as _format_input_template,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.utils.json_utils import extract_json_universal
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context
from app.agents.developer_v2.src.skills import SkillRegistry

logger = logging.getLogger(__name__)


def _clean_error_logs(logs: str, max_lines: int = 50) -> str:
    """Clean error logs by removing noise and keeping relevant lines."""
    if not logs:
        return ""
    
    # Noise patterns to filter out
    noise_patterns = [
        "baseline-browser-mapping",
        "npm WARN",
        "bun install",
        "modules old",
        "update:",
        "Compiling",
        "Compiled",
        "webpack",
        "Module not found",  # Keep only if it's the actual error
    ]
    
    # Important patterns to keep
    important_patterns = [
        "Error:",
        "error:",
        "FAIL",
        "fail",
        "TypeError",
        "ReferenceError",
        "SyntaxError",
        "Cannot",
        "cannot",
        "Expected",
        "expected",
        "Received",
        "received",
        "at Object",
        "at Module",
        ".test.ts",
        ".test.tsx",
        "✕",
        "●",
    ]
    
    lines = logs.split('\n')
    filtered = []
    
    for line in lines:
        # Skip noise
        if any(noise in line for noise in noise_patterns):
            continue
        # Keep important lines
        if any(important in line for important in important_patterns):
            filtered.append(line)
        # Keep lines with file paths
        elif '.ts' in line or '.tsx' in line or '.js' in line:
            filtered.append(line)
    
    # Limit lines
    result = '\n'.join(filtered[:max_lines])
    return result if result else logs[:2000]  # Fallback to truncated original


# =============================================================================
# STRUCTURED ERROR PARSING (MetaGPT-style)
# =============================================================================

@dataclass
class ParsedError:
    """Structured error from logs."""
    file_path: str
    line: Optional[int]
    column: Optional[int]
    error_code: Optional[str]
    error_type: str
    message: str
    raw_line: str


def _parse_error_structured(logs: str) -> List[ParsedError]:
    """Parse error logs into structured format."""
    errors = []
    
    # TypeScript error format: src/file.tsx(line,col): error TS2307: message
    ts_pattern = r'([^\s(]+\.tsx?)\((\d+),(\d+)\):\s*error\s*(TS\d+):\s*(.+)'
    for match in re.finditer(ts_pattern, logs):
        errors.append(ParsedError(
            file_path=match.group(1),
            line=int(match.group(2)),
            column=int(match.group(3)),
            error_code=match.group(4),
            error_type="TypeScript",
            message=match.group(5).strip(),
            raw_line=match.group(0)
        ))
    
    # Next.js build error: ./src/file.tsx:line:col
    nextjs_pattern = r'\./([^\s:]+\.tsx?):(\d+):(\d+)\s*\n?\s*(.+?)(?:\n|$)'
    for match in re.finditer(nextjs_pattern, logs):
        errors.append(ParsedError(
            file_path=match.group(1),
            line=int(match.group(2)),
            column=int(match.group(3)),
            error_code=None,
            error_type="NextJS",
            message=match.group(4).strip(),
            raw_line=match.group(0)
        ))
    
    # Prisma error: Error code: P1001
    prisma_pattern = r'Error code:\s*(P\d+)[^\n]*\n?(.+?)(?:\n\n|$)'
    for match in re.finditer(prisma_pattern, logs, re.DOTALL):
        errors.append(ParsedError(
            file_path="prisma/schema.prisma",
            line=None,
            column=None,
            error_code=match.group(1),
            error_type="Prisma",
            message=match.group(2).strip()[:200],
            raw_line=match.group(0)
        ))
    
    # Jest test error: FAIL src/file.test.tsx
    jest_pattern = r'FAIL\s+([^\s]+\.test\.tsx?)'
    for match in re.finditer(jest_pattern, logs):
        errors.append(ParsedError(
            file_path=match.group(1),
            line=None,
            column=None,
            error_code=None,
            error_type="Jest",
            message="Test failed",
            raw_line=match.group(0)
        ))
    
    # Module not found: Can't resolve 'package'
    module_pattern = r"(?:Cannot find module|Module not found|Can't resolve)\s*['\"]([^'\"]+)['\"]"
    for match in re.finditer(module_pattern, logs):
        module_name = match.group(1)
        errors.append(ParsedError(
            file_path="unknown",
            line=None,
            column=None,
            error_code="TS2307",
            error_type="Import",
            message=f"Cannot find module '{module_name}'",
            raw_line=match.group(0)
        ))
    
    return errors


def _format_parsed_errors(errors: List[ParsedError]) -> str:
    """Format parsed errors for LLM context."""
    if not errors:
        return ""
    
    lines = ["## PARSED ERRORS (fix these files!):\n"]
    for i, err in enumerate(errors[:5], 1):
        loc = f":{err.line}" if err.line else ""
        code = f" [{err.error_code}]" if err.error_code else ""
        lines.append(f"{i}. **{err.file_path}{loc}**{code}: {err.message}")
    
    return "\n".join(lines)


class ErrorAnalysisAndPlan(BaseModel):
    """Combined error analysis and fix plan."""
    error_type: Literal["TEST_ERROR", "SOURCE_ERROR", "IMPORT_ERROR", "CONFIG_ERROR", "UNFIXABLE"] = Field(
        description="Type of error"
    )
    file_to_fix: str = Field(description="Primary file that needs fixing")
    root_cause: str = Field(description="Root cause (1-2 sentences)")
    should_continue: bool = Field(description="True if fixable")
    fix_steps: List[PlanStep] = Field(
        default_factory=list,
        description="Fix steps: order, description, file_path, action (create/modify)"
    )


async def analyze_error(state: DeveloperState, agent=None) -> DeveloperState:
    """Analyze error and create fix plan in ONE LLM call."""
    print("[NODE] analyze_error")
    
    try:
        error_logs = state.get("run_stderr", "")
        files_modified = state.get("files_modified", [])
        debug_count = state.get("debug_count", 0)
        debug_history = state.get("debug_history", [])
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        if not error_logs:
            logger.info("[analyze_error] No error logs")
            return {**state, "action": "RESPOND"}
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Load skill registry
        tech_stack = state.get("tech_stack", "nextjs")
        skill_registry = state.get("skill_registry")
        if not skill_registry:
            skill_registry = SkillRegistry.load(tech_stack)
        
        # Build history context
        history_context = ""
        if debug_history:
            history_context = "\n## PREVIOUS ATTEMPTS (DO NOT REPEAT!)\n"
            for h in debug_history[-3:]:
                history_context += f"- #{h.get('iteration')}: {h.get('fix_description', '')[:80]} -> FAILED\n"
        
        # ==============================================
        # STRUCTURED ERROR PARSING (MetaGPT-style)
        # ==============================================
        parsed_errors = _parse_error_structured(error_logs)
        parsed_context = _format_parsed_errors(parsed_errors)
        
        if parsed_errors:
            logger.info(f"[analyze_error] Parsed {len(parsed_errors)} structured errors:")
            for err in parsed_errors[:3]:
                logger.info(f"[analyze_error]   - {err.file_path}: {err.error_code or err.error_type} - {err.message[:60]}")
        
        # Clean error logs to remove noise
        cleaned_logs = _clean_error_logs(error_logs)
        
        # Inject parsed errors at the top of the prompt
        error_context = parsed_context + "\n\n" if parsed_context else ""
        
        # Use prompts from yaml
        input_text = _format_input_template(
            "analyze_error",
            error_logs=error_context + cleaned_logs,
            files_modified=', '.join(files_modified) if files_modified else 'None',
            history_context=history_context,
            debug_count=debug_count + 1,
        )

        tools = [read_file_safe, list_directory_safe, glob]
        messages = [
            SystemMessage(content=_build_system_prompt("analyze_error")),
            HumanMessage(content=input_text)
        ]
        
        # Tool exploration
        exploration = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="analyze_error",
            max_iterations=4  # Increased from 2 - need more iterations to understand errors
        )
        
        # Request JSON response with result tags
        json_instruction = """
Based on your analysis, respond ONLY with JSON wrapped in <result> tags:

<result>
{
  "error_type": "TEST_ERROR|SOURCE_ERROR|IMPORT_ERROR|CONFIG_ERROR|UNFIXABLE",
  "file_to_fix": "path/to/file.ts",
  "root_cause": "Brief explanation of root cause",
  "should_continue": true,
  "fix_steps": [
    {"order": 1, "description": "Fix description", "file_path": "path/to/file.ts", "action": "modify"}
  ]
}
</result>

CRITICAL: Respond ONLY with the JSON in <result> tags. No other text.
"""
        messages.append(HumanMessage(content=f"Context:\n{exploration[:3000]}\n\n{json_instruction}"))
        
        # Invoke LLM and extract JSON
        response = await code_llm.ainvoke(messages, config=_cfg(state, "analyze_error"))
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parse JSON from response
        parsed = extract_json_universal(response_text, "analyze_error")
        
        # Validate and filter fix_steps
        valid_actions = {'create', 'modify', 'delete', 'test', 'config', 'review'}
        valid_steps = []
        for step in parsed.get("fix_steps", []):
            action = step.get("action", "modify")
            # Fix invalid action values
            if action not in valid_actions:
                action = "modify"  # Default to modify
            step["action"] = action
            try:
                valid_steps.append(PlanStep(**step))
            except Exception as e:
                logger.warning(f"[analyze_error] Skipping invalid step: {e}")
        
        # Convert to ErrorAnalysisAndPlan
        result = ErrorAnalysisAndPlan(
            error_type=parsed.get("error_type", "UNFIXABLE"),
            file_to_fix=parsed.get("file_to_fix", ""),
            root_cause=parsed.get("root_cause", "Unknown error"),
            should_continue=parsed.get("should_continue", False),
            fix_steps=valid_steps
        )
        
        logger.info(f"[analyze_error] {result.error_type}: {result.root_cause}")
        
        if not result.should_continue or not result.fix_steps:
            return {
                **state,
                "error_analysis": {"error_type": result.error_type, "root_cause": result.root_cause},
                "action": "RESPOND",
            }
        
        logger.info(f"[analyze_error] {len(result.fix_steps)} fix steps")
        
        steps_text = "\n".join(f"  {s.order}. [{s.action}] {s.description}" for s in result.fix_steps)
        msg = f"""🔧 **Bug Fix** (Attempt #{debug_count + 1})

**Error:** {result.error_type}
**Cause:** {result.root_cause[:100]}

{steps_text}
"""
        
        return {
            **state,
            "error_analysis": {
                "error_type": result.error_type,
                "file_to_fix": result.file_to_fix,
                "root_cause": result.root_cause,
            },
            "task_type": "bug_fix",
            "complexity": "low",
            "affected_files": [result.file_to_fix],
            "summarize_feedback": f"Error: {result.root_cause}",
            "implementation_plan": [s.model_dump() for s in result.fix_steps],
            "total_steps": len(result.fix_steps),
            "current_step": 0,
            "message": msg,
            "action": "IMPLEMENT",
            "skill_registry": skill_registry,
            "tech_stack": tech_stack,
            "debug_count": debug_count + 1,
        }
        
    except Exception as e:
        logger.error(f"[analyze_error] Error: {e}", exc_info=True)
        return {**state, "action": "RESPOND", "error": str(e)}
