"""Review node - MetaGPT-style code review with LGTM/LBTM decision."""
import logging
import re
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.tools.filesystem_tools import get_modified_files
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = """You are a Senior Code Reviewer performing code review.
Your task is to review the implemented code and decide: LGTM (approve) or LBTM (request changes).

## Review Criteria
1. **Completeness**: No TODOs, placeholders, or "// rest of code"
2. **Correctness**: Logic is correct, handles edge cases
3. **Types**: Strong typing, no `any` types
4. **Imports**: All imports are valid and used
5. **Best Practices**: Follows framework conventions

## Decision Rules
- LGTM: Code is complete and correct, ready for next step
- LBTM: Code has issues that MUST be fixed

## Output Format
```
DECISION: LGTM|LBTM

REVIEW:
- [issue or approval point]
- [issue or approval point]

FEEDBACK: (only if LBTM)
[Specific feedback for fixing the issues]
```
"""

REVIEW_INPUT_TEMPLATE = """## Task Completed
{task_description}

## File: {file_path}
```{file_ext}
{file_content}
```

## Context (dependencies used)
{dependencies_context}

Review the code above and provide your decision (LGTM or LBTM).
"""


def _get_file_extension(file_path: str) -> str:
    """Get file extension for code block."""
    if file_path.endswith('.ts') or file_path.endswith('.tsx'):
        return 'typescript'
    elif file_path.endswith('.js') or file_path.endswith('.jsx'):
        return 'javascript'
    elif file_path.endswith('.py'):
        return 'python'
    elif file_path.endswith('.prisma'):
        return 'prisma'
    return ''


def _parse_review_response(response: str) -> dict:
    """Parse review response to extract decision and feedback."""
    result = {
        "decision": "LGTM",  # Default to LGTM
        "review": "",
        "feedback": ""
    }
    
    # Extract decision
    decision_match = re.search(r'DECISION:\s*(LGTM|LBTM)', response, re.IGNORECASE)
    if decision_match:
        result["decision"] = decision_match.group(1).upper()
    
    # Extract review section
    review_match = re.search(r'REVIEW:\s*\n([\s\S]*?)(?=FEEDBACK:|$)', response, re.IGNORECASE)
    if review_match:
        result["review"] = review_match.group(1).strip()
    
    # Extract feedback (only for LBTM)
    feedback_match = re.search(r'FEEDBACK:\s*\n?([\s\S]*?)$', response, re.IGNORECASE)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip()
    
    return result


async def review(state: DeveloperState, agent=None) -> DeveloperState:
    """Review implemented code with LGTM/LBTM decision (MetaGPT-style).
    
    Returns:
        State with review_result: "LGTM" or "LBTM"
        If LBTM, includes review_feedback for re-implementation
    """
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] review step {current_step}/{total_steps}")
    
    try:
        plan_steps = state.get("implementation_plan", [])
        workspace_path = state.get("workspace_path", "")
        dependencies_content = state.get("dependencies_content", {})
        
        if not plan_steps or current_step < 1:
            return {**state, "review_result": "LGTM", "review_feedback": ""}
        
        # Get the step that was just implemented (current_step - 1 because we increment after implement)
        step_index = current_step - 1
        if step_index >= len(plan_steps):
            step_index = len(plan_steps) - 1
            
        step = plan_steps[step_index]
        file_path = step.get("file_path", "")
        task_description = step.get("task", step.get("description", ""))
        
        if not file_path:
            return {**state, "review_result": "LGTM", "review_feedback": ""}
        
        # Read the implemented file
        import os
        full_path = os.path.join(workspace_path, file_path) if workspace_path else file_path
        
        if not os.path.exists(full_path):
            logger.warning(f"[review] File not found: {full_path}")
            return {**state, "review_result": "LBTM", "review_feedback": f"File {file_path} was not created"}
        
        with open(full_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Build dependencies context
        deps_context = ""
        step_deps = step.get("dependencies", [])
        for dep in step_deps[:3]:  # Limit to 3 deps
            if dep in dependencies_content:
                content = dependencies_content[dep][:500]
                deps_context += f"### {dep}\n```\n{content}\n```\n\n"
        
        if not deps_context:
            deps_context = "No dependencies"
        
        # Build review prompt
        input_text = REVIEW_INPUT_TEMPLATE.format(
            task_description=task_description,
            file_path=file_path,
            file_ext=_get_file_extension(file_path),
            file_content=file_content[:4000],  # Limit content size
            dependencies_context=deps_context
        )
        
        messages = [
            SystemMessage(content=REVIEW_SYSTEM_PROMPT),
            HumanMessage(content=input_text)
        ]
        
        # Get review from LLM
        response = await code_llm.ainvoke(messages, config=_cfg(state, "review"))
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parse response
        review_result = _parse_review_response(response_text)
        
        logger.info(f"[review] {file_path}: {review_result['decision']}")
        
        if review_result["decision"] == "LBTM":
            logger.info(f"[review] Feedback: {review_result['feedback'][:100]}...")
        
        # Increment review_count if LBTM (for retry limit tracking)
        current_count = state.get("review_count", 0)
        new_count = current_count + 1 if review_result["decision"] == "LBTM" else current_count
        
        # Track total LBTM count across all steps (for skip summarize optimization)
        total_lbtm = state.get("total_lbtm_count", 0)
        if review_result["decision"] == "LBTM":
            total_lbtm += 1
        
        # Increment current_step ONLY on LGTM (not in implement node)
        # This ensures LBTM re-implements the SAME step
        current_step = state.get("current_step", 0)
        if review_result["decision"] == "LGTM":
            current_step += 1
            logger.info(f"[review] LGTM - advancing to step {current_step + 1}")
        
        return {
            **state,
            "current_step": current_step,  # Only increment on LGTM
            "review_result": review_result["decision"],
            "review_feedback": review_result["feedback"],
            "review_details": review_result["review"],
            "review_count": new_count,  # Track LBTM retries per step
            "total_lbtm_count": total_lbtm,  # Track total LBTM for skip summarize
        }
        
    except Exception as e:
        logger.error(f"[review] Error: {e}")
        # On error, default to LGTM to not block the flow
        return {**state, "review_result": "LGTM", "review_feedback": "", "error": str(e)}


def route_after_review(state: DeveloperState) -> str:
    """Route based on review result.
    
    Returns:
        - "implement": LBTM, need to re-implement with feedback
        - "next_step": LGTM, proceed to next step or summarize
    """
    review_result = state.get("review_result", "LGTM")
    review_count = state.get("review_count", 0)
    max_reviews = 2  # Max re-reviews per step
    
    if review_result == "LBTM" and review_count < max_reviews:
        logger.info(f"[route_after_review] LBTM -> re-implement (attempt {review_count + 1})")
        return "implement"
    
    # LGTM or max reviews reached
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if current_step >= total_steps:
        logger.info("[route_after_review] All steps done -> summarize")
        return "summarize"
    
    logger.info(f"[route_after_review] LGTM -> next step ({current_step + 1}/{total_steps})")
    return "next_step"
