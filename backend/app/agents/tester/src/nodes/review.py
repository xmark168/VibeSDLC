"""Review node - LGTM/LBTM test review with parallel file processing."""
import asyncio
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
MAX_LBTM_PER_FILE = 3  # Force LGTM for file after 3 LBTM


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
    """Parse review response to extract decision and feedback."""
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


async def _review_single_file(
    state: TesterState,
    file_path: str,
    step: dict,
    step_index: int,
) -> dict:
    """Review a single test file (called in parallel).
    
    Returns:
        Dict with file_path, decision, feedback, issues
    """
    workspace_path = state.get("workspace_path", "") or state.get("project_path", "")
    scenarios = step.get("scenarios", [])
    
    # Read test file
    file_content, error = _read_test_file(workspace_path, file_path)
    
    if error:
        logger.warning(f"[review] {error}")
        return {
            "file_path": file_path,
            "decision": "LBTM",
            "feedback": error,
            "issues": [error],
            "step_index": step_index,
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
        response = await _llm.ainvoke(messages, config=_cfg(state, f"review_{step_index + 1}"))
        response_text = response.content if hasattr(response, "content") else str(response)
        
        # Parse response
        review_result = _parse_review_response(response_text)
        decision = review_result["decision"]
        feedback = review_result.get("feedback", "")
        issues = review_result.get("issues", [])
        
        logger.info(f"[review] {file_path}: {decision}")
        
        # Log LBTM reason for debugging
        if decision == "LBTM":
            logger.warning(f"[review] LBTM reason for {file_path}:")
            if feedback:
                # Log first 500 chars of feedback
                feedback_preview = feedback[:500] + "..." if len(feedback) > 500 else feedback
                logger.warning(f"[review]   Feedback: {feedback_preview}")
            if issues:
                for i, issue in enumerate(issues[:5], 1):
                    logger.warning(f"[review]   Issue {i}: {issue}")
        
        return {
            "file_path": file_path,
            "decision": decision,
            "feedback": feedback,
            "issues": issues,
            "step_index": step_index,
        }
        
    except Exception as e:
        logger.error(f"[review] Error reviewing {file_path}: {e}")
        return {
            "file_path": file_path,
            "decision": "LBTM",
            "feedback": f"Review error: {e}",
            "issues": [str(e)],
            "step_index": step_index,
        }


async def review(state: TesterState, agent=None) -> dict:
    """Review ALL test files in PARALLEL using asyncio.gather.

    This node:
    1. Gets all files_modified from implement_tests
    2. Runs all reviews in parallel
    3. Collects LGTM/LBTM for each file
    4. Returns aggregated result

    Includes interrupt signal check for pause/cancel support.

    Benefits:
    - 50% faster: All files reviewed simultaneously
    - Better feedback: Each file gets specific feedback
    """
    from langgraph.types import interrupt
    from app.agents.tester.src.graph import check_interrupt_signal
    
    # Check for pause/cancel signal
    story_id = state.get("story_id", "")
    if story_id:
        signal = check_interrupt_signal(story_id)
        if signal:
            logger.info(f"[review] Interrupt signal received: {signal}")
            interrupt({"reason": signal, "story_id": story_id, "node": "review"})
    
    files_modified = state.get("files_modified", [])
    test_plan = state.get("test_plan", [])
    total_steps = len(test_plan)
    review_count = state.get("review_count", 0)
    file_lbtm_counts = state.get("file_lbtm_counts", {})  # Track per-file LBTM
    
    print(f"[NODE] review - PARALLEL {len(files_modified)} files")
    
    if not files_modified:
        logger.info("[review] No files to review - advancing to run_tests")
        return {
            "review_result": "LGTM",
            "review_results": [],
            "failed_files": [],
            "review_feedback": "",
        }
    
    # Build file -> step mapping
    file_to_step = {}
    for i, step in enumerate(test_plan):
        step_file = step.get("file_path", "")
        if step_file:
            file_to_step[step_file] = (i, step)
    
    # Create review tasks for ALL files
    tasks = []
    for file_path in files_modified:
        # Find corresponding step (or use empty step if not found)
        step_index, step = file_to_step.get(file_path, (0, {}))
        
        task = _review_single_file(
            state=state,
            file_path=file_path,
            step=step,
            step_index=step_index,
        )
        tasks.append(task)
    
    # Run ALL reviews in PARALLEL
    logger.info(f"[review] Running {len(tasks)} reviews in parallel...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    review_results = []
    failed_files = []
    all_feedback = []
    lgtm_count = 0
    lbtm_count = 0
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"[review] Task exception: {result}")
            continue
        
        if isinstance(result, dict):
            file_path = result.get("file_path", "")
            decision = result.get("decision", "LGTM")
            
            # Track per-file LBTM and force LGTM after MAX_LBTM_PER_FILE
            if decision == "LBTM":
                file_lbtm_counts[file_path] = file_lbtm_counts.get(file_path, 0) + 1
                
                if file_lbtm_counts[file_path] >= MAX_LBTM_PER_FILE:
                    logger.warning(f"[review] Force LGTM for {file_path} after {file_lbtm_counts[file_path]} LBTM attempts")
                    result["decision"] = "LGTM"
                    result["feedback"] = f"(Force-approved after {file_lbtm_counts[file_path]} LBTM attempts)"
                    decision = "LGTM"
            
            review_results.append(result)
            
            if decision == "LGTM":
                lgtm_count += 1
            else:
                lbtm_count += 1
                failed_files.append(file_path)
                if result.get("feedback"):
                    all_feedback.append(f"{file_path}: {result['feedback']}")
    
    # Determine overall result
    # Force LGTM if max review attempts reached
    new_review_count = review_count + 1
    
    if lbtm_count > 0 and new_review_count < MAX_REVIEWS:
        overall_decision = "LBTM"
        logger.info(f"[review] {lbtm_count} LBTM files - will re-implement")
    else:
        overall_decision = "LGTM"
        if new_review_count >= MAX_REVIEWS and lbtm_count > 0:
            logger.warning(f"[review] Max reviews ({MAX_REVIEWS}) reached - forcing LGTM")
            all_feedback.append(f"(Force-approved after {new_review_count} review cycles)")
        else:
            logger.info(f"[review] All {lgtm_count} files LGTM - advancing to run_tests")
    
    combined_feedback = "\n".join(all_feedback) if all_feedback else ""
    
    return {
        "review_result": overall_decision,
        "review_results": review_results,
        "review_feedback": combined_feedback,
        "failed_files": failed_files if overall_decision == "LBTM" else [],
        "review_count": new_review_count,
        "total_lbtm_count": state.get("total_lbtm_count", 0) + lbtm_count,
        "file_lbtm_counts": file_lbtm_counts,  # Persist per-file LBTM tracking
    }
