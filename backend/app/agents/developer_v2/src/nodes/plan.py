"""Plan node - Create implementation plan."""
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
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context, build_static_context
from app.agents.developer_v2.src.skills import SkillRegistry

logger = logging.getLogger(__name__)


async def plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Create implementation plan based on analysis."""
    print("[NODE] plan")
    try:
        analysis = state.get("analysis_result") or {}
        complexity = state.get("complexity", "medium")
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Load skill registry
        tech_stack = state.get("tech_stack", "nextjs")
        skill_registry = state.get("skill_registry")
        if not skill_registry:
            skill_registry = SkillRegistry.load(tech_stack)
            logger.info(f"[plan] Loaded SkillRegistry: {len(skill_registry.skills)} skills")
        
        # Get skill catalog for LLM to choose from (Phase 1: Discovery)
        skill_catalog = skill_registry.get_skill_catalog() if skill_registry else ""
        
        # Get directory structure
        static_context = build_static_context(state)
        dir_structure = static_context or ""
        
        if workspace_path:
            try:
                result = list_directory_safe.invoke({"path": "src", "depth": 3})
                if result and not result.startswith("Error:"):
                    dir_structure += f"\n```\n{result[:2000]}\n```"
            except Exception:
                pass
        
        input_text = _format_input_template(
            "create_plan",
            story_title=state.get("story_title", "Untitled"),
            analysis_summary=analysis.get("summary", ""),
            task_type=state.get("task_type", "feature"),
            complexity=complexity,
            directory_structure=dir_structure,
            acceptance_criteria=chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            available_skills=skill_catalog,
        )

        tools = [read_file_safe, list_directory_safe, semantic_code_search, search_files]
        
        messages = [
            SystemMessage(content=_build_system_prompt("create_plan")),
            HumanMessage(content=input_text)
        ]
        
        exploration = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="plan_explore",
            max_iterations=2
        )
        
        messages.append(HumanMessage(content=f"Context:\n{exploration[:3000]}\n\nCreate plan."))
        structured_llm = code_llm.with_structured_output(ImplementationPlan)
        plan_result = await structured_llm.ainvoke(messages, config=_cfg(state, "plan"))
        
        if not plan_result.steps:
            logger.warning(f"[plan] No steps!")
        else:
            logger.info(f"[plan] {len(plan_result.steps)} steps, {plan_result.total_estimated_hours}h")
        
        steps_text = "\n".join(
            f"  {s.order}. [{s.action}] {s.description}"
            for s in plan_result.steps
        )
        
        msg = f"""📋 **Plan**

**Story:** {plan_result.story_summary}
**Steps:** {len(plan_result.steps)}

{steps_text}
"""
        
        return {
            **state,
            "implementation_plan": [s.model_dump() for s in plan_result.steps],
            "total_steps": len(plan_result.steps),
            "current_step": 0,
            "message": msg,
            "action": "IMPLEMENT",
            "skill_registry": skill_registry,
            "available_skills": skill_registry.get_skill_ids() if skill_registry else [],
            "tech_stack": tech_stack,
        }
        
    except Exception as e:
        logger.error(f"[plan] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
