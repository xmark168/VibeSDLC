"""Implement node - Execute tasks using tools (Agentic Skills)."""
import logging
import os
import platform
from datetime import date
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.filesystem_tools import (
    read_file_safe, write_file_safe, edit_file, list_directory_safe, glob, grep_files,
    get_modified_files, reset_modified_files,
)
from app.agents.developer_v2.src.tools.shell_tools import execute_shell
from app.agents.developer_v2.src.tools.skill_tools import activate_skills, read_skill_file, list_skill_files, set_skill_context, reset_skill_cache
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.utils.prompt_utils import (
    format_input_template as _format_input_template,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context
from app.agents.developer_v2.src.skills import SkillRegistry, get_project_structure

logger = logging.getLogger(__name__)


def _build_modified_files_context(files_modified: list) -> str:
    """List files modified in previous steps."""
    if not files_modified:
        return "None"
    return "\n".join(f"- {f}" for f in files_modified)


def _build_dependencies_context(dependencies_content: dict, step_dependencies: list) -> str:
    """Build pre-loaded dependencies context for the current step."""
    if not dependencies_content:
        return ""
    
    parts = []
    
    # First add step-specific dependencies
    if step_dependencies:
        for dep_path in step_dependencies:
            # Skip non-string dependencies (e.g., integers from LLM mistakes)
            if not isinstance(dep_path, str):
                continue
            if dep_path in dependencies_content:
                content = dependencies_content[dep_path]
                parts.append(f"### {dep_path}\n```\n{content}\n```")
    
    # Then add common files if not already included
    common_files = ["prisma/schema.prisma", "src/lib/prisma.ts"]
    for dep_path in common_files:
        if dep_path in dependencies_content and dep_path not in (step_dependencies or []):
            content = dependencies_content[dep_path]
            parts.append(f"### {dep_path}\n```\n{content}\n```")
    
    if not parts:
        return ""
    
    return "<pre_loaded_context>\n" + "\n\n".join(parts) + "\n</pre_loaded_context>"


def _build_env_info(workspace_path: str) -> str:
    """Build environment info string."""
    is_git = os.path.exists(os.path.join(workspace_path, ".git")) if workspace_path else False
    return f"""OS: {platform.system()} {platform.release()}
Working directory: {workspace_path or '.'}
Git repo: {"Yes" if is_git else "No"}
Date: {date.today().isoformat()}"""


async def implement(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute implementation step (Claude decides what/where to implement)."""
    reset_skill_cache()
    reset_modified_files()  # Reset file tracking for this step
    
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] implement {current_step + 1}/{total_steps}")
    
    # Reset review_count for new step (prevents carry-over from previous step)
    # This ensures each step gets fresh review attempts
    review_count = 0
    
    try:
        plan_steps = state.get("implementation_plan", [])
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        tech_stack = state.get("tech_stack", "nextjs")
        
        # React loop handling
        react_loop_count = state.get("react_loop_count", 0)
        debug_count = state.get("debug_count", 0)
        if state.get("react_mode") and state.get("run_status") == "FAIL":
            current_step = 0
            react_loop_count += 1
            # NOTE: Do NOT reset debug_count here - it's tracked by analyze_error
            # and checked by route_after_test for max_debug limit
            logger.info(f"[implement] React loop {react_loop_count}, debug_count={debug_count}")
        
        if not plan_steps:
            return {**state, "error": "No implementation plan", "action": "RESPOND"}
        
        if current_step >= len(plan_steps):
            return {**state, "message": "Implementation done", "action": "VALIDATE"}
        
        step = plan_steps[current_step]
        # Support both new format (task) and legacy format (description)
        task_description = step.get("task", step.get("description", ""))
        file_path = step.get("file_path", "")
        action = step.get("action", "")
        step_dependencies = step.get("dependencies", [])
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Build context
        context_parts = []
        
        # Project structure (Claude uses this to find correct paths)
        project_structure = get_project_structure(tech_stack)
        if project_structure:
            context_parts.append(f"<project_structure>\n{project_structure}\n</project_structure>")
        
        # Pre-loaded dependencies from analyze_and_plan (MetaGPT-style)
        dependencies_content = state.get("dependencies_content", {})
        deps_context = _build_dependencies_context(dependencies_content, step_dependencies)
        if deps_context:
            context_parts.append(deps_context)
            logger.info(f"[implement] Using {len(step_dependencies)} pre-loaded dependencies")
        
        # Feedback from previous attempt
        feedback_section = ""
        if state.get("summarize_feedback"):
            feedback_section = f"<feedback>\n{state.get('summarize_feedback')}\n</feedback>"
        if state.get('run_stderr'):
            feedback_section += f"\n<errors>\n{state.get('run_stderr')[:2000]}\n</errors>"
        
        # Load skill registry
        skill_registry = state.get("skill_registry") or SkillRegistry.load(tech_stack)
        set_skill_context(skill_registry)
        
        # Auto-load debugging skill in debug mode
        task_type = state.get("task_type", "")
        is_debug_mode = task_type == "bug_fix" or debug_count > 0
        
        if is_debug_mode:
            debug_skill = skill_registry.get_skill("debugging")
            if debug_skill:
                debug_content = debug_skill.load_content()
                context_parts.append(f"<debugging_skill>\n{debug_content}\n</debugging_skill>")
                logger.info("[implement] Auto-loaded debugging skill for bug fix")
        
        # Tools - MetaGPT-style hybrid approach:
        # - Normal mode: Skill + write + limited read (for checking imports/Props)
        # - Debug mode: Full exploration tools for fixing bugs
        if is_debug_mode:
            # Debug mode: Full tools for exploration and fixing
            tools = [
                read_file_safe, write_file_safe, edit_file, list_directory_safe,
                execute_shell, glob, grep_files,
                activate_skills, read_skill_file, list_skill_files,
            ]
            logger.info("[implement] Debug mode: using full tool set")
        else:
            # Normal mode: Skill + write + read (hybrid approach)
            # - write_file_safe, edit_file: Create/modify files
            # - read_file_safe: Check imports, Props interfaces (READ BEFORE IMPORT rule)
            # - activate_skills, read_skill_file: Load patterns
            # - NO exploration: glob, grep_files, list_directory_safe (context pre-loaded)
            tools = [
                write_file_safe, edit_file,  # Action tools
                read_file_safe,  # For checking imports/Props (hybrid - not pure MetaGPT)
                activate_skills, read_skill_file, list_skill_files,  # Skill tools
            ]
            logger.info("[implement] Normal mode: hybrid tools (write + read + skills)")
        
        # Get modified files from previous steps
        files_modified = state.get("files_modified", [])
        modified_files_content = _build_modified_files_context(files_modified)
        
        # Build enhanced task description with file_path and action
        enhanced_task = task_description
        if file_path:
            enhanced_task = f"[{action.upper()}] {file_path}\n{task_description}"
        
        input_text = _format_input_template(
            "implement_step",
            step_number=current_step + 1,
            total_steps=len(plan_steps),
            task_description=enhanced_task,
            modified_files=modified_files_content,
            related_context="\n\n".join(context_parts)[:6000],  # Increased for pre-loaded context
            feedback_section=feedback_section,
        )
        
        skill_catalog = skill_registry.get_skill_catalog_for_prompt()
        system_prompt = _build_system_prompt("implement_step", skill_catalog=skill_catalog)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ]
        
        logger.info(f"[implement] Task {current_step + 1}: {task_description[:50]}...")
        
        # Execute (Claude decides files to create/modify)
        await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="implement_code",
            max_iterations=15
        )
        
        # Get files modified in this step and merge with previous
        new_modified = get_modified_files()
        all_modified = list(set(files_modified + new_modified))
        
        # NOTE: Don't increment current_step here!
        # current_step is incremented in review node ONLY when LGTM
        # This ensures LBTM re-implements the SAME step
        return {
            **state,
            "current_step": current_step,  # Keep same step until review LGTM
            "react_loop_count": react_loop_count,
            "debug_count": debug_count,
            "review_count": review_count,  # Reset for this step
            "run_status": None,
            "skill_registry": skill_registry,
            "files_modified": all_modified,
            "last_implemented_file": file_path,  # Track for review
            "message": f"✅ Task {current_step + 1}: {task_description}",
            "action": "IMPLEMENT" if current_step + 1 < len(plan_steps) else "VALIDATE",
        }
        
    except Exception as e:
        logger.error(f"[implement] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
