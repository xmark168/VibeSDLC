"""Review node - LGTM/LBTM test review (Developer V2 pattern).

Uses prompts from prompts.yaml for consistency.
No duplicate routing function - routing is in graph.py only.
"""
import json
import logging
import os
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.utils.token_utils import smart_truncate_tokens
from app.agents.tester.src._llm import review_llm

logger = logging.getLogger(__name__)

_llm = review_llm

# Config
MAX_REVIEW_TOKENS = 8000
MAX_LBTM_PER_STEP = 3  # Force advance after 3 LBTM per step
MAX_REVIEWS = 2  # Max reviews before force advancing


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {"run_name": name}


def _get_file_extension(file_path: str) -> str:
    """Get file extension for code block."""
    ext_map = {
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript",
        ".py": "python",
    }
    for ext, lang in ext_map.items():
        if file_path.endswith(ext):
            return lang
    return ""


def _parse_review_response(response: str) -> dict:
    """Parse review response to extract decision and feedback.
    
    Handles multiple formats:
    - DECISION: LGTM/LBTM
    - JSON format {"decision": "LGTM", ...}
    """
    result = {"decision": "LGTM", "review": "", "feedback": "", "issues": []}

    # Try JSON format first
    try:
        # Find JSON in response
        json_match = re.search(r'\{[^{}]*"decision"[^{}]*\}', response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            result["decision"] = parsed.get("decision", "LGTM").upper()
            result["feedback"] = parsed.get("feedback", "")
            result["issues"] = parsed.get("issues", [])
            return result
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback to text parsing
    # Find ALL decisions and take the LAST one (LLM sometimes reconsiders)
    decisions = re.findall(r"DECISION:\s*(LGTM|LBTM)", response, re.IGNORECASE)
    if decisions:
        result["decision"] = decisions[-1].upper()

    # Extract review section
    review_match = re.search(
        r"REVIEW:\s*\n([\s\S]*?)(?=FEEDBACK:|$)", response, re.IGNORECASE
    )
    if review_match:
        result["review"] = review_match.group(1).strip()

    # Extract feedback (for LBTM)
    feedback_match = re.search(r"FEEDBACK:\s*\n?([\s\S]*?)$", response, re.IGNORECASE)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip()

    return result


def _read_test_file(workspace_path: str, file_path: str) -> tuple[str, str]:
    """Read test file content with error handling.
    
    Returns:
        (content, error_message) - content is empty if error
    """
    full_path = Path(workspace_path) / file_path if workspace_path else Path(file_path)
    
    if full_path.is_dir():
        return "", f"Path is a directory, not a file: {file_path}"
    
    if not full_path.exists():
        return "", f"Test file not found: {file_path}"
    
    try:
        content = full_path.read_text(encoding="utf-8")
        return content, ""
    except Exception as e:
        return "", f"Error reading file: {e}"


def _get_source_context(state: dict, step: dict) -> str:
    """Get relevant source code context for review."""
    dependencies_content = state.get("dependencies_content", {})
    step_deps = step.get("dependencies", [])
    
    if not dependencies_content:
        return "N/A"
    
    parts = []
    for dep_path in step_deps:
        if dep_path in dependencies_content:
            content = dependencies_content[dep_path]
            # Truncate long files
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"
            parts.append(f"### {dep_path}\n```typescript\n{content}\n```")
    
    return "\n\n".join(parts) if parts else "N/A"


async def review(state: TesterState, agent=None) -> dict:
    """Review implemented test with LGTM/LBTM decision.

    Uses prompts from prompts.yaml for consistency.
    Tracks per-step LBTM counts to avoid infinite loops.

    Returns:
        - review_result: "LGTM" or "LBTM"
        - review_feedback: Feedback for re-implementation (if LBTM)
        - current_step: Incremented on LGTM
    """
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] review - step {current_step + 1}/{total_steps}")

    test_plan = state.get("test_plan", [])
    workspace_path = state.get("workspace_path", "") or state.get("project_path", "")
    review_count = state.get("review_count", 0)

    # Early exit conditions
    if not test_plan or current_step < 0 or current_step >= len(test_plan):
        logger.info("[review] No valid step to review - advancing")
        return {
            "current_step": current_step + 1,
            "review_result": "LGTM",
            "review_feedback": "",
            "review_count": 0,
        }

    # Get current step info
    step = test_plan[current_step]
    file_path = step.get("file_path", "")
    task_description = step.get("description", "")
    scenarios = step.get("scenarios", [])

    if not file_path:
        logger.info("[review] No file path - advancing")
        return {
            "current_step": current_step + 1,
            "review_result": "LGTM",
            "review_feedback": "",
            "review_count": 0,
        }

    # Read test file
    file_content, error = _read_test_file(workspace_path, file_path)
    
    if error:
        logger.warning(f"[review] {error}")
        new_count = review_count + 1
        
        # Force advance if max reviews reached
        if new_count >= MAX_REVIEWS:
            logger.info(f"[review] Max reviews ({MAX_REVIEWS}) reached - force advancing")
            return {
                "current_step": current_step + 1,
                "review_result": "LBTM",
                "review_feedback": error,
                "review_count": MAX_REVIEWS,
                "total_lbtm_count": state.get("total_lbtm_count", 0) + 1,
            }
        
        return {
            "current_step": current_step,
            "review_result": "LBTM",
            "review_feedback": error,
            "review_count": new_count,
        }

    try:
        # Smart truncate file content
        file_content_review, was_truncated = smart_truncate_tokens(file_content, MAX_REVIEW_TOKENS)
        truncation_note = " (truncated - showing head + tail)" if was_truncated else ""

        # Format data for prompt
        scenarios_str = "\n".join(f"- {s}" for s in scenarios) if scenarios else "N/A"
        source_context = _get_source_context(state, step)

        # Get prompts from YAML
        system_prompt = get_system_prompt("review")
        user_prompt = get_user_prompt(
            "review",
            file_path=file_path + truncation_note,
            test_content=file_content_review,
            source_code=source_context,
            scenarios=scenarios_str,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Call LLM
        response = await _llm.ainvoke(messages, config=_cfg(state, f"review_step_{current_step + 1}"))
        response_text = response.content if hasattr(response, "content") else str(response)

        # Parse response
        review_result = _parse_review_response(response_text)
        decision = review_result["decision"]

        logger.info(f"[review] {file_path}: {decision}")
        if decision == "LBTM":
            logger.info(f"[review] Feedback: {review_result['feedback'][:100]}...")

        # Track LBTM per step
        step_lbtm_counts = state.get("step_lbtm_counts", {})
        step_key = str(current_step)
        total_lbtm = state.get("total_lbtm_count", 0)
        new_current_step = current_step

        if decision == "LBTM":
            step_lbtm_counts[step_key] = step_lbtm_counts.get(step_key, 0) + 1
            total_lbtm += 1
            
            # Force LGTM if too many attempts
            if step_lbtm_counts[step_key] >= MAX_LBTM_PER_STEP:
                logger.warning(f"[review] Step {current_step} has {step_lbtm_counts[step_key]} LBTM - forcing LGTM")
                decision = "LGTM"
                review_result["feedback"] = f"(Force-approved after {step_lbtm_counts[step_key]} attempts)"
                new_current_step += 1
        else:
            # LGTM - advance
            new_current_step += 1
            logger.info(f"[review] LGTM - advancing to step {new_current_step + 1}")

        return {
            "current_step": new_current_step,
            "review_result": decision,
            "review_feedback": review_result["feedback"],
            "review_details": review_result["review"],
            "review_count": step_lbtm_counts.get(step_key, 0),
            "total_lbtm_count": total_lbtm,
            "step_lbtm_counts": step_lbtm_counts,
        }

    except Exception as e:
        logger.error(f"[review] Error: {e}", exc_info=True)
        new_count = review_count + 1
        
        if new_count >= MAX_REVIEWS:
            logger.info(f"[review] Max reviews reached after error - force advancing")
            return {
                "current_step": current_step + 1,
                "review_result": "LGTM",
                "review_feedback": f"Force approved after error: {e}",
                "review_count": MAX_REVIEWS,
                "error": str(e),
            }
        
        return {
            "current_step": current_step,
            "review_result": "LBTM",
            "review_feedback": f"Review failed: {e}",
            "review_count": new_count,
            "error": str(e),
        }
