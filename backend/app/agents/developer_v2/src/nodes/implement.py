"""Implement node - Direct file output without tools."""
import json
import logging
import os
import platform
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState


class ImplementOutput(BaseModel):
    content: str = Field(description="Complete file content")

from app.agents.developer_v2.src.tools.filesystem_tools import get_modified_files, reset_modified_files, _modified_files
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg
from app.agents.developer_v2.src.utils.prompt_utils import (
    format_input_template as _format_input_template,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.utils.token_utils import truncate_to_tokens
from app.agents.developer_v2.src.nodes._llm import code_llm, get_llm_for_skills
from app.agents.developer_v2.src.skills import SkillRegistry, get_project_structure

logger = logging.getLogger(__name__)


def _build_modified_files_context(files_modified: list) -> str:
    if not files_modified:
        return "None"
    return "\n".join(f"- {f}" for f in files_modified)


def _build_dependencies_context(
    dependencies_content: dict, 
    step_dependencies: list,
    workspace_path: str = "",
    exclude_file: str = ""
) -> str:
    """Build context from dependencies, auto-loading from disk if not in cache."""
    parts = []
    loaded_files = set()
    
    if step_dependencies:
        for dep_path in step_dependencies:
            if not isinstance(dep_path, str):
                continue
            if dep_path == exclude_file:
                continue
            
            content = dependencies_content.get(dep_path)
            if not content and workspace_path:
                full_path = os.path.join(workspace_path, dep_path)
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        logger.debug(f"[implement] Auto-loaded dependency: {dep_path}")
                    except Exception as e:
                        logger.warning(f"[implement] Failed to load {dep_path}: {e}")
            
            if content:
                parts.append(f"### {dep_path}\n```\n{content[:5000]}\n```")
                loaded_files.add(dep_path)
    
    common_files = ["prisma/schema.prisma"]
    for dep_path in common_files:
        if dep_path in loaded_files or dep_path == exclude_file:
            continue
        if workspace_path:
            full_path = os.path.join(workspace_path, dep_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    parts.append(f"### {dep_path}\n```\n{content}\n```")
                    continue
                except Exception:
                    pass
        if dep_path in dependencies_content:
            parts.append(f"### {dep_path}\n```\n{dependencies_content[dep_path]}\n```")
    
    if not parts:
        return ""
    return "<pre_loaded_context>\n" + "\n\n".join(parts) + "\n</pre_loaded_context>"


def _build_debug_summary(state: dict) -> str:
    """Build summary of previous debug attempts."""
    debug_count = state.get("debug_count", 0)
    review_count = state.get("review_count", 0)
    react_loop_count = state.get("react_loop_count", 0)
    
    if debug_count == 0 and review_count == 0:
        return ""
    
    parts = ["## Debug Summary (Previous Attempts)"]
    
    # Debug iterations info
    if debug_count > 0 or react_loop_count > 0:
        parts.append(f"- Debug iterations: {debug_count}")
        parts.append(f"- React loop count: {react_loop_count}")
    
    # Review feedback history
    if review_count > 0:
        parts.append(f"- Review attempts: {review_count}")
        review_feedback = state.get("review_feedback", "")
        if review_feedback:
            parts.append(f"- Last review feedback:\n```\n{review_feedback[:500]}\n```")
    
    # Previous errors
    error = state.get("error", "")
    run_stderr = state.get("run_stderr", "")
    if error:
        parts.append(f"- Last error: {error[:300]}")
    if run_stderr:
        parts.append(f"- Runtime stderr:\n```\n{run_stderr[:500]}\n```")
    
    # Files already modified
    files_modified = state.get("files_modified", [])
    if files_modified:
        parts.append(f"- Files modified so far: {', '.join(files_modified[:10])}")
    
    # Step LBTM counts
    step_lbtm_counts = state.get("step_lbtm_counts", {})
    if step_lbtm_counts:
        lbtm_info = ", ".join(f"step {k}: {v}" for k, v in step_lbtm_counts.items())
        parts.append(f"- LBTM counts per step: {lbtm_info}")
    
    parts.append("\nIMPORTANT: Learn from previous attempts. Don't repeat the same mistakes.")
    
    return "\n".join(parts)


def _parse_implement_output(response_content: str) -> Optional[ImplementOutput]:
    """Parse structured output from LLM response.
    
    Handles both JSON code blocks and raw JSON.
    """
    if not response_content:
        return None
    
    # Try to extract JSON from code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_content)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try raw JSON
        json_str = response_content.strip()
    
    try:
        data = json.loads(json_str)
        return ImplementOutput(**data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[implement] Failed to parse output: {e}")
        return None


def _preload_skills(registry: SkillRegistry, skill_ids: list[str], include_bundled: bool = True) -> str:
    """Preload skill content for injection into system prompt.
    
    Args:
        registry: SkillRegistry instance
        skill_ids: List of skill IDs to load
        include_bundled: Whether to include bundled reference files
    
    Returns:
        Formatted skill content string
    """
    if not skill_ids:
        return ""
    
    parts = []
    for skill_id in skill_ids:
        skill = registry.get_skill(skill_id)
        if not skill:
            logger.warning(f"[implement] Skill not found: {skill_id}")
            continue
        
        content = skill.load_content()
        if not content:
            continue
        
        # Optionally include bundled reference files
        if include_bundled:
            bundled = skill.list_bundled_files()
            logger.debug(f"[implement] Skill {skill_id} bundled files: {bundled}")
            for bf in bundled:  # Load all bundled files
                bf_content = skill.load_bundled_file(bf)
                if bf_content:
                    content += f"\n\n### Reference: {bf}\n{bf_content}"
                    logger.debug(f"[implement] Loaded reference {bf}: {len(bf_content)} chars")
        
        parts.append(f"## Skill: {skill_id}\n{content}")
        logger.info(f"[implement] Preloaded skill: {skill_id} ({len(content)} chars, bundled: {len(bundled) if include_bundled else 0})")
    
    return "\n\n---\n\n".join(parts) if parts else ""


async def implement(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute implementation step with preloaded skills."""
    reset_modified_files()
    
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    logger.info(f"[NODE] implement {current_step + 1}/{total_steps}")
    
    # Check debug mode early for review_count logic
    task_type = state.get("task_type", "")
    debug_count = state.get("debug_count", 0)
    is_debug_mode = task_type == "bug_fix" or debug_count > 0
    
    # Fix: Don't reset review_count in debug mode to prevent infinite LBTM loop
    previous_step = state.get("_last_implement_step", -1)
    if is_debug_mode:
        review_count = state.get("review_count", 0)
    else:
        review_count = 0 if current_step != previous_step else state.get("review_count", 0)
    
    # Max debug reviews limit to prevent infinite loops
    MAX_DEBUG_REVIEWS = 3
    if is_debug_mode and review_count >= MAX_DEBUG_REVIEWS:
        logger.warning(f"[implement] Max debug reviews ({MAX_DEBUG_REVIEWS}) reached, skipping to validate")
        return {**state, "review_count": review_count, "action": "VALIDATE"}
    
    try:
        plan_steps = state.get("implementation_plan", [])
        workspace_path = state.get("workspace_path", "")
        tech_stack = state.get("tech_stack", "nextjs")
        
        react_loop_count = state.get("react_loop_count", 0)
        # debug_count already defined above
        if state.get("react_mode") and state.get("run_status") == "FAIL":
            current_step = 0
            react_loop_count += 1
            logger.info(f"[implement] React loop {react_loop_count}, debug_count={debug_count}")
        
        if not plan_steps:
            return {**state, "error": "No implementation plan", "action": "RESPOND"}
        
        if current_step >= len(plan_steps):
            return {**state, "message": "Implementation done", "action": "VALIDATE"}
        
        step = plan_steps[current_step]
        task_description = step.get("task", step.get("description", ""))
        file_path = step.get("file_path", "")
        action = step.get("action", "")
        step_dependencies = step.get("dependencies", [])
        step_skills = step.get("skills", [])  # Skills from plan
        
        # Auto-include frontend-component when frontend-design is used
        if "frontend-design" in step_skills and "frontend-component" not in step_skills:
            step_skills = step_skills + ["frontend-component"]
        
        # Load skill registry and preload skills from step
        skill_registry = state.get("skill_registry") or SkillRegistry.load(tech_stack)
        
        # Preload skills specified in plan step
        skills_content = _preload_skills(skill_registry, step_skills)
        
        # Context: only dependencies (project_structure removed - skills have patterns)
        context_parts = []
        dependencies_content = state.get("dependencies_content", {})
        # Auto-load dependencies from disk if not in cache (MetaGPT-style)
        deps_context = _build_dependencies_context(
            dependencies_content, 
            step_dependencies,
            workspace_path=workspace_path,
            exclude_file=file_path
        )
        if deps_context:
            context_parts.append(deps_context)
        
        feedback_section = ""
        if state.get("review_feedback"):
            feedback_section = f"<review_feedback>\n{state.get('review_feedback')}\n</review_feedback>"
        if state.get("summarize_feedback"):
            feedback_section += f"\n<summarize_feedback>\n{state.get('summarize_feedback')}\n</summarize_feedback>"
        if state.get('run_stderr'):
            feedback_section += f"\n<errors>\n{state.get('run_stderr')[:2000]}\n</errors>"
        
        # Add debug summary for previous attempts (MetaGPT-style)
        debug_summary = _build_debug_summary(state)
        if debug_summary:
            feedback_section += f"\n\n{debug_summary}"
        
        # is_debug_mode already defined above
        
        # Add debugging skill if in debug mode
        if is_debug_mode and "debugging" not in step_skills:
            debug_content = _preload_skills(skill_registry, ["debugging"])
            if debug_content:
                skills_content = f"{skills_content}\n\n---\n\n{debug_content}" if skills_content else debug_content
        
        # No tools - all context is pre-loaded (MetaGPT-style)
        
        files_modified = state.get("files_modified", [])
        modified_files_content = _build_modified_files_context(files_modified)
        
        logic_analysis = state.get("logic_analysis", [])
        logic_analysis_str = "\n".join(
            f"- {item[0]}: {item[1]}" 
            for item in logic_analysis 
            if isinstance(item, list) and len(item) >= 2
        ) or "None"
        
        legacy_code = "None (new file)"
        if action == "modify" and file_path:
            full_path = os.path.join(workspace_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        legacy_code = f.read()
                except Exception:
                    legacy_code = "Error reading file"
        
        debug_logs = "None"
        error_analysis = state.get("error_analysis") or {}
        if error_analysis.get("error_message"):
            debug_logs = error_analysis["error_message"][:2000]
        elif state.get("error"):
            debug_logs = state.get("error")[:2000]
        
        enhanced_task = task_description
        if file_path:
            enhanced_task = f"[{action.upper()}] {file_path}\n{task_description}"
        
        input_text = _format_input_template(
            "implement_step",
            step_number=current_step + 1,
            total_steps=len(plan_steps),
            task_description=enhanced_task,
            modified_files=modified_files_content,
            related_context=truncate_to_tokens("\n\n".join(context_parts), 4000),
            feedback_section=feedback_section,
            logic_analysis=logic_analysis_str,
            legacy_code=legacy_code,
            debug_logs=debug_logs,
        )
        
        # Build system prompt with preloaded skills (no skill catalog needed)
        system_prompt = _build_system_prompt("implement_step", skills_content=skills_content)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ]
        
        # Select model based on step skills (opus for UI, sonnet for API/DB)
        step_llm = get_llm_for_skills(step_skills)
        
        logger.info(f"[implement] Task {current_step + 1}: {task_description[:50]}... (skills: {step_skills})")
        
        # Direct LLM call - no tools (MetaGPT-style, all context pre-loaded)
        response = await step_llm.ainvoke(messages, config=_cfg(state, "implement_code"))
        logger.info("[implement_code] Direct output (no tools)")
        
        # Parse output and write file directly (MetaGPT-style, no tools)
        output = _parse_implement_output(response.content or "")
        if output and file_path:
            full_path = os.path.join(workspace_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(output.content)
            _modified_files.add(file_path)  # Track for prisma auto-push
            logger.info(f"[implement] {action.upper()} {file_path}")
        elif not output:
            logger.warning(f"[implement] Failed to parse JSON output, trying code block fallback")
            # Fallback: try to extract code from response and write
            if response.content and file_path:
                code_match = re.search(r'```(?:typescript|tsx|javascript|jsx|python|prisma)?\s*([\s\S]*?)\s*```', response.content)
                if code_match:
                    full_path = os.path.join(workspace_path, file_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(code_match.group(1))
                    _modified_files.add(file_path)  # Track for prisma auto-push
                    logger.info(f"[implement] FALLBACK {file_path}")
        
        new_modified = get_modified_files()
        
        # Auto db:push if prisma schema was modified (handle both / and \ separators)
        prisma_modified = any(
            f.replace("\\", "/").endswith("prisma/schema.prisma") or f.endswith("schema.prisma")
            for f in new_modified
        )
        if prisma_modified:
            workspace = state.get("workspace_path", "")
            if workspace:
                logger.info("[implement] Prisma schema modified, running generate + db:push + seed...")
                try:
                    # Generate client first
                    result = subprocess.run(
                        "pnpm exec prisma generate", cwd=workspace, shell=True,
                        capture_output=True, text=True, timeout=60,
                        encoding='utf-8', errors='replace'
                    )
                    logger.info(f"[implement] prisma generate: {result.stdout[:200] if result.stdout else 'OK'}")
                    
                    # Push schema to DB
                    result = subprocess.run(
                        "pnpm exec prisma db push --accept-data-loss", cwd=workspace, shell=True,
                        capture_output=True, text=True, timeout=60,
                        encoding='utf-8', errors='replace'
                    )
                    logger.info(f"[implement] db:push: {result.stdout[:200] if result.stdout else 'OK'}")
                    
                    # Auto seed if seed.ts exists
                    seed_file = Path(workspace) / "prisma" / "seed.ts"
                    if seed_file.exists():
                        logger.info("[implement] Running database seed...")
                        result = subprocess.run(
                            "pnpm exec ts-node prisma/seed.ts", cwd=workspace, shell=True,
                            capture_output=True, text=True, timeout=60,
                            encoding='utf-8', errors='replace'
                        )
                        if result.returncode == 0:
                            logger.info("[implement] Database seeded successfully")
                        else:
                            logger.warning(f"[implement] Seed failed: {result.stderr[:200] if result.stderr else 'unknown'}")
                except Exception as e:
                    logger.warning(f"[implement] prisma commands failed: {e}")
        
        all_modified = list(set(files_modified + new_modified))
        
        # Refresh dependencies_content with modified files (fix stale context issue)
        dependencies_content = state.get("dependencies_content", {})
        workspace = state.get("workspace_path", "")
        if workspace and new_modified:
            important_files = ["prisma/schema.prisma", "src/app/layout.tsx", "src/lib/prisma.ts", "src/types/index.ts"]
            for mod_file in new_modified:
                normalized = mod_file.replace("\\", "/")
                if normalized in important_files or normalized in dependencies_content:
                    full_path = os.path.join(workspace, normalized)
                    if os.path.exists(full_path):
                        try:
                            with open(full_path, "r", encoding="utf-8") as f:
                                dependencies_content[normalized] = f.read()
                            logger.info(f"[implement] Refreshed dependency: {normalized}")
                        except Exception as e:
                            logger.warning(f"[implement] Failed to refresh {normalized}: {e}")
        
        # For low complexity, increment current_step here (review is skipped)
        # For medium/high complexity, review node will increment current_step
        complexity = state.get("complexity", "medium")
        next_step = current_step + 1 if complexity == "low" else current_step
        
        return {
            **state,
            "current_step": next_step,
            "_last_implement_step": current_step,
            "react_loop_count": react_loop_count,
            "debug_count": debug_count,
            "review_count": review_count,
            "run_status": None,
            "skill_registry": skill_registry,
            "files_modified": all_modified,
            "last_implemented_file": file_path,
            "message": f"✅ Task {current_step + 1}: {task_description}",
            "action": "IMPLEMENT" if next_step < len(plan_steps) else "VALIDATE",
        }
        
    except Exception as e:
        logger.error(f"[implement] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}


# =============================================================================
# PARALLEL IMPLEMENTATION
# =============================================================================

from app.agents.developer_v2.src.nodes.parallel_utils import (
    group_steps_by_layer,
    run_layer_parallel,
    merge_parallel_results,
    should_use_parallel,
    MAX_CONCURRENT,
)


async def _implement_single_step(
    step: Dict,
    state: DeveloperState,
    skill_registry: SkillRegistry,
    workspace_path: str,
    dependencies_content: Dict,
    created_components: Dict[str, str] = None,
) -> Dict:
    """Implement a single step (for parallel execution)."""
    file_path = step.get("file_path", "")
    task_description = step.get("task", step.get("description", ""))
    action = step.get("action", "")
    step_dependencies = step.get("dependencies", [])
    step_skills = step.get("skills", [])
    
    try:
        if "frontend-design" in step_skills and "frontend-component" not in step_skills:
            step_skills = step_skills + ["frontend-component"]
        
        skills_content = _preload_skills(skill_registry, step_skills)
        
        # Context: only dependencies (project_structure removed - skills have patterns)
        context_parts = []
        deps_context = _build_dependencies_context(
            dependencies_content, step_dependencies,
            workspace_path=workspace_path, exclude_file=file_path
        )
        if deps_context:
            context_parts.append(deps_context)
        
        # Add created component import paths (critical for correct imports)
        if created_components:
            import_hints = ["## Created Component Imports (USE EXACT PATHS)"]
            for comp_name, import_path in sorted(created_components.items()):
                import_hints.append(f"- {comp_name}: `import {{ {comp_name} }} from '{import_path}'`")
            context_parts.append("\n".join(import_hints))
        
        legacy_code = ""
        if action == "modify" and file_path:
            full_path = os.path.join(workspace_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        legacy_code = f.read()
                except Exception:
                    pass
        
        enhanced_task = f"[{action.upper()}] {file_path}\n{task_description}" if file_path else task_description
        
        input_text = _format_input_template(
            "implement_step",
            step_number=step.get("order", 1),
            total_steps=state.get("total_steps", 1),
            task_description=enhanced_task,
            modified_files="",
            related_context="\n\n".join(context_parts),
            feedback_section="",
            logic_analysis="",
            legacy_code=legacy_code,
            debug_logs="",
        )
        
        system_prompt = _build_system_prompt("implement_step", skills_content=skills_content)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ]
        
        step_llm = get_llm_for_skills(step_skills)
        response = await step_llm.ainvoke(messages, config=_cfg(state, f"impl_{file_path}"))
        output = _parse_implement_output(response.content or "")
        
        if output and file_path:
            full_path = os.path.join(workspace_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(output.content)
            logger.info(f"[parallel] {action.upper()} {file_path}")
            return {"file_path": file_path, "success": True, "modified_files": [file_path]}
        
        return {"file_path": file_path, "success": False, "error": "No output"}
    except Exception as e:
        logger.error(f"[parallel] Step failed ({file_path}): {e}")
        return {"file_path": file_path, "success": False, "error": str(e)}


async def implement_parallel(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute implementation steps in parallel by layer (1-8)."""
    logger.info("[NODE] implement_parallel")
    
    try:
        plan_steps = state.get("implementation_plan", [])
        workspace_path = state.get("workspace_path", "")
        tech_stack = state.get("tech_stack", "nextjs")
        
        if not plan_steps:
            return {**state, "error": "No implementation plan", "action": "RESPOND"}
        
        skill_registry = state.get("skill_registry") or SkillRegistry.load(tech_stack)
        dependencies_content = dict(state.get("dependencies_content", {}))
        
        layers = group_steps_by_layer(plan_steps)
        sorted_layers = sorted(layers.keys())
        
        logger.info(f"[parallel] {len(plan_steps)} steps in {len(layers)} layers: {sorted_layers}")
        
        all_modified = []
        all_errors = []
        step_count = 0
        
        created_components = {}  # Pre-populate component paths for parallel execution
        for step in plan_steps:
            file_path = step.get("file_path", "")
            if "/components/" in file_path and file_path.endswith(".tsx"):
                comp_name = os.path.basename(file_path).replace(".tsx", "")
                import_path = "@/" + file_path.replace(".tsx", "")
                created_components[comp_name] = import_path
        
        if created_components:
            logger.info(f"[parallel] Pre-populated {len(created_components)} component paths from plan")
        
        for layer_num in sorted_layers:
            layer_steps = layers[layer_num]
            layer_files = [s.get("file_path", "") for s in layer_steps]
            is_parallel = len(layer_steps) > 1 and layer_num >= 5
            
            logger.info(f"[parallel] Layer {layer_num}: {len(layer_steps)} steps {'(PARALLEL)' if is_parallel else '(SEQ)'}")
            
            if is_parallel:
                async def impl_step(step, comps=created_components):
                    return await _implement_single_step(
                        step, state, skill_registry, workspace_path, dependencies_content, comps
                    )
                
                results = await run_layer_parallel(layer_steps, impl_step, state, MAX_CONCURRENT)
            else:
                results = []
                for step in layer_steps:
                    result = await _implement_single_step(
                        step, state, skill_registry, workspace_path, dependencies_content, created_components
                    )
                    results.append(result)
                    step_count += 1
                    logger.info(f"[parallel] Step {step_count}/{len(plan_steps)}: {step.get('file_path', '')}")
            
            for result in results:
                if result.get("success"):
                    all_modified.extend(result.get("modified_files", []))
                elif result.get("error"):
                    all_errors.append(f"{result.get('file_path')}: {result.get('error')}")
            
            if layer_num == 1:
                schema_modified = any("schema.prisma" in str(r.get("file_path", "")) for r in results)
                if schema_modified:
                    logger.info("[parallel] Running prisma generate + db push...")
                    try:
                        subprocess.run(
                            "pnpm exec prisma generate", 
                            cwd=workspace_path, shell=True, capture_output=True, timeout=60,
                            encoding='utf-8', errors='replace'
                        )
                        subprocess.run(
                            "pnpm exec prisma db push --accept-data-loss", 
                            cwd=workspace_path, shell=True, capture_output=True, timeout=60,
                            encoding='utf-8', errors='replace'
                        )
                        logger.info("[parallel] Prisma commands completed")
                        schema_path = os.path.join(workspace_path, "prisma/schema.prisma")
                        if os.path.exists(schema_path):
                            with open(schema_path, 'r', encoding='utf-8') as f:
                                dependencies_content["prisma/schema.prisma"] = f.read()
                    except Exception as e:
                        logger.warning(f"[parallel] Prisma failed: {e}")
            
            elif layer_num == 2:
                seed_created = any("seed.ts" in str(r.get("file_path", "")) for r in results)
                if seed_created:
                    seed_path = os.path.join(workspace_path, "prisma/seed.ts")
                    if os.path.exists(seed_path):
                        logger.info("[parallel] Running database seed...")
                        try:
                            result = subprocess.run(
                                "pnpm exec ts-node prisma/seed.ts",
                                cwd=workspace_path, shell=True, capture_output=True, 
                                text=True, timeout=60,
                                encoding='utf-8', errors='replace'
                            )
                            if result.returncode == 0:
                                logger.info("[parallel] Database seeded successfully")
                                import hashlib
                                cache_file = Path(workspace_path) / ".seed_cache"
                                seed_hash = hashlib.md5(Path(seed_path).read_bytes()).hexdigest()
                                cache_file.write_text(seed_hash)
                            else:
                                logger.warning(f"[parallel] Seed failed: {result.stderr[:200]}")
                        except Exception as e:
                            logger.warning(f"[parallel] Seed failed: {e}")
            
            elif layer_num == 3:
                types_path = os.path.join(workspace_path, "src/types/index.ts")
                if os.path.exists(types_path):
                    with open(types_path, 'r', encoding='utf-8') as f:
                        dependencies_content["src/types/index.ts"] = f.read()
            
            elif layer_num >= 5:
                refreshed = 0
                for result in results:
                    file_path = result.get("file_path", "")
                    if file_path and file_path.endswith(".tsx"):
                        full_path = os.path.join(workspace_path, file_path)
                        if os.path.exists(full_path):
                            try:
                                with open(full_path, 'r', encoding='utf-8') as f:
                                    dependencies_content[file_path] = f.read()
                                refreshed += 1
                                if "/components/" in file_path:
                                    comp_name = os.path.basename(file_path).replace(".tsx", "")
                                    import_path = "@/" + file_path.replace(".tsx", "")
                                    created_components[comp_name] = import_path
                            except Exception:
                                pass
                if refreshed:
                    logger.info(f"[parallel] Refreshed {refreshed} component files for context")
        
        success_count = len([r for r in all_modified])
        logger.info(f"[parallel] Completed: {success_count} files, {len(all_errors)} errors")
        
        return {
            **state,
            "current_step": len(plan_steps),
            "total_steps": len(plan_steps),
            "files_modified": list(set(all_modified)),
            "dependencies_content": dependencies_content,
            "parallel_errors": all_errors if all_errors else None,
            "message": f"Implemented {success_count} files ({len(layers)} layers)",
            "action": "VALIDATE",
        }
    except Exception as e:
        logger.error(f"[implement_parallel] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}



