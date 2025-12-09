"""Review node - Code review with LGTM/LBTM decision."""
import logging
import re
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes._llm import review_llm
from app.agents.developer_v2.src.schemas import SimpleReviewOutput
from app.agents.developer_v2.src.tools.filesystem_tools import get_modified_files
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg, flush_langfuse
from app.agents.developer_v2.src.utils.prompt_utils import (
    format_input_template as _format_input_template,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.utils.token_utils import (
    count_tokens,
    smart_truncate_tokens,
)

logger = logging.getLogger(__name__)

MAX_REVIEW_TOKENS = 10000


def _get_file_extension(file_path: str) -> str:
    if file_path.endswith('.ts') or file_path.endswith('.tsx'):
        return 'typescript'
    elif file_path.endswith('.js') or file_path.endswith('.jsx'):
        return 'javascript'
    elif file_path.endswith('.py'):
        return 'python'
    elif file_path.endswith('.prisma'):
        return 'prisma'
    return ''


def _smart_truncate(content: str, max_tokens: int = MAX_REVIEW_TOKENS) -> tuple[str, bool]:
    return smart_truncate_tokens(content, max_tokens, head_ratio=0.7)


async def review(state: DeveloperState, agent=None) -> DeveloperState:
    """Review implemented code with LGTM/LBTM decision."""
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    logger.info(f"[NODE] review step {current_step}/{total_steps}")
    
    try:
        plan_steps = state.get("implementation_plan", [])
        workspace_path = state.get("workspace_path", "")
        dependencies_content = state.get("dependencies_content", {})
        
        if not plan_steps or current_step >= len(plan_steps):
            return {**state, "review_result": "LGTM", "review_feedback": ""}
        
        step_index = max(current_step, 0)
        step = plan_steps[step_index]
        file_path = step.get("file_path", "")
        task_description = step.get("task", step.get("description", ""))
        
        if not file_path:
            return {**state, "review_result": "LGTM", "review_feedback": ""}
        
        import os
        full_path = os.path.join(workspace_path, file_path) if workspace_path else file_path
        
        if not os.path.exists(full_path):
            return {**state, "review_result": "LBTM", "review_feedback": f"File {file_path} was not created"}
        
        with open(full_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        file_content_review, is_truncated = _smart_truncate(file_content)
        truncation_note = " (truncated)" if is_truncated else ""
        
        # Read fresh dependencies from disk (fix stale cache issue)
        deps_context = ""
        for dep in step.get("dependencies", [])[:5]:
            dep_content = None
            # Try fresh read from disk first
            if workspace_path:
                dep_path = os.path.join(workspace_path, dep)
                if os.path.exists(dep_path):
                    try:
                        with open(dep_path, 'r', encoding='utf-8') as f:
                            dep_content = f.read()
                    except Exception:
                        pass
            # Fallback to cache
            if not dep_content and dep in dependencies_content:
                dep_content = dependencies_content[dep]
            if dep_content:
                deps_context += f"### {dep}\n```\n{dep_content[:3000]}\n```\n\n"
        deps_context = deps_context or "No dependencies"
        
        system_prompt = _build_system_prompt("review")
        input_text = _format_input_template(
            "review",
            task_description=task_description,
            file_path=file_path + truncation_note,
            file_ext=_get_file_extension(file_path),
            file_content=file_content_review,
            dependencies_context=deps_context
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ]
        
        structured_llm = review_llm.with_structured_output(SimpleReviewOutput)
        result = await structured_llm.ainvoke(messages, config=_cfg(state, "review"))
        flush_langfuse(state)
        review_result = result.model_dump()
        
        logger.info(f"[review] {file_path}: {review_result['decision']}")
        if review_result['decision'] == "LBTM":
            logger.info(f"[review] LBTM reason: {review_result['feedback'][:500] if review_result['feedback'] else 'No feedback'}")
        
        # Track LBTM count PER STEP (not global)
        step_lbtm_counts = state.get("step_lbtm_counts", {})
        step_key = str(step_index)
        
        current_step = state.get("current_step", 0)
        total_lbtm = state.get("total_lbtm_count", 0)
        
        if review_result["decision"] == "LBTM":
            step_lbtm_counts[step_key] = step_lbtm_counts.get(step_key, 0) + 1
            total_lbtm += 1
            
            # Adaptive LBTM limit based on complexity
            complexity = state.get("complexity", "medium")
            max_lbtm = {"low": 1, "medium": 2, "high": 3}.get(complexity, 2)
            logger.info(f"[review] Step {step_index} LBTM count: {step_lbtm_counts[step_key]}/{max_lbtm} (complexity={complexity})")
            
            # If this step has reached max LBTM for its complexity, force move to next step
            if step_lbtm_counts[step_key] >= max_lbtm:
                logger.warning(f"[review] Step {step_index} reached max LBTM ({step_lbtm_counts[step_key]}/{max_lbtm}), forcing LGTM")
                review_result["decision"] = "LGTM"
                review_result["feedback"] = f"(Force-approved after {step_lbtm_counts[step_key]} attempts)"
                current_step += 1
        else:
            logger.info(f"[review] Step {step_index} LGTM, moving to step {current_step + 1}")
            current_step += 1
        
        return {
            **state,
            "current_step": current_step,
            "review_result": review_result["decision"],
            "review_feedback": review_result.get("feedback", ""),
            "review_count": state.get("review_count", 0) + (1 if review_result["decision"] == "LBTM" else 0),
            "total_lbtm_count": total_lbtm,
            "step_lbtm_counts": step_lbtm_counts,
        }
        
    except Exception as e:
        logger.error(f"[review] Error: {e}")
        return {**state, "review_result": "LGTM", "review_feedback": "", "error": str(e)}


def route_after_review(state: DeveloperState) -> str:
    """Route based on review result."""
    review_result = state.get("review_result", "LGTM")
    
    # If LBTM, go back to implement (per-step limit enforced in review node)
    if review_result == "LBTM":
        return "implement"
    
    # LGTM - check if more steps
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if current_step >= total_steps:
        return "summarize"
    return "implement"  # Changed from "next_step" to "implement"
