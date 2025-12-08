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
# Single Step Implementation (used by parallel executor)
# =============================================================================

async def _implement_single_step(
    state: TesterState,
    step: dict,
    step_index: int,
    total_steps: int,
    skill_registry: SkillRegistry,
    workspace_path: str,
) -> dict:
    """Implement a single test step (called in parallel).
    
    Returns:
        Dict with file_path, content, success, error
    """
    test_type = step.get("type", "integration")
    file_path = step.get("file_path", "")
    story_title = step.get("story_title", "Unknown")
    description = step.get("description", "")
    scenarios = step.get("scenarios", [])
    step_skills = step.get("skills", [])
    step_dependencies = step.get("dependencies", [])
    
    # Auto-select skills if not specified based on test_type
    if not step_skills:
        step_skills = ["unit-test"] if test_type == "unit" else ["integration-test"]
    
    # Preload skills into prompt
    skills_content = _preload_skills(skill_registry, step_skills)
    
    # Build pre-loaded dependencies context
    dependencies_content = state.get("dependencies_content", {})
    deps_context = _build_dependencies_context(dependencies_content, step_dependencies)
    
    # Include feedback from previous review (if LBTM - for re-implementation)
    feedback_section = ""
    review_feedback = state.get("review_feedback", "")
    failed_files = state.get("failed_files", [])
    
    # Only include feedback if this specific file failed
    if review_feedback and file_path in failed_files:
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
        step_number=step_index + 1,
        total_steps=total_steps,
        test_type=test_type,
        file_path=file_path,
        story_title=story_title,
        description=description,
        scenarios=scenarios_str,
    )
    
    # Append pre-loaded context
    if deps_context:
        user_prompt += f"\n\n{deps_context}"
    
    # Add component context for unit tests
    if test_type == "unit":
        component_context = state.get("component_context", "")
        if component_context:
            user_prompt += f"\n\n<component_analysis>\n{component_context}\n</component_analysis>"
    
    if feedback_section:
        user_prompt += f"\n\n{feedback_section}"
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        logger.info(f"[implement_tests] Step {step_index + 1}: {description[:50]}...")
        
        structured_llm = _llm.with_structured_output(TestFileOutput)
        result = await _invoke_with_retry(
            structured_llm,
            messages,
            config=_cfg(state, f"implement_step_{step_index + 1}"),
        )
        
        # Direct file write
        actual_file_path = result.file_path or file_path
        write_result = _write_file_direct(workspace_path, actual_file_path, result.content)
        logger.info(f"[implement_tests] {write_result}")
        
        return {
            "success": True,
            "file_path": actual_file_path,
            "content": result.content,
            "summary": result.summary,
            "step_index": step_index,
            "test_type": test_type,
        }
        
    except Exception as e:
        logger.error(f"[implement_tests] Step {step_index + 1} failed: {e}")
        return {
            "success": False,
            "file_path": file_path,
            "error": str(e),
            "step_index": step_index,
            "test_type": test_type,
        }


# =============================================================================
# Main Node Function - PARALLEL EXECUTION
# =============================================================================

async def implement_tests(state: TesterState, agent=None) -> dict:
    """Implement ALL test steps in PARALLEL using asyncio.gather.

    This node:
    1. Gets ALL steps from test_plan
    2. Runs all implementations in parallel (IT + UT simultaneously)
    3. Collects results and writes all files
    4. Returns all modified files for parallel review

    Benefits:
    - 50% faster: IT and UT run at the same time
    - Same quality: Each step gets full context
    """
    test_plan = state.get("test_plan", [])
    total_steps = len(test_plan)
    workspace_path = state.get("workspace_path", "") or state.get("project_path", "")
    tech_stack = state.get("tech_stack", "nextjs")
    
    # Check for re-implementation mode (after LBTM)
    failed_files = state.get("failed_files", [])
    is_reimplementation = bool(failed_files)
    
    if is_reimplementation:
        # Only re-implement failed files
        steps_to_run = [
            (i, step) for i, step in enumerate(test_plan)
            if step.get("file_path", "") in failed_files
        ]
        print(f"[NODE] implement_tests - RE-IMPLEMENTING {len(steps_to_run)} failed files")
    else:
        # First run: implement ALL steps
        steps_to_run = list(enumerate(test_plan))
        print(f"[NODE] implement_tests - PARALLEL {total_steps} steps")
    
    if not steps_to_run:
        logger.info("[implement_tests] No steps to implement")
        return {
            "message": "Không có steps cần implement.",
            "action": "RUN",
        }
    
    # Initialize skill registry once (shared across all steps)
    skill_registry = SkillRegistry.load(tech_stack)
    logger.info(f"[SkillRegistry] Loaded {len(skill_registry.skills)} skills for '{tech_stack}'")
    
    # Create tasks for ALL steps
    tasks = []
    for step_index, step in steps_to_run:
        task = _implement_single_step(
            state=state,
            step=step,
            step_index=step_index,
            total_steps=total_steps,
            skill_registry=skill_registry,
            workspace_path=workspace_path,
        )
        tasks.append(task)
    
    # Run ALL implementations in PARALLEL
    logger.info(f"[implement_tests] Running {len(tasks)} steps in parallel...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    files_modified = state.get("files_modified", []).copy() if is_reimplementation else []
    implementation_results = []
    success_count = 0
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"[implement_tests] Task exception: {result}")
            continue
        
        if isinstance(result, dict):
            implementation_results.append(result)
            
            if result.get("success"):
                success_count += 1
                file_path = result.get("file_path", "")
                if file_path and file_path not in files_modified:
                    files_modified.append(file_path)
    
    # Progress message
    msg = f"✅ Implemented {success_count}/{len(tasks)} test files in parallel"
    for result in implementation_results:
        if result.get("success"):
            test_icon = "🧩" if result.get("test_type") == "unit" else "🔧"
            msg += f"\n   {test_icon} {result.get('file_path', 'unknown')}"
    
    await send_message(state, agent, msg, "progress")
    logger.info(f"[implement_tests] Completed: {success_count}/{len(tasks)} successful")
    
    return {
        "current_step": total_steps,  # All steps done
        "files_modified": files_modified,
        "implementation_results": implementation_results,
        "review_count": 0,  # Reset for fresh review
        "failed_files": [],  # Clear failed files after re-implementation
        "message": msg,
        "action": "REVIEW",
    }
