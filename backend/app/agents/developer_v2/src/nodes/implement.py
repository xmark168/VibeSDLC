"""Implement node - Execute implementation step by step using tools."""
import logging
import os
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, write_file_safe, edit_file, list_directory_safe, search_files
from app.agents.developer_v2.src.tools.shell_tools import execute_shell, semantic_code_search
from app.agents.developer_v2.src.tools import get_related_code_indexed, get_boilerplate_examples, get_agents_md
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.utils.prompt_utils import (
    format_input_template as _format_input_template,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context, build_static_context
from app.agents.developer_v2.src.skills import SkillRegistry

logger = logging.getLogger(__name__)


async def implement(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute implementation step by step."""
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] implement {current_step + 1}/{total_steps}")
    try:
        plan_steps = state.get("implementation_plan", [])
        current_step = state.get("current_step", 0)
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        react_loop_count = state.get("react_loop_count", 0)
        debug_count = state.get("debug_count", 0)
        summarize_feedback = state.get("summarize_feedback")
        run_status = state.get("run_status")
        
        if state.get("react_mode") and run_status == "FAIL":
            current_step = 0
            react_loop_count += 1
            debug_count = 0
            logger.info(f"[implement] React loop {react_loop_count} (from run_code FAIL, restarting from step 0)")
        elif state.get("react_mode") and current_step == 0 and summarize_feedback:
            react_loop_count += 1
            debug_count = 0
            logger.info(f"[implement] React loop {react_loop_count} (from summarize: {summarize_feedback[:100]}...)")
        
        if not plan_steps:
            logger.error("[implement] No implementation plan")
            return {**state, "error": "No implementation plan", "action": "RESPOND"}
        
        if current_step >= len(plan_steps):
            return {
                **state,
                "message": "Implementation hoàn tất",
                "action": "VALIDATE",
            }
        
        step = plan_steps[current_step]
        current_file = step.get("file_path") or ""
        
        # Gather related code context using CocoIndex
        related_context = state.get("related_code_context", "")
        if workspace_path and not related_context:
            index_ready = state.get("index_ready", False)
            step_description = step.get("description", "")
            
            if index_ready:
                related_context = get_related_code_indexed(
                    project_id=project_id,
                    current_file=current_file,
                    task_description=step_description,
                    top_k=8,
                    task_id=task_id
                )
                logger.info(f"[implement] Using CocoIndex for context")
        
        # Get existing code if modifying
        existing_code = ""
        if workspace_path and current_file and step.get("action") == "modify":
            try:
                result = read_file_safe.invoke({"file_path": current_file})
                if result and not result.startswith("Error:"):
                    if "\n\n" in result:
                        existing_code = result.split("\n\n", 1)[1]
                    else:
                        existing_code = result
            except Exception:
                pass
        
        implementation_plan = state.get("code_plan_doc") or ""
        if not implementation_plan:
            implementation_plan = "\n".join(
                f"{s.get('order', i+1)}. [{s.get('action')}] {s.get('description')}"
                for i, s in enumerate(plan_steps)
            )
        
        # Build context (pass current_file for smart section extraction)
        static_context = build_static_context(state, current_file)
        
        # Always include AGENTS.md directly (not from search)
        agents_md = state.get("agents_md", "")
        if not agents_md and workspace_path:
            agents_md = get_agents_md(workspace_path)
        if agents_md:
            static_context = f"## AGENTS.MD (MUST FOLLOW!)\n{agents_md}\n\n---\n\n{static_context}" if static_context else f"## AGENTS.MD (MUST FOLLOW!)\n{agents_md}"
        
        if workspace_path:
            task_type = "page"
            if "component" in current_file.lower():
                task_type = "component"
            elif "api" in current_file.lower() or "route" in current_file.lower():
                task_type = "api"
            elif "layout" in current_file.lower():
                task_type = "layout"
            
            boilerplate = get_boilerplate_examples(workspace_path, task_type)
            if boilerplate:
                static_context = f"{static_context}\n\n---\n\n{boilerplate}" if static_context else boilerplate
        
        dynamic_parts = []
        
        if related_context:
            dynamic_parts.append(f"## RELATED CODE\n{related_context}")
        
        research_context = state.get("research_context", "")
        if research_context:
            dynamic_parts.append(f"## Best Practices (from web research)\n{research_context[:1500]}")
        
        summarize_feedback = state.get("summarize_feedback", "")
        if summarize_feedback:
            dynamic_parts.append(f"## FEEDBACK FROM PREVIOUS ATTEMPT (MUST ADDRESS)\n{summarize_feedback}")
        
        dynamic_context = "\n\n---\n\n".join(dynamic_parts) if dynamic_parts else "No additional context"
        full_related_context = f"{static_context}\n\n{'='*60}\n\n{dynamic_context}" if static_context else dynamic_context
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Build conditional sections (OPTIMIZED - only include when needed)
        existing_code_section = ""
        if step.get("action") == "modify" and existing_code:
            existing_code_section = f"<existing_code>\n{existing_code}\n</existing_code>"
        
        error_logs_section = ""
        if state.get('error_logs'):
            error_logs_section = f"<previous_errors>\n{state.get('error_logs')}\n</previous_errors>"
        
        # Tools for implementation - LLM uses these directly to create/edit files
        tools = [read_file_safe, write_file_safe, edit_file, list_directory_safe, semantic_code_search, execute_shell, search_files]
        
        # Get skill from registry (or load if not available)
        skill_registry: SkillRegistry = state.get("skill_registry")
        if not skill_registry:
            tech_stack = state.get("tech_stack", "nextjs")
            skill_registry = SkillRegistry.load(tech_stack)
        
        # Try to get skill: first from step's required_skill, then auto-detect
        skill = None
        required_skill_id = step.get("required_skill")
        
        if required_skill_id and skill_registry:
            skill = skill_registry.get_skill(required_skill_id)
            if skill:
                logger.info(f"[implement] Using assigned skill: {skill.id}")
        
        if not skill and skill_registry:
            skill = skill_registry.detect_skill(current_file, step.get("description", ""))
            if skill:
                logger.info(f"[implement] Auto-detected skill: {skill.id}")
        
        # ALWAYS use generic prompt structure from prompts.yaml
        input_text = _format_input_template(
            "implement_step",
            step_number=current_step + 1,
            total_steps=len(plan_steps),
            step_description=step.get("description", ""),
            file_path=current_file,
            action=step.get("action", "modify"),
            story_summary=state.get("analysis_result", {}).get("summary", ""),
            related_context=full_related_context[:6000],  # Full context including AGENTS.md
            existing_code_section=existing_code_section,
            error_logs_section=error_logs_section
        )
        
        # Build system prompt with optional skill injection
        system_prompt = _build_system_prompt("implement_step")
        
        if skill:
            # Inject skill as additional section (not replace)
            skill_section = f"""
<skill name="{skill.id}">
{skill.system_prompt}
</skill>
"""
            system_prompt += f"\n\n{skill_section}"
            logger.info(f"[implement] Injected skill: {skill.id} for {current_file}")
        else:
            logger.info(f"[implement] No skill found, using generic only for {current_file}")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ]
        
        # Let LLM use tools directly to implement the code
        result = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="implement_code",
            max_iterations=10  # Allow multiple tool calls for complex changes
        )
        
        logger.info(f"[implement] Step {current_step + 1} completed via tool usage")
        
        # Track file changes
        action = step.get("action", "create")
        files_created = state.get("files_created", [])
        files_modified = state.get("files_modified", [])
        
        if action == "create" and current_file:
            if current_file not in files_created:
                files_created.append(current_file)
        elif action == "modify" and current_file:
            if current_file not in files_modified:
                files_modified.append(current_file)
        
        msg = f"✅ Step {current_step + 1}: {step.get('description', '')}"
        
        return {
            **state,
            "files_created": files_created,
            "files_modified": files_modified,
            "current_step": current_step + 1,
            "react_loop_count": react_loop_count,
            "debug_count": debug_count,
            "run_status": None,
            "message": msg,
            "action": "IMPLEMENT" if current_step + 1 < len(plan_steps) else "VALIDATE",
        }
        
    except Exception as e:
        logger.error(f"[implement] Error: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "message": f"❌ Lỗi khi implement: {str(e)}",
            "action": "RESPOND",
        }
