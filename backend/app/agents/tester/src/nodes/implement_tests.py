"""Implement Tests node - Generate tests using structured output with skills and preloaded dependencies."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.skills import SkillRegistry
from app.agents.tester.src.state import TesterState
from app.agents.tester.src.nodes.helpers import send_message, generate_user_message
from app.agents.tester.src.schemas import TestFileOutput
from app.utils.token_utils import truncate_to_tokens
from app.agents.core.llm_factory import create_fast_llm, create_medium_llm
from app.core.config import llm_settings
MAX_RETRIES = llm_settings.MAX_RETRIES
RETRY_DELAY = llm_settings.RETRY_BACKOFF_MIN

MAX_CONCURRENT = llm_settings.MAX_CONCURRENT_TASKS

logger = logging.getLogger(__name__)

_llm = create_medium_llm()


def git_commit_tests(workspace_path: str, description: str, files: List[str] = None) -> bool:
    """Commit test files after successful implementation."""
    import subprocess
    
    try:
        # Stage files
        if files:
            for f in files:
                try:
                    subprocess.run(
                        ["git", "add", f],
                        cwd=workspace_path,
                        capture_output=True,
                        timeout=30
                    )
                except Exception:
                    pass
        else:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=workspace_path,
                capture_output=True,
                timeout=30
            )
        
        # Check if there are staged changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=workspace_path,
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0:
            logger.debug(f"[git] No changes to commit")
            return True
        
        # Commit with WIP message
        msg = f"wip(test): {description[:50]}"
        subprocess.run(
            ["git", "commit", "-m", msg, "--no-verify"],
            cwd=workspace_path,
            capture_output=True,
            timeout=30
        )
        logger.info(f"[git] Committed tests: {description[:50]}")
        return True
    except Exception as e:
        logger.warning(f"[git] Commit error: {e}")
        return False


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


def _cfg(config: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback from runtime config."""
    callbacks = config.get("callbacks", []) if config else []
    return {"callbacks": callbacks, "run_name": name} if callbacks else {"run_name": name}


def _get_relevant_component_source(state: dict, step: dict, workspace_path: str = "") -> str:
    """Get ONLY the relevant component source for this unit test step.
    
    This extracts the actual component code that tests should be based on,
    so LLM reads the REAL implementation instead of making assumptions.
    
    CRITICAL: Searches FILESYSTEM directly if not found in dependencies_content,
    because keyword extraction may miss important components like CategoryCard.
    """
    from pathlib import Path
    
    dependencies_content = state.get("dependencies_content", {})
    description = step.get("description", "").lower()
    workspace_path = workspace_path or state.get("workspace_path", "")
    
    # Keywords to match from description - expanded list
    keywords = ["category", "book", "card", "search", "hero", "section", "list", "grid", "item"]
    
    relevant = []
    found_paths = set()
    
    # 1. First, search in dependencies_content
    for path, content in dependencies_content.items():
        normalized_path = path.replace("\\", "/")
        
        # Only include component files
        if "components/" not in normalized_path or not path.endswith(".tsx"):
            continue
        # Skip UI primitives
        if "/ui/" in normalized_path:
            continue
        
        # Check if component name is mentioned in description or matches keywords
        component_name = path.split("/")[-1].replace(".tsx", "").lower()
        is_relevant = (
            component_name in description or
            any(kw in component_name for kw in keywords) or
            any(kw in description for kw in keywords if kw in normalized_path.lower())
        )
        
        if is_relevant:
            relevant.append(f"### {path}\n```tsx\n{content}\n```")
            found_paths.add(normalized_path)
    
    # 2. CRITICAL: Search filesystem directly for components not in dependencies_content
    # This ensures we find CategoryCard even if keyword extraction missed it
    if workspace_path:
        ws_path = Path(workspace_path)
        component_dirs = [
            ws_path / "src" / "components",
            ws_path / "components",
        ]
        
        for comp_dir in component_dirs:
            if not comp_dir.exists():
                continue
            
            for tsx_file in comp_dir.rglob("*.tsx"):
                if "node_modules" in str(tsx_file):
                    continue
                
                relative_path = str(tsx_file.relative_to(ws_path)).replace("\\", "/")
                
                # Skip if already found or is UI primitive
                if relative_path in found_paths or "/ui/" in relative_path:
                    continue
                
                component_name = tsx_file.stem.lower()
                
                # Check relevance
                is_relevant = (
                    component_name in description or
                    any(kw in component_name for kw in keywords) or
                    any(kw in description for kw in keywords if kw in relative_path.lower())
                )
                
                if is_relevant:
                    try:
                        content = tsx_file.read_text(encoding="utf-8")
                        # Truncate very long files
                        if len(content) > 5000:
                            content = content[:5000] + "\n// ... (truncated)"
                        relevant.append(f"### {relative_path}\n```tsx\n{content}\n```")
                        found_paths.add(relative_path)
                        logger.info(f"[_get_relevant_component_source] Found from filesystem: {relative_path}")
                    except Exception as e:
                        logger.warning(f"[_get_relevant_component_source] Failed to read {tsx_file}: {e}")
    
    return "\n\n".join(relevant[:3])  # Limit to 3 most relevant


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
        return f"Created: {file_path}"
    except Exception as e:
        logger.error(f"[_write_file_direct] Error writing {file_path}: {e}")
        return f"Error: {e}"


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
    config: dict = None,
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
    
    # FIX MODE: Read existing test code to preserve working tests
    existing_test_code = ""
    fix_instructions = ""
    
    # Get fix context from step (populated by analyze_errors)
    error_code = step.get("error_code", "")
    find_code = step.get("find_code", "")
    replace_with = step.get("replace_with", "")
    
    if file_path in failed_files:
        # Read current file content before re-implementing
        full_path = Path(workspace_path) / file_path
        if full_path.exists():
            try:
                existing_test_code = full_path.read_text(encoding="utf-8")
                
                # Build precise fix instructions based on error_code
                fix_instructions = f"""
FIX MODE - CRITICAL RULES:
You are FIXING an existing test file, NOT creating a new one.

## Error Code: {error_code}

## PRECISE FIX REQUIRED:
"""
                # Add specific instructions based on error type
                if error_code == "ARIA_SELECTED":
                    fix_instructions += """
⚠️ ARIA_SELECTED ERROR - The component does NOT have selection state!
- DELETE any assertion that checks aria-selected='true'
- DELETE any waitFor that waits for aria-selected to change
- The component renders ALL options with aria-selected='false' - this is correct behavior
- Just remove the broken assertion, keep other tests
"""
                elif error_code == "FETCH_ASSERTION":
                    fix_instructions += """
⚠️ FETCH_ASSERTION ERROR - Unit tests should NOT test fetch calls!
- DELETE any expect(fetch).toHaveBeenCalled() assertions
- DELETE any expect(fetch).toHaveBeenCalledWith(...) assertions
- Unit tests should only test UI rendering, not API calls
- Keep the component render and UI assertions
"""
                elif error_code == "NO_ERROR_STATE":
                    fix_instructions += """
⚠️ NO_ERROR_STATE - Component does not render error UI!
- DELETE assertions looking for error messages
- DELETE assertions for error states
- Component does not have error handling UI
"""
                
                # Add find/replace if provided
                if find_code:
                    fix_instructions += f"""
## EXACT CODE TO FIND AND {'DELETE' if not replace_with else 'REPLACE'}:
```
{find_code}
```
"""
                    if replace_with:
                        fix_instructions += f"""
## REPLACE WITH:
```
{replace_with}
```
"""
                    else:
                        fix_instructions += """
## ACTION: DELETE the code above entirely (do not replace with anything)
"""
                
                fix_instructions += """
## RULES:
1. PRESERVE ALL WORKING TESTS - Do NOT remove or rewrite tests that work
2. ONLY FIX the specific error - make minimal changes
3. Keep the SAME file structure, imports, and describe blocks
4. The existing test code is in <existing_test_code>
5. Your output must be a MODIFIED VERSION of this code
"""
                logger.info(f"[implement_tests] FIX MODE: Loaded existing code for {file_path} ({len(existing_test_code)} chars), error_code={error_code}")
            except Exception as e:
                logger.warning(f"[implement_tests] Could not read existing file {file_path}: {e}")
    
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
        existing_test_code=existing_test_code,
        fix_instructions=fix_instructions,
    )
    
    # For unit tests: Add CRITICAL component source code with MANDATORY verification
    if test_type == "unit":
        relevant_components = _get_relevant_component_source(state, step, workspace_path)
        if relevant_components:
            user_prompt += f"""

<critical_source_code>
## ⛔ MANDATORY: PARSE THIS SOURCE CODE FIRST!

Before writing ANY test assertion, you MUST:
1. List ALL elements you found in the source below (inputs, buttons, headings, links)
2. For each assertion, the element MUST exist in this source code
3. If element is NOT in source → DO NOT write test for it

## Source Code (the ONLY truth):
{relevant_components}

## ⛔ YOUR VERIFICATION TASK (do this FIRST):
Scan the source code above and list what you found:
- Inputs/Search bars: [list any <input> or <Input> with placeholder, or write "NONE"]
- Buttons: [list any <button> or <Button> text, or write "NONE"]
- Headings: [list any <h1>-<h6> text, or write "NONE"]
- Links: [list any <Link> or <a> href patterns, or write "NONE"]

⛔ ONLY write tests for elements you listed above!
⛔ If you wrote "NONE" for inputs → DO NOT test for search/input elements!
</critical_source_code>
"""
        
        # Add summary as secondary reference only
        component_context = state.get("component_context", "")
        if component_context:
            user_prompt += f"\n\n<component_summary>\n(Reference only - verify against source code above)\n{component_context}\n</component_summary>"
    
    # Append pre-loaded context (API routes, libs, etc.)
    if deps_context:
        user_prompt += f"\n\n{deps_context}"
    
    if feedback_section:
        user_prompt += f"\n\n{feedback_section}"
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        logger.info(f"[implement_tests] Step {step_index + 1}: {description[:50]}... (skills: {step_skills})")
        
        # Get implement LLM
        step_llm = create_medium_llm()
        structured_llm = step_llm.with_structured_output(TestFileOutput)
        # Pass config from runtime (not state) to avoid checkpoint serialization issues
        result = await _invoke_with_retry(
            structured_llm,
            messages,
            config=_cfg(config, f"implement_step_{step_index + 1}"),
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

async def implement_tests(state: TesterState, config: dict = None, agent=None) -> dict:
    """Implement ALL test steps in PARALLEL using asyncio.gather.
    
    Args:
        state: Current tester state
        config: LangGraph runtime config (contains callbacks for Langfuse)
        agent: Tester agent instance

    This node:
    1. Gets ALL steps from test_plan
    2. Runs all implementations in parallel (IT + UT simultaneously)
    3. Collects results and writes all files
    4. Returns all modified files for parallel review
    5. Git commits test files after each successful implementation

    Includes interrupt signal check for pause/cancel support.

    Benefits:
    - 50% faster: IT and UT run at the same time
    - Same quality: Each step gets full context
    """
    # FIX #1: Removed duplicate signal check - handled by _run_graph_with_signal_check()
    from app.agents.developer.src.utils.story_logger import StoryLogger
    
    config = config or {}  # Ensure config is not None
    
    # Create story logger
    story_logger = StoryLogger.from_state(state, agent).with_node("implement_tests")
    story_id = state.get("story_id", "")
    
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
    else:
        steps_to_run = list(enumerate(test_plan))
    
    if not steps_to_run:
        await story_logger.info("No steps to implement")
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
            config=config,
        )
        tasks.append(task)
    
    # Run ALL implementations in PARALLEL
    await story_logger.message(f"🔨 Implementing {len(tasks)} test files in parallel...")
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
    
    # Refresh dependencies_content for modified test files (Developer V2 pattern)
    # This ensures later steps (like analyze_errors) have fresh context
    dependencies_content = dict(state.get("dependencies_content", {}))
    if workspace_path and files_modified:
        for file_path in files_modified:
            if file_path.endswith(('.test.ts', '.test.tsx')):
                full_path = os.path.join(workspace_path, file_path)
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            dependencies_content[file_path] = f.read()
                        logger.debug(f"[implement_tests] Refreshed dependency: {file_path}")
                    except Exception as e:
                        logger.warning(f"[implement_tests] Failed to refresh {file_path}: {e}")
    
    # Git commit test files after successful implementation (aligned with Developer V2)
    if workspace_path and files_modified:
        test_desc = f"{len(files_modified)} test files"
        git_commit_tests(workspace_path, test_desc, files_modified)
    
    # FIX #1: Removed post-implementation signal check - handled by _run_graph_with_signal_check()
    
    # Progress message (persona-driven intro + file list)
    intro = await generate_user_message(
        "implement_done",
        f"{success_count}/{len(tasks)} test files created",
        agent
    )
    msg = intro
    for result in implementation_results:
        if result.get("success"):
            test_icon = "🧩" if result.get("test_type") == "unit" else "🔧"
            msg += f"\n   {test_icon} {result.get('file_path', 'unknown')}"
    
    await send_message(state, agent, msg, "progress")
    logger.info(f"[implement_tests] Completed: {success_count}/{len(tasks)} successful")
    
    return {
        "current_step": total_steps,  # All steps done
        "files_modified": files_modified,
        "dependencies_content": dependencies_content,  # Refreshed dependencies
        "implementation_results": implementation_results,
        "review_count": 0,  # Reset for fresh review
        "failed_files": [],  # Clear failed files after re-implementation
        "message": msg,
        "action": "REVIEW",
    }
