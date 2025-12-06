"""Implement node - Execute tasks using tools."""
import logging
import os
import platform
from datetime import date
from typing import List, Dict
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.filesystem_tools import (
    read_file_safe, write_file_safe, edit_file, list_directory_safe, glob, grep_files,
    get_modified_files, reset_modified_files,
)
from app.agents.developer_v2.src.tools.shell_tools import execute_shell
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.utils.prompt_utils import (
    format_input_template as _format_input_template,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.utils.token_utils import truncate_to_tokens
from app.agents.developer_v2.src.nodes._llm import code_llm, get_llm_for_skills
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context
from app.agents.developer_v2.src.skills import SkillRegistry, get_project_structure

logger = logging.getLogger(__name__)


def _build_modified_files_context(files_modified: list) -> str:
    if not files_modified:
        return "None"
    return "\n".join(f"- {f}" for f in files_modified)


def _build_dependencies_context(dependencies_content: dict, step_dependencies: list) -> str:
    if not dependencies_content:
        return ""
    
    parts = []
    if step_dependencies:
        for dep_path in step_dependencies:
            if not isinstance(dep_path, str):
                continue
            if dep_path in dependencies_content:
                parts.append(f"### {dep_path}\n```\n{dependencies_content[dep_path]}\n```")
    
    common_files = ["prisma/schema.prisma"]
    for dep_path in common_files:
        if dep_path in dependencies_content and dep_path not in (step_dependencies or []):
            parts.append(f"### {dep_path}\n```\n{dependencies_content[dep_path]}\n```")
    
    if not parts:
        return ""
    return "<pre_loaded_context>\n" + "\n\n".join(parts) + "\n</pre_loaded_context>"


def _build_env_info(workspace_path: str) -> str:
    is_git = os.path.exists(os.path.join(workspace_path, ".git")) if workspace_path else False
    return f"""OS: {platform.system()} {platform.release()}
Working directory: {workspace_path or '.'}
Git repo: {"Yes" if is_git else "No"}
Date: {date.today().isoformat()}"""


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
    
    previous_step = state.get("_last_implement_step", -1)
    review_count = 0 if current_step != previous_step else state.get("review_count", 0)
    
    try:
        plan_steps = state.get("implementation_plan", [])
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        tech_stack = state.get("tech_stack", "nextjs")
        
        react_loop_count = state.get("react_loop_count", 0)
        debug_count = state.get("debug_count", 0)
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
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Load skill registry and preload skills from step
        skill_registry = state.get("skill_registry") or SkillRegistry.load(tech_stack)
        
        # Preload skills specified in plan step
        skills_content = _preload_skills(skill_registry, step_skills)
        
        context_parts = []
        project_structure = get_project_structure(tech_stack)
        if project_structure:
            context_parts.append(f"<project_structure>\n{project_structure}\n</project_structure>")
        
        dependencies_content = state.get("dependencies_content", {})
        deps_context = _build_dependencies_context(dependencies_content, step_dependencies)
        if deps_context:
            context_parts.append(deps_context)
        
        feedback_section = ""
        if state.get("review_feedback"):
            feedback_section = f"<review_feedback>\n{state.get('review_feedback')}\n</review_feedback>"
        if state.get("summarize_feedback"):
            feedback_section += f"\n<summarize_feedback>\n{state.get('summarize_feedback')}\n</summarize_feedback>"
        if state.get('run_stderr'):
            feedback_section += f"\n<errors>\n{state.get('run_stderr')[:2000]}\n</errors>"
        
        task_type = state.get("task_type", "")
        is_debug_mode = task_type == "bug_fix" or debug_count > 0
        
        # Add debugging skill if in debug mode
        if is_debug_mode and "debugging" not in step_skills:
            debug_content = _preload_skills(skill_registry, ["debugging"])
            if debug_content:
                skills_content = f"{skills_content}\n\n---\n\n{debug_content}" if skills_content else debug_content
        
        # Simplified tools - no skill tools needed (skills preloaded)
        if is_debug_mode:
            tools = [read_file_safe, write_file_safe, edit_file, list_directory_safe, execute_shell, glob, grep_files]
        else:
            tools = [write_file_safe, edit_file, read_file_safe]
        
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
        
        await _llm_with_tools(
            llm=step_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="implement_code",
            max_iterations=8  # Reduced - no skill tool calls needed
        )
        
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
                    # Generate client first
                    result = execute_shell.invoke({
                        "command": "bunx prisma generate",
                        "cwd": workspace
                    })
                    logger.info(f"[implement] prisma generate: {result[:200] if result else 'OK'}")
                    
                    # Then push schema to DB
                    result = execute_shell.invoke({
                        "command": "bunx prisma db push --accept-data-loss",
                        "cwd": workspace
                    })
                    logger.info(f"[implement] db:push: {result[:200] if result else 'OK'}")
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



