"""Analyze error node - Pre-debug analysis."""
import logging
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from typing import Literal

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, list_directory_safe
from app.agents.developer_v2.src.tools.shell_tools import semantic_code_search
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context

logger = logging.getLogger(__name__)


class ErrorAnalysis(BaseModel):
    """Error analysis result."""
    error_type: Literal["TEST_ERROR", "SOURCE_ERROR", "IMPORT_ERROR", "CONFIG_ERROR", "UNFIXABLE"] = Field(
        description="Type of error"
    )
    file_to_fix: str = Field(description="Path to file that needs fixing")
    root_cause: str = Field(description="Brief description of root cause")
    fix_strategy: str = Field(description="How to fix this error")
    should_continue: bool = Field(description="True if fixable, False if should give up")


async def analyze_error(state: DeveloperState, agent=None) -> DeveloperState:
    """Analyze error before attempting fix."""
    print("[NODE] analyze_error")
    
    try:
        error_logs = state.get("run_stderr", "")
        files_modified = state.get("files_modified", [])
        debug_count = state.get("debug_count", 0)
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        if not error_logs:
            logger.info("[analyze_error] No error logs, skipping")
            return {**state, "action": "RESPOND"}
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Get debug history to avoid repeating failed fixes
        debug_history = state.get("debug_history", [])
        history_str = "\n".join([
            f"- Attempt #{h.get('iteration', '?')}: Fixed {h.get('file', 'unknown')} - {h.get('fix_description', '')[:60]}"
            for h in debug_history[-3:]
        ]) if debug_history else "None"
        
        prompt = f"""Analyze this error and determine the fix strategy.

## Error Logs
```
{error_logs[:5000]}
```

## Files Modified in This Task
{', '.join(files_modified) if files_modified else 'None'}

## Previous Debug Attempts (avoid repeating these!)
{history_str}

## Debug Attempt
This is attempt #{debug_count + 1}

## INSTRUCTIONS
1. **Find the ACTUAL failing file**: Look for "FAIL" prefix in Jest/test output
   - "FAIL src/__tests__/X.test.ts" = this is the failing test file
   - "PASS src/__tests__/Y.test.ts" = ignore, this passed
   
2. **Use semantic_code_search** to find related files:
   - Search for imports of the failing module
   - Search for functions/types used by the failing code
   
3. **Analyze the relationship** between files

After exploration, provide your analysis with:
- error_type: TEST_ERROR, SOURCE_ERROR, IMPORT_ERROR, CONFIG_ERROR, or UNFIXABLE
- file_to_fix: exact path to the PRIMARY file that needs fixing
- root_cause: brief description (1-2 sentences)
- fix_strategy: how to fix (mention if related files need updates too)
- should_continue: true if fixable, false if should give up
"""
        
        # Tool exploration for better error analysis
        tools = [read_file_safe, list_directory_safe, semantic_code_search]
        messages = [HumanMessage(content=prompt)]
        
        exploration = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="analyze_error_explore",
            max_iterations=2
        )
        
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:3000]}\n\nNow provide your error analysis."))
        structured_llm = code_llm.with_structured_output(ErrorAnalysis)
        analysis = await structured_llm.ainvoke(messages, config=_cfg(state, "analyze_error"))
        
        logger.info(f"[analyze_error] Type: {analysis.error_type}, File: {analysis.file_to_fix}")
        logger.info(f"[analyze_error] Root cause: {analysis.root_cause}")
        logger.info(f"[analyze_error] Strategy: {analysis.fix_strategy}")
        logger.info(f"[analyze_error] Should continue: {analysis.should_continue}")
        
        return {
            **state,
            "error_analysis": analysis.model_dump(),
            "action": "DEBUG" if analysis.should_continue else "RESPOND",
        }
        
    except Exception as e:
        logger.error(f"[analyze_error] Error: {e}", exc_info=True)
        # On error, continue to debug_error anyway
        return {**state, "action": "DEBUG"}
