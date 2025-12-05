"""Review node - MetaGPT-style test review with LGTM/LBTM decision."""
import logging
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.tester.src.state import TesterState

logger = logging.getLogger(__name__)

# LLM setup
_api_key = os.getenv("TESTER_API_KEY") or os.getenv("OPENAI_API_KEY")
_base_url = os.getenv("TESTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
_model = os.getenv("TESTER_MODEL", "gpt-4.1")

_llm = (
    ChatOpenAI(model=_model, temperature=0, api_key=_api_key, base_url=_base_url)
    if _base_url
    else ChatOpenAI(model=_model, temperature=0)
)


REVIEW_SYSTEM_PROMPT = """You are a Senior QA Engineer performing test code review.
Your task is to review the implemented test and decide: LGTM (approve) or LBTM (request changes).

## Review Criteria (Priority Order)
1. **Runnable**: Test file is syntactically correct and can run
2. **Core Scenarios**: Main happy path and 1-2 error cases are covered
3. **Assertions**: Each test has at least one meaningful assertion
4. **Mocking**: External dependencies are mocked (if needed)

## LGTM Conditions (approve if ANY is true)
- Test covers main happy path + at least 1 error case
- Test has 3+ test cases with proper assertions
- Test follows project conventions and is runnable

## LBTM Conditions (reject ONLY if)
- Test file has syntax errors or won't run
- Test has NO assertions (empty expects)
- Test is completely missing required mocks
- Test file is incomplete (has TODO/placeholder comments)

## IMPORTANT
- Do NOT reject for missing edge cases - those can be added later
- Do NOT reject for missing 1-2 scenarios from plan - main flow is enough
- Prefer LGTM over LBTM when test is functional

## Output Format
```
DECISION: LGTM|LBTM

REVIEW:
- [issue or approval point]

FEEDBACK: (only if LBTM - be specific)
[What MUST be fixed to pass]
```
"""

REVIEW_INPUT_TEMPLATE = """## Test Task
{task_description}

## Scenarios to Cover
{scenarios}

## Test File: {file_path}
```{file_ext}
{file_content}
```

## Testing Context
{testing_context}

Review the test code above and provide your decision (LGTM or LBTM).
"""


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {"run_name": name}


def _get_file_extension(file_path: str) -> str:
    """Get file extension for code block."""
    if file_path.endswith(".ts") or file_path.endswith(".tsx"):
        return "typescript"
    elif file_path.endswith(".js") or file_path.endswith(".jsx"):
        return "javascript"
    elif file_path.endswith(".py"):
        return "python"
    return ""


def _parse_review_response(response: str) -> dict:
    """Parse review response to extract decision and feedback."""
    result = {"decision": "LGTM", "review": "", "feedback": ""}

    # Extract decision
    decision_match = re.search(r"DECISION:\s*(LGTM|LBTM)", response, re.IGNORECASE)
    if decision_match:
        result["decision"] = decision_match.group(1).upper()

    # Extract review section
    review_match = re.search(
        r"REVIEW:\s*\n([\s\S]*?)(?=FEEDBACK:|$)", response, re.IGNORECASE
    )
    if review_match:
        result["review"] = review_match.group(1).strip()

    # Extract feedback (only for LBTM)
    feedback_match = re.search(r"FEEDBACK:\s*\n?([\s\S]*?)$", response, re.IGNORECASE)
    if feedback_match:
        result["feedback"] = feedback_match.group(1).strip()

    return result


async def review(state: TesterState, agent=None) -> dict:
    """Review implemented test with LGTM/LBTM decision (MetaGPT-style).

    Returns:
        State with review_result: "LGTM" or "LBTM"
        If LBTM, includes review_feedback for re-implementation
    """
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] review step {current_step}/{total_steps}")

    try:
        test_plan = state.get("test_plan", [])
        workspace_path = state.get("workspace_path", "") or state.get("project_path", "")
        testing_context = state.get("testing_context", {})

        if not test_plan or current_step < 0:
            # No plan or invalid step - skip review, advance to next step
            return {
                "current_step": current_step + 1,
                "review_result": "LGTM",
                "review_feedback": "",
            }

        # Get the step that was just implemented
        # implement_tests uses current_step as 0-indexed step
        # So we review the same current_step (not current_step - 1)
        step_index = current_step
        if step_index < 0:
            step_index = 0
        if step_index >= len(test_plan):
            step_index = len(test_plan) - 1

        step = test_plan[step_index]
        file_path = step.get("file_path", "")
        task_description = step.get("description", "")
        scenarios = step.get("scenarios", [])

        if not file_path:
            # No file path specified - skip review, advance to next step
            return {
                "current_step": current_step + 1,
                "review_result": "LGTM",
                "review_feedback": "",
            }

        # Read the implemented test file
        full_path = os.path.join(workspace_path, file_path) if workspace_path else file_path
        
        # Check max_reviews for file access errors
        max_reviews = 2
        current_review_count = state.get("review_count", 0)

        # Check if path is a directory (invalid)
        if os.path.isdir(full_path):
            logger.warning(f"[review] Path is a directory, not a file: {full_path}")
            new_count = current_review_count + 1
            if new_count >= max_reviews:
                logger.info(f"[review] Max reviews ({max_reviews}) reached for invalid path - force advancing")
                return {
                    "current_step": current_step + 1,
                    "review_result": "LBTM",
                    "review_feedback": f"Invalid path: {file_path} is a directory, not a test file.",
                    "review_count": max_reviews,  # Keep at max so routing knows we hit limit
                    "total_lbtm_count": state.get("total_lbtm_count", 0) + 1,
                }
            return {
                "current_step": current_step,
                "review_result": "LBTM",
                "review_feedback": f"Invalid path: {file_path} is a directory. Please specify a valid test file path.",
                "review_count": new_count,
            }

        if not os.path.exists(full_path):
            logger.warning(f"[review] Test file not found: {full_path}")
            new_count = current_review_count + 1
            # Check max_reviews and force advance if exceeded
            if new_count >= max_reviews:
                logger.info(f"[review] Max reviews ({max_reviews}) reached for missing file - force advancing")
                return {
                    "current_step": current_step + 1,
                    "review_result": "LBTM",
                    "review_feedback": f"Test file {file_path} was not created after {max_reviews} attempts.",
                    "review_count": max_reviews,  # Keep at max so routing knows we hit limit
                    "total_lbtm_count": state.get("total_lbtm_count", 0) + 1,
                }
            # LBTM but keep current_step to retry same step
            return {
                "current_step": current_step,
                "review_result": "LBTM",
                "review_feedback": f"Test file {file_path} was not created. Please create the file at: {file_path}",
                "review_count": new_count,
            }

        with open(full_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Format scenarios
        scenarios_str = "\n".join(f"- {s}" for s in scenarios) if scenarios else "N/A"

        # Format testing context
        testing_context_str = ""
        if testing_context:
            import json
            testing_context_str = json.dumps(testing_context, indent=2, ensure_ascii=False)

        # Build review prompt
        input_text = REVIEW_INPUT_TEMPLATE.format(
            task_description=task_description,
            scenarios=scenarios_str,
            file_path=file_path,
            file_ext=_get_file_extension(file_path),
            file_content=file_content,
            testing_context=testing_context_str or "N/A",
        )

        messages = [
            SystemMessage(content=REVIEW_SYSTEM_PROMPT),
            HumanMessage(content=input_text),
        ]

        # Get review from LLM
        response = await _llm.ainvoke(messages, config=_cfg(state, "review_test"))
        response_text = response.content if hasattr(response, "content") else str(response)

        # Parse response
        review_result = _parse_review_response(response_text)

        logger.info(f"[review] {file_path}: {review_result['decision']}")

        if review_result["decision"] == "LBTM":
            logger.info(f"[review] Feedback: {review_result['feedback'][:100]}...")

        # Increment review_count if LBTM, reset to 0 if LGTM (new step)
        current_count = state.get("review_count", 0)
        if review_result["decision"] == "LBTM":
            new_count = current_count + 1
        else:
            new_count = 0  # Reset for next step on LGTM

        # Track total LBTM count
        total_lbtm = state.get("total_lbtm_count", 0)
        if review_result["decision"] == "LBTM":
            total_lbtm += 1

        # Increment current_step on LGTM OR when max reviews reached (force advance)
        max_reviews = 2
        new_current_step = state.get("current_step", 0)
        
        # Reset review_count when advancing to next step
        should_advance = False
        if review_result["decision"] == "LGTM":
            new_current_step += 1
            should_advance = True
            logger.info(f"[review] LGTM - advancing to step {new_current_step}")
        elif new_count >= max_reviews:
            # Force advance after max LBTM retries
            new_current_step += 1
            should_advance = True
            logger.info(f"[review] Max reviews ({max_reviews}) reached - force advancing to step {new_current_step}")

        # Keep review_count at max when force-advancing (LBTM), reset to 0 only for LGTM
        if should_advance and review_result["decision"] == "LGTM":
            final_review_count = 0  # Reset for next step
        elif should_advance:
            final_review_count = max_reviews  # Keep at max so routing knows we hit limit
        else:
            final_review_count = new_count

        return {
            "current_step": new_current_step,
            "review_result": review_result["decision"],
            "review_feedback": review_result["feedback"],
            "review_details": review_result["review"],
            "review_count": final_review_count,
            "total_lbtm_count": total_lbtm,
        }

    except Exception as e:
        logger.error(f"[review] Error: {e}", exc_info=True)
        # On error, return LBTM with error info, check max_reviews to avoid infinite loop
        max_reviews = 2
        current_review_count = state.get("review_count", 0)
        new_count = current_review_count + 1
        
        if new_count >= max_reviews:
            logger.info(f"[review] Max reviews ({max_reviews}) reached after error - force advancing")
            return {
                "current_step": current_step + 1,
                "review_result": "LBTM",
                "review_feedback": f"Review failed with error: {str(e)}",
                "review_count": max_reviews,  # Keep at max so routing knows we hit limit
                "total_lbtm_count": state.get("total_lbtm_count", 0) + 1,
                "error": str(e),
            }
        return {
            "current_step": current_step,
            "review_result": "LBTM",
            "review_feedback": f"Review failed with error: {str(e)}. Please check the file path.",
            "review_count": new_count,
            "error": str(e),
        }


def route_after_review(state: TesterState) -> str:
    """Route based on review result.

    Returns:
        - "implement_tests": LBTM, need to re-implement with feedback
        - "summarize": All steps done, go to final summary
        - "implement_tests": LGTM but more steps remain
    """
    review_result = state.get("review_result", "LGTM")
    review_count = state.get("review_count", 0)
    max_reviews = 2

    if review_result == "LBTM" and review_count < max_reviews:
        logger.info(f"[route_after_review] LBTM -> re-implement (attempt {review_count + 1})")
        return "implement_tests"

    # LGTM or max reviews reached
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)

    if current_step >= total_steps:
        logger.info("[route_after_review] All steps done -> summarize")
        return "summarize"

    logger.info(f"[route_after_review] LGTM -> next step ({current_step}/{total_steps})")
    return "implement_tests"
