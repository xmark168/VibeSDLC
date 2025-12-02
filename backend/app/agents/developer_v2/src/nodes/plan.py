"""Plan node - Break story into abstract tasks."""
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import ImplementationPlan
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, list_directory_safe, search_files
from app.agents.developer_v2.src.tools.shell_tools import semantic_code_search
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
from app.agents.developer_v2.src.skills.registry import SkillRegistry
from app.agents.developer_v2.src.skills import get_project_structure

logger = logging.getLogger(__name__)


async def plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Break story into abstract tasks (WHAT, not HOW)."""
    print("[NODE] plan")
    try:
        analysis = state.get("analysis_result") or {}
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Get directory structure (minimal context)
        dir_structure = ""
        if workspace_path:
            try:
                result = list_directory_safe.invoke({"path": "src", "depth": 2})
                if result and not result.startswith("Error:"):
                    dir_structure = result[:1500]
            except Exception:
                pass
        
        # Get project structure for path guidance
        tech_stack = state.get("tech_stack", "nextjs")
        project_structure = get_project_structure(tech_stack)
        
        input_text = _format_input_template(
            "create_plan",
            story_title=state.get("story_title", "Untitled"),
            analysis_summary=analysis.get("summary", ""),
            project_structure=project_structure,
            acceptance_criteria=chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
        )

        tools = [list_directory_safe, search_files]
        
        # Load feature-plan skill for completeness guidance
        system_prompt = _build_system_prompt("create_plan")
        skill_registry = SkillRegistry.load(tech_stack)
        plan_skill = skill_registry.get_skill("feature-plan")
        if plan_skill:
            skill_content = plan_skill.load_content()
            system_prompt += f"\n\n<skill>\n{skill_content}\n</skill>"
            logger.info("[plan] Loaded feature-plan skill")
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ]
        
        # Quick exploration (1 iteration max)
        exploration = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="plan_explore",
            max_iterations=1
        )
        
        messages.append(HumanMessage(content=f"Context:\n{exploration[:2000]}\n\nCreate plan."))
        structured_llm = code_llm.with_structured_output(ImplementationPlan)
        plan_result = await structured_llm.ainvoke(messages, config=_cfg(state, "plan"))
        
        logger.info(f"[plan] {len(plan_result.steps)} steps")
        
        def format_step(s):
            # Show [action] file_path if available
            if s.file_path and s.action:
                text = f"  {s.order}. [{s.action}] {s.file_path}"
                text += f"\n      {s.description}"
            else:
                text = f"  {s.order}. {s.description}"
            return text
        
        steps_text = "\n".join(format_step(s) for s in plan_result.steps)
        msg = f"📋 **Plan** ({len(plan_result.steps)} steps)\n{steps_text}"
        
        return {
            **state,
            "implementation_plan": [s.model_dump() for s in plan_result.steps],
            "total_steps": len(plan_result.steps),
            "current_step": 0,
            "message": msg,
            "action": "IMPLEMENT",
        }
        
    except Exception as e:
        logger.error(f"[plan] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
