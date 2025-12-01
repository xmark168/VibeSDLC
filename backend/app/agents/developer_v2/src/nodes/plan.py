"""Plan node - Create design + implementation plan."""
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
    get_shared_context as _get_shared_context,
)
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context, build_static_context

logger = logging.getLogger(__name__)


async def plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Create design + implementation plan (merged node)."""
    print("[NODE] plan")
    try:
        analysis = state.get("analysis_result") or {}
        complexity = state.get("complexity", "medium")
        workspace_path = state.get("workspace_path", "")
        
        # Simple design for medium/high complexity
        design_doc = ""
        if complexity in ["medium", "high"]:
            research_context = state.get("research_context", "")
            design_doc = f"""# Design Notes

## Task: {state.get("story_title", "")}
## Complexity: {complexity}

## Approach
Based on analysis: {analysis.get("summary", "N/A")}

## Affected Files
{chr(10).join(f"- {f}" for f in state.get("affected_files", []))}

## Best Practices
{research_context[:1000] if research_context else "Follow project conventions in AGENTS.md"}
"""
            logger.info(f"[plan] Built simple design doc: {len(design_doc)} chars")
        
        static_context = build_static_context(state)
        directory_structure = static_context if static_context else ""
        
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Get actual directory structure
        actual_structure = ""
        if workspace_path:
            try:
                result = list_directory_safe.invoke({"path": "src", "depth": 3})
                if result and not result.startswith("Error:"):
                    actual_structure = f"\n\n## ACTUAL DIRECTORY STRUCTURE (src/):\n```\n{result[:2000]}\n```"
            except Exception:
                pass
        
        input_text = _format_input_template(
            "create_plan",
            story_title=state.get("story_title", "Untitled"),
            analysis_summary=analysis.get("summary", ""),
            task_type=state.get("task_type", "feature"),
            complexity=complexity,
            design_doc=design_doc or "No design document",
            directory_structure=directory_structure + actual_structure,
            code_guidelines=_get_shared_context("code_guidelines"),
            acceptance_criteria=chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            existing_code="Use search_codebase and read_file tools to explore existing code"
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
            max_iterations=3
        )
        
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:3000]}\n\nNow create the implementation plan."))
        structured_llm = code_llm.with_structured_output(ImplementationPlan)
        plan_result = await structured_llm.ainvoke(messages, config=_cfg(state, "plan"))
        
        if not plan_result.steps:
            logger.warning(f"[plan] No steps in plan! affected_files: {state.get('affected_files', [])}")
        else:
            logger.info(f"[plan] Created {len(plan_result.steps)} steps, estimated {plan_result.total_estimated_hours}h")
        
        steps_text = "\n".join(
            f"  {s.order}. [{s.action}] {s.description} ({s.estimated_minutes}m)"
            for s in plan_result.steps
        )
        
        msg = f"""📋 **Implementation Plan**

**Story:** {plan_result.story_summary}
**Total Time:** {plan_result.total_estimated_hours}h
**Steps:** {len(plan_result.steps)}

{steps_text}

🔄 **Rollback Plan:** {plan_result.rollback_plan or 'N/A'}"""
        
        return {
            **state,
            "implementation_plan": [s.model_dump() for s in plan_result.steps],
            "total_steps": len(plan_result.steps),
            "current_step": 0,
            "design_doc": design_doc,
            "message": msg,
            "action": "IMPLEMENT",
        }
        
    except Exception as e:
        logger.error(f"[plan] Error: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "message": f"❌ Lỗi khi tạo plan: {str(e)}",
            "action": "RESPOND",
        }
