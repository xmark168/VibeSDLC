"""Implement node - Execute tasks using tools (Agentic Skills)."""
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, write_file_safe, edit_file, list_directory_safe, search_files
from app.agents.developer_v2.src.tools.shell_tools import execute_shell, semantic_code_search
from app.agents.developer_v2.src.tools.skill_tools import activate_skill, read_skill_file, list_skill_files, set_skill_context, reset_skill_cache
from app.agents.developer_v2.src.tools.cocoindex_tools import search_codebase_tool
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


async def implement(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute implementation step (Claude activates skills as needed)."""
    # Reset skill cache at start of each step (prevents duplicate activations)
    reset_skill_cache()
    
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] implement {current_step + 1}/{total_steps}")
    
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
            debug_count = 0
            logger.info(f"[implement] React loop {react_loop_count}")
        
        if not plan_steps:
            return {**state, "error": "No implementation plan", "action": "RESPOND"}
        
        if current_step >= len(plan_steps):
            return {**state, "message": "Implementation done", "action": "VALIDATE"}
        
        step = plan_steps[current_step]
        current_file = step.get("file_path") or ""
        step_action = step.get("action", "modify")
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Build minimal context (Claude will search for more via tools)
        context_parts = []
        
        # Project structure only
        project_structure = get_project_structure(tech_stack)
        if project_structure:
            context_parts.append(f"<project_structure>\n{project_structure}\n</project_structure>")
        
        # Feedback from previous attempt (critical for debug loops)
        if state.get("summarize_feedback"):
            context_parts.append(f"<feedback>\n{state.get('summarize_feedback')}\n</feedback>")
        
        # Existing code for modify
        existing_code_section = ""
        if step_action == "modify" and current_file:
            try:
                result = read_file_safe.invoke({"file_path": current_file})
                if result and not result.startswith("Error:"):
                    code = result.split("\n\n", 1)[1] if "\n\n" in result else result
                    existing_code_section = f"<existing_code>\n{code}\n</existing_code>"
            except Exception:
                pass
        
        # Error logs
        error_logs_section = ""
        if state.get('run_stderr'):
            error_logs_section = f"<errors>\n{state.get('run_stderr')[:2000]}\n</errors>"
        
        # Load skill registry
        skill_registry = state.get("skill_registry") or SkillRegistry.load(tech_stack)
        set_skill_context(skill_registry)
        
        # Tools (Claude searches codebase and activates skills as needed)
        tools = [
            read_file_safe, write_file_safe, edit_file, list_directory_safe,
            semantic_code_search, execute_shell, search_files,
            search_codebase_tool,  # Semantic search via CocoIndex
            activate_skill, read_skill_file, list_skill_files,
        ]
        
        # Build prompt
        input_text = _format_input_template(
            "implement_step",
            step_number=current_step + 1,
            total_steps=len(plan_steps),
            step_description=step.get("description", ""),
            file_path=current_file,
            action=step_action,
            related_context="\n\n".join(context_parts)[:4000],
            existing_code_section=existing_code_section,
            error_logs_section=error_logs_section
        )
        
        skill_catalog = skill_registry.get_skill_catalog_for_prompt()
        system_prompt = _build_system_prompt("implement_step", skill_catalog=skill_catalog)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ]
        
        logger.info(f"[implement] Step {current_step + 1}: {current_file}")
        
        # Execute
        await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="implement_code",
            max_iterations=10
        )
        
        # Track files
        files_created = state.get("files_created", [])
        files_modified = state.get("files_modified", [])
        if step_action == "create" and current_file and current_file not in files_created:
            files_created.append(current_file)
        elif step_action == "modify" and current_file and current_file not in files_modified:
            files_modified.append(current_file)
        
        return {
            **state,
            "files_created": files_created,
            "files_modified": files_modified,
            "current_step": current_step + 1,
            "react_loop_count": react_loop_count,
            "debug_count": debug_count,
            "run_status": None,
            "skill_registry": skill_registry,
            "message": f"✅ Step {current_step + 1}: {step.get('description', '')}",
            "action": "IMPLEMENT" if current_step + 1 < len(plan_steps) else "VALIDATE",
        }
        
    except Exception as e:
        logger.error(f"[implement] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
