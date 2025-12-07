"""Implement node - Direct file output (MetaGPT-style, no tools)."""
import json
import logging
import os
import platform
import re
import subprocess
from datetime import date
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState


class ImplementOutput(BaseModel):
    """Structured output for implementation step."""
    content: str = Field(description="COMPLETE file content")
    explanation: str = Field(default="", description="Brief explanation of changes")

from app.agents.developer_v2.src.tools.filesystem_tools import get_modified_files, reset_modified_files
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
    """Build context from dependencies, auto-loading from disk if not in cache (MetaGPT-style).
    
    Args:
        dependencies_content: Cached file contents
        step_dependencies: List of dependency file paths for this step
        workspace_path: Workspace root path for auto-loading
        exclude_file: Current file being implemented (exclude from context)
    """
    parts = []
    loaded_files = set()
    
    # Load step dependencies (from cache or disk)
    if step_dependencies:
        for dep_path in step_dependencies:
            if not isinstance(dep_path, str):
                continue
            if dep_path == exclude_file:
                continue
            
            content = None
            # Try cache first
            if dep_path in dependencies_content:
                content = dependencies_content[dep_path]
            # Auto-load from disk if not in cache (MetaGPT-style)
            elif workspace_path:
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
    
    # Add common files if not already loaded
    common_files = ["prisma/schema.prisma"]
    for dep_path in common_files:
        if dep_path in loaded_files or dep_path == exclude_file:
            continue
        if dep_path in dependencies_content:
            parts.append(f"### {dep_path}\n```\n{dependencies_content[dep_path]}\n```")
    
    if not parts:
        return ""
    return "<pre_loaded_context>\n" + "\n\n".join(parts) + "\n</pre_loaded_context>"


def _build_debug_summary(state: dict) -> str:
    """Build summary log for debug iterations (MetaGPT-style).
    
    Shows previous attempts and what was tried to help LLM avoid repeating mistakes.
    """
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
            for bf in bundled:  # Load all bundled files
                bf_content = skill.load_bundled_file(bf)
                if bf_content:
                    content += f"\n\n### Reference: {bf}\n{bf_content}"
        
        parts.append(f"## Skill: {skill_id}\n{content}")
        logger.info(f"[implement] Preloaded skill: {skill_id} ({len(content)} chars)")
    
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
        
        # Load skill registry and preload skills from step
        skill_registry = state.get("skill_registry") or SkillRegistry.load(tech_stack)
        
        # Preload skills specified in plan step
        skills_content = _preload_skills(skill_registry, step_skills)
        
        context_parts = []
        project_structure = get_project_structure(tech_stack)
        if project_structure:
            context_parts.append(f"<project_structure>\n{project_structure}\n</project_structure>")
        
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
            logger.info(f"[implement] {action.upper()} {file_path}: {output.explanation[:100] if output.explanation else 'done'}")
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
                logger.info("[implement] Prisma schema modified, running generate + db:push...")
                try:
                    # Generate client first (direct subprocess, no tools)
                    result = subprocess.run(
                        "bunx prisma generate", cwd=workspace, shell=True,
                        capture_output=True, text=True, timeout=60
                    )
                    logger.info(f"[implement] prisma generate: {result.stdout[:200] if result.stdout else 'OK'}")
                    
                    # Then push schema to DB
                    result = subprocess.run(
                        "bunx prisma db push --accept-data-loss", cwd=workspace, shell=True,
                        capture_output=True, text=True, timeout=60
                    )
                    logger.info(f"[implement] db:push: {result.stdout[:200] if result.stdout else 'OK'}")
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
        
        return {
            **state,
            "current_step": current_step,
            "_last_implement_step": current_step,
            "react_loop_count": react_loop_count,
            "debug_count": debug_count,
            "review_count": review_count,
            "run_status": None,
            "skill_registry": skill_registry,
            "files_modified": all_modified,
            "dependencies_content": dependencies_content,  # Refreshed with modified files
            "last_implemented_file": file_path,
            "message": f"✅ Task {current_step + 1}: {task_description}",
            "action": "IMPLEMENT" if current_step + 1 < len(plan_steps) else "VALIDATE",
        }
        
    except Exception as e:
        logger.error(f"[implement] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}



