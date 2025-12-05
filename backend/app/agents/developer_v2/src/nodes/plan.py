"""Plan node - Break story into abstract tasks."""
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import ImplementationPlan, PlanTask
from app.agents.developer_v2.src.utils.json_utils import extract_json_universal
from app.agents.developer_v2.src.tools.filesystem_tools import list_directory_safe, glob
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
        
        # Get project structure for path guidance
        tech_stack = state.get("tech_stack", "nextjs")
        project_structure = get_project_structure(tech_stack)
        
        # Format requirements and acceptance criteria
        requirements = state.get("story_requirements", [])
        req_text = chr(10).join(f"- {r}" for r in requirements)
        ac_text = chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", []))
        
        input_text = _format_input_template(
            "create_plan",
            story_id=state.get("story_id", ""),
            epic=state.get("epic", ""),
            story_title=state.get("story_title", "Untitled"),
            story_description=state.get("story_description", ""),
            story_requirements=req_text,
            analysis_summary=analysis.get("summary", ""),
            project_structure=project_structure,
            acceptance_criteria=ac_text,
        )

        tools = [list_directory_safe, glob]
        
        # Load feature-plan skill for completeness guidance
        system_prompt = _build_system_prompt("create_plan")
        skill_registry = SkillRegistry.load(tech_stack)
        plan_skill = skill_registry.get_skill("feature-plan")
        if plan_skill:
            skill_content = plan_skill.load_content()
            system_prompt += f"\n\n<skill>\n{skill_content}\n</skill>"
            logger.info("[plan] Loaded feature-plan skill")
        
        # CRITICAL: Add JSON requirement to system prompt (not as HumanMessage)
        json_requirement = """

CRITICAL OUTPUT REQUIREMENT:
Respond with ONLY JSON in result tags. No explanations.

<result>
{
  "story_summary": "<brief summary>",
  "tasks": [
    {"order": 1, "task": "<abstract task description>"},
    {"order": 2, "task": "<abstract task description>"}
  ]
}
</result>

Tasks describe WHAT to achieve, NOT file operations. Agent will decide files."""
        
        system_prompt += json_requirement
        
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
        
        # Add exploration context only (JSON requirement already in system prompt)
        messages.append(HumanMessage(content=f"Context from exploration:\n{exploration[:2000]}\n\nNow create the implementation plan following the system instructions."))
        response = await code_llm.ainvoke(messages, config=_cfg(state, "plan"))
        data = extract_json_universal(response.content, "plan_node")
        plan_result = ImplementationPlan(**data)
        
        logger.info(f"[plan] {len(plan_result.tasks)} tasks")
        
        def format_task(t):
            return f"  {t.order}. {t.task}"
        
        tasks_text = "\n".join(format_task(t) for t in plan_result.tasks)
        msg = f"📋 **Plan** ({len(plan_result.tasks)} tasks)\n{tasks_text}"
        
        return {
            **state,
            "implementation_plan": [t.model_dump() for t in plan_result.tasks],
            "total_steps": len(plan_result.tasks),
            "current_step": 0,
            "message": msg,
            "action": "IMPLEMENT",
        }
        
    except Exception as e:
        logger.error(f"[plan] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
