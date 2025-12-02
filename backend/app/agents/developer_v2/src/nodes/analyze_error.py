"""Analyze error node - Error analysis + fix planning in ONE LLM call."""
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import Literal, List

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import PlanStep
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, list_directory_safe, search_files
from app.agents.developer_v2.src.tools.shell_tools import semantic_code_search
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
        
        # Use prompts from yaml
        input_text = _format_input_template(
            "analyze_error",
            error_logs=error_logs[:4000],
            files_modified=', '.join(files_modified) if files_modified else 'None',
            history_context=history_context,
            debug_count=debug_count + 1,
        )

        tools = [read_file_safe, list_directory_safe, semantic_code_search, search_files]
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
            max_iterations=2
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
        
        # Convert to ErrorAnalysisAndPlan
        result = ErrorAnalysisAndPlan(
            error_type=parsed.get("error_type", "UNFIXABLE"),
            file_to_fix=parsed.get("file_to_fix", ""),
            root_cause=parsed.get("root_cause", "Unknown error"),
            should_continue=parsed.get("should_continue", False),
            fix_steps=[PlanStep(**step) for step in parsed.get("fix_steps", [])]
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
        }
        
    except Exception as e:
        logger.error(f"[analyze_error] Error: {e}", exc_info=True)
        return {**state, "action": "RESPOND", "error": str(e)}
