"""Analyze error node - Pre-debug analysis."""
import logging
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from typing import Literal

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.filesystem_tools import list_directory_safe
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg
from app.agents.developer_v2.src.nodes._llm import fast_llm

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
        
        if not error_logs:
            logger.info("[analyze_error] No error logs, skipping")
            return {**state, "action": "RESPOND"}
        
        # Get existing files for context
        existing_files = ""
        try:
            result = list_directory_safe.invoke({"dir_path": "src"})
            if result and not result.startswith("Error:"):
                existing_files = result[:2000]
        except Exception:
            pass
        
        prompt = f"""Analyze this error and determine the fix strategy.

## Error Logs
```
{error_logs[:5000]}
```

## Files Modified in This Task
{', '.join(files_modified) if files_modified else 'None'}

## Existing Files
{existing_files or 'N/A'}

## Debug Attempt
This is attempt #{debug_count + 1}

Determine:
1. error_type: TEST_ERROR (test assertion), SOURCE_ERROR (source code bug), IMPORT_ERROR (wrong import/path), CONFIG_ERROR (config issue), or UNFIXABLE
2. file_to_fix: exact path to the file that needs fixing
3. root_cause: brief description (1-2 sentences)
4. fix_strategy: how to fix (1-2 sentences)
5. should_continue: true if fixable, false if should give up (e.g., requires manual intervention)
"""
        
        structured_llm = fast_llm.with_structured_output(ErrorAnalysis)
        analysis = await structured_llm.ainvoke([HumanMessage(content=prompt)], config=_cfg(state, "analyze_error"))
        
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
