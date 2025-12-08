"""Implement Tests node - Generate tests using structured output (Developer V2 pattern).

Optimized version:
- NO tool calling iterations
- Skills preloaded into system prompt
- Dependencies preloaded from plan phase
- Single LLM call with structured output + retry
- Direct file write (no tools)
"""

import asyncio
import logging
from pathlib import Path
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.skills import SkillRegistry
from app.agents.tester.src.state import TesterState
from app.agents.tester.src.core_nodes import send_message
from app.agents.tester.src.utils.token_utils import truncate_to_tokens
from app.agents.tester.src._llm import implement_llm

logger = logging.getLogger(__name__)

_llm = implement_llm

# Config
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


# =============================================================================
# Structured Output Schema (Developer V2 pattern)
# =============================================================================

class TestFileOutput(BaseModel):
    """Structured output for test file generation. NO tool calling needed."""
    file_path: str = Field(description="Relative path to the test file")
    content: str = Field(description="Complete test file content (TypeScript/JavaScript)")
    summary: str = Field(default="", description="Brief summary of what was tested")


# =============================================================================
# Helper Functions
# =============================================================================

def _preload_skills(registry: SkillRegistry, skill_ids: list[str]) -> str:
    """Preload skill content into system prompt (Developer V2 pattern).
    
    This eliminates the need for activate_skill tool calls entirely.
    Loads ALL bundled reference files (aligned with Developer V2).
    """
    if not skill_ids or not registry:
        return ""
    
    parts = []
    for skill_id in skill_ids:
        skill = registry.get_skill(skill_id)
        if not skill:
            logger.warning(f"[_preload_skills] Skill not found: {skill_id}")
            continue
        
        content = skill.load_content()
        if not content:
            continue
        
        # Include ALL bundled reference files (Developer V2 pattern - no limit)
        try:
            bundled = skill.list_bundled_files()
            for bf in bundled:  # Load ALL, not just first 2
                bf_content = skill.load_bundled_file(bf)
                if bf_content:
                    content += f"\n\n### Reference: {bf}\n{bf_content}"
        except Exception as e:
            logger.warning(f"[_preload_skills] Error loading bundled files: {e}")
        
        parts.append(f"## Skill: {skill_id}\n{content}")
        logger.info(f"[_preload_skills] Preloaded skill: {skill_id} ({len(content)} chars)")
    
    if not parts:
        return ""
    
    return "<skills>\n" + "\n\n---\n\n".join(parts) + "\n</skills>"


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {"run_name": name}


def _build_dependencies_context(dependencies_content: dict, step_dependencies: list) -> str:
    """Build pre-loaded dependencies context for the current step (MetaGPT-style)."""
    if not dependencies_content:
        return ""
    
    parts = []
    included_paths = set()
    
    # 1. Add step-specific dependencies first
    if step_dependencies:
        for dep_path in step_dependencies:
            if not isinstance(dep_path, str):
                continue
            if dep_path in dependencies_content:
                content = dependencies_content[dep_path]
                ext = dep_path.split(".")[-1] if "." in dep_path else ""
                lang = "typescript" if ext in ["ts", "tsx"] else "javascript" if ext in ["js", "jsx"] else ""
                parts.append(f"### {dep_path}\n```{lang}\n{content}\n```")
                included_paths.add(dep_path)
    
    # 2. Add ALL source files (API routes, services, components)
    source_patterns = ["src/app/api/", "src/lib/", "src/services/", "app/api/", "pages/api/", "src/components/"]
    for dep_path, content in dependencies_content.items():
        if dep_path in included_paths:
            continue
        normalized_path = dep_path.replace("\\", "/")
        if any(pattern in normalized_path for pattern in source_patterns):
            ext = dep_path.split(".")[-1] if "." in dep_path else ""
            lang = "typescript" if ext in ["ts", "tsx"] else "javascript"
            parts.append(f"### {dep_path} (SOURCE CODE)\n```{lang}\n{content}\n```")
            included_paths.add(dep_path)
    
    # 3. Add common test setup files
    common_files = ["jest.config.ts", "jest.setup.ts", "prisma/schema.prisma"]
    for dep_path in common_files:
        if dep_path in dependencies_content and dep_path not in included_paths:
            content = dependencies_content[dep_path]
            parts.append(f"### {dep_path}\n```\n{content}\n```")
            included_paths.add(dep_path)
    
    if not parts:
        return ""
    
    header = """<pre_loaded_context>
## Read SOURCE CODE below for actual exports, types, function signatures.
## Use EXACT imports from these files.

"""
    return header + "\n\n".join(parts) + "\n</pre_loaded_context>"


def _write_file_direct(workspace_path: str, file_path: str, content: str) -> str:
    """Write file directly without tool calling."""
    try:
        full_path = Path(workspace_path) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        logger.info(f"[_write_file_direct] Written: {file_path}")
        return f"✅ Created: {file_path}"
    except Exception as e:
        logger.error(f"[_write_file_direct] Error writing {file_path}: {e}")
        return f"❌ Error: {e}"


async def _invoke_with_retry(
    structured_llm,
    messages: list,
    config: dict,
    max_retries: int = MAX_RETRIES,
) -> TestFileOutput:
    """Invoke structured LLM with retry logic.
    
    Retries on:
    - Timeout errors
    - Connection errors
    - Parse errors (structured output validation)
    """
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            result = await structured_llm.ainvoke(messages, config=config)
            
            # Validate result
            if not result.content or len(result.content) < 50:
                raise ValueError("Generated content too short")
            
            return result
            
        except Exception as e:
            last_error = e
            logger.warning(f"[implement_tests] Attempt {attempt}/{max_retries} failed: {e}")
            
            if attempt < max_retries:
                wait_time = RETRY_DELAY * attempt  # Exponential backoff
                logger.info(f"[implement_tests] Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
    
    # All retries failed
    raise last_error


# =============================================================================
# Main Node Function
# =============================================================================

async def implement_tests(state: TesterState, agent=None) -> dict:
    """Implement tests using structured output (Developer V2 pattern).

    This node:
    1. Gets current step from test_plan
    2. Preloads skills into system prompt (no tool calls)
    3. Uses pre-loaded dependencies from plan_tests
    4. Single LLM call with structured output + retry
    5. Direct file write (no tools)

    Output:
    - current_step: NOT incremented (review node handles this on LGTM)
    - files_modified: Updated list
    - review_count: Reset to 0 for fresh review
    """
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] implement_tests - step {current_step + 1}/{total_steps}")

    test_plan = state.get("test_plan", [])
    workspace_path = state.get("workspace_path", "") or state.get("project_path", "")
    tech_stack = state.get("tech_stack", "nextjs")

    # Check if all steps done
    if current_step >= total_steps or current_step >= len(test_plan):
        logger.info("[implement_tests] All steps completed")
        return {
            "message": "Hoàn thành tất cả steps.",
            "action": "RUN",
        }

    # Get current step
    step = test_plan[current_step]
    test_type = step.get("type", "integration")
    file_path = step.get("file_path", "")
    story_title = step.get("story_title", "Unknown")
    description = step.get("description", "")
    scenarios = step.get("scenarios", [])
    step_skills = step.get("skills", [])
    step_dependencies = step.get("dependencies", [])

    # Initialize skill registry and preload skills
    skill_registry = SkillRegistry.load(tech_stack)
    
    # Auto-select skills if not specified based on test_type
    if not step_skills:
        if test_type == "unit":
            step_skills = ["unit-test"]
        else:
            step_skills = ["integration-test"]
    
    # Preload skills into prompt (Developer V2 pattern - no tool calls)
    skills_content = _preload_skills(skill_registry, step_skills)
    logger.info(f"[implement_tests] Preloaded {len(step_skills)} skills: {step_skills}")

    # Build pre-loaded dependencies context
    dependencies_content = state.get("dependencies_content", {})
    deps_context = _build_dependencies_context(dependencies_content, step_dependencies)
    if deps_context:
        logger.info(f"[implement_tests] Built deps_context with {len(deps_context)} chars")

    # Include feedback from previous review (if LBTM)
    feedback_section = ""
    review_feedback = state.get("review_feedback", "")
    if review_feedback:
        feedback_section = f"\n<previous_feedback>\n{review_feedback}\n</previous_feedback>"

    # Format scenarios
    scenarios_str = "\n".join(f"- {s}" for s in scenarios) if scenarios else "N/A"

    # Build system prompt with preloaded skills
    system_prompt = get_system_prompt("implement")
    if skills_content:
        system_prompt += f"\n\n{skills_content}"

    # Build user prompt
    user_prompt = get_user_prompt(
        "implement",
        step_number=current_step + 1,
        total_steps=total_steps,
        test_type=test_type,
        file_path=file_path,
        story_title=story_title,
        description=description,
        scenarios=scenarios_str,
    )

    # Append pre-loaded context and feedback (load ALL dependencies)
    if deps_context:
        user_prompt += f"\n\n{deps_context}"
    
    # Add component context for unit tests (helps with correct selectors/props)
    if test_type == "unit":
        component_context = state.get("component_context", "")
        if component_context:
            user_prompt += f"\n\n<component_analysis>\n{component_context}\n</component_analysis>"
    
    if feedback_section:
        user_prompt += f"\n\n{feedback_section}"

    try:
        # Build messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Single LLM call with structured output + retry
        logger.info(f"[implement_tests] Step {current_step + 1}: {description[:50]}...")
        
        structured_llm = _llm.with_structured_output(TestFileOutput)
        result = await _invoke_with_retry(
            structured_llm,
            messages,
            config=_cfg(state, f"implement_step_{current_step + 1}"),
        )

        # Direct file write (no tools)
        actual_file_path = result.file_path or file_path
        write_result = _write_file_direct(workspace_path, actual_file_path, result.content)
        logger.info(f"[implement_tests] {write_result}")

        # Track files
        files_modified = state.get("files_modified", []).copy()
        if actual_file_path and actual_file_path not in files_modified:
            files_modified.append(actual_file_path)

        # Progress message
        msg = f"✅ Step {current_step + 1}/{total_steps}: {description}"
        if result.summary:
            msg += f"\n   {result.summary}"
        await send_message(state, agent, msg, "progress")

        logger.info(f"[implement_tests] Completed step {current_step + 1}")

        return {
            "current_step": current_step,  # Review node will increment on LGTM
            "files_modified": files_modified,
            "last_implemented_file": actual_file_path,
            "last_test_content": result.content[:2000],  # For review
            "review_count": 0,  # Reset for fresh review
            "message": msg,
            "action": "REVIEW",
        }

    except Exception as e:
        logger.error(f"[implement_tests] Error after {MAX_RETRIES} retries: {e}", exc_info=True)
        error_msg = f"Lỗi khi implement step {current_step + 1}: {str(e)}"
        await send_message(state, agent, error_msg, "error")
        return {
            "error": str(e),
            "message": error_msg,
            "action": "RESPOND",
        }
